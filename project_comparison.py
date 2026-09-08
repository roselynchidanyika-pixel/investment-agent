"""Two/Three-project comparison engine.

Runs the exact same analysis pipeline as the single-project flow for each project
(capital budgeting, DCF, returns, risk, scenario, sensitivity, FX risk, currency
strategy, final decision), then builds a side-by-side matrix, ranks the projects
with a transparent equal-weight composite score, and produces a recommendation.

The winner is decided purely by the computed results — no currency (USD, ZAR or
ZiG) is ever treated as automatically superior.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

import pandas as pd

from data_validation import validate_project_inputs, get_default_inputs
from calculations import calculate_all_metrics, calculate_full_sensitivity
from risk_analysis import assess_risks
from scenario_analysis import run_scenario_analysis
from fx_analysis import (
    run_fx_scenario_analysis,
    assess_currency_exposure,
    get_fx_risk_summary,
    recommend_currency_strategy,
)
from decision_engine import get_final_decision
from project_templates import get_template_inputs, get_project_type_list

PROJECT_LABELS = {0: "A", 1: "B", 2: "C"}
RISK_RANK = {"LOW": 1, "MODERATE": 2, "HIGH": 3, "VERY HIGH": 4}

# Comparison metrics and whether higher is better or worse.
COMPARISON_METHODS = {
    "NPV": ("NPV USD", "higher"),
    "IRR": ("IRR", "higher"),
    "MIRR": ("MIRR", "higher"),
    "PI": ("PI", "higher"),
    "ROI": ("ROI", "higher"),
    "Payback": ("Payback", "lower"),
    "Base NPV": ("Base NPV USD", "higher"),
    "Risk": ("Risk Level", "lower"),
}


def _to_usd(amount: Any, currency: str, rates: Dict[str, Any]) -> float:
    """Convert an amount in the project currency to USD using the legacy rates dict."""
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return 0.0
    ccy = str(currency or "USD").upper()
    if ccy == "USD":
        return amount
    per_usd = rates.get(ccy) or rates.get(f"USD_{ccy}") or 0
    if not per_usd:
        return amount
    try:
        return amount / float(per_usd)
    except (ZeroDivisionError, TypeError, ValueError):
        return amount


def _coerce(value: str) -> Any:
    v = value.strip()
    try:
        return float(v)
    except ValueError:
        return v


# ---------------------------------------------------------------------------
# Sample comparison data (also shipped as sample_projects_2.csv / _3.csv)
# ---------------------------------------------------------------------------

_SLOT_TEMPLATES = {
    0: "generic",   # Growth Facility Expansion (manual-ish profile, matches sample_data.csv)
    1: "manufacturing_capacity_upgrade",
    2: "solar_energy_expansion",
}

_SLOT_OVERRIDES = {
    0: {
        "project_name": "Growth Facility Expansion",
        "project_description": "Expansion of production capacity to satisfy growing regional demand",
        "initial_investment": 1000000.0,
        "project_life": 10,
        "annual_revenue": 350000.0,
        "operating_costs": 80000.0,
        "tax_rate": 0.25,
        "working_capital": 0.0,
        "terminal_value": 0.0,
        "wacc": 0.10,
        "financing_rate": 0.08,
        "reinvestment_rate": 0.06,
        "revenue_growth": 0.0,
        "cost_growth": 0.0,
        "terminal_growth": 0.0,
        "depreciation_rate": 0.10,
        "currency": "USD",
        "zig_revenue_share": 0.20,
        "zig_cost_share": 0.30,
        "zar_revenue_share": 0.20,
        "zar_cost_share": 0.10,
        "investment_fx_share": 0.0,
        "liquidity_buffer_months": 6,
    },
}

_SAMPLE_LABELS = {0: "Project A", 1: "Project B", 2: "Project C"}


def _build_sample_slots() -> List[Dict[str, Any]]:
    slots = []
    for i in range(3):
        tid = _SLOT_TEMPLATES[i]
        data = get_template_inputs(tid) if tid != "generic" else dict(get_default_inputs())
        data.update(_SLOT_OVERRIDES.get(i, {}))
        data.setdefault("zig_revenue_share", 0.0)
        data.setdefault("zig_cost_share", 0.0)
        data.setdefault("zar_revenue_share", 0.0)
        data.setdefault("zar_cost_share", 0.0)
        data.setdefault("investment_fx_share", 0.0)
        data.setdefault("liquidity_buffer_months", 6)
        data["_template_id"] = tid
        data["_label"] = _SAMPLE_LABELS[i]
        slots.append(data)
    return slots


def load_sample_projects(n: int) -> List[Dict[str, Any]]:
    """Load sample project inputs for a 2- or 3-project comparison.

    Prefers the shipped sample CSVs; falls back to built-in profiles if the file
    cannot be read.
    """
    n = int(n)
    if n not in (2, 3):
        raise ValueError("Sample comparisons support exactly 2 or 3 projects.")

    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"sample_projects_{n}.csv")
    try:
        df = pd.read_csv(csv_path)
        projects: List[Dict[str, Any]] = []
        for prj, grp in df.groupby("project", sort=False):
            data = {str(r["parameter"]): _coerce(str(r["value"])) for _, r in grp.iterrows()}
            data["_label"] = _SAMPLE_LABELS[len(projects)]
            if len(projects) < 3:
                data["_template_id"] = _SLOT_TEMPLATES[len(projects)]
            projects.append(data)
        if len(projects) == n:
            return projects
    except Exception:
        pass

    slots = _build_sample_slots()
    return slots[:n]


# ---------------------------------------------------------------------------
# Per-project evaluation
# ---------------------------------------------------------------------------

def evaluate_project(inputs: Dict[str, Any], fx_market: Dict[str, Any]) -> Dict[str, Any]:
    """Run the full single-project pipeline for one project in a comparison."""
    is_valid, errors, warnings = validate_project_inputs(inputs)
    if not is_valid:
        return {
            "status": "invalid",
            "label": inputs.get("_label", inputs.get("project_label", "Project")),
            "name": inputs.get("project_name", "Unnamed project"),
            "inputs": inputs,
            "errors": errors,
            "warnings": warnings,
        }

    metrics = calculate_all_metrics(inputs)
    fx_scenarios = run_fx_scenario_analysis(inputs)
    fx_exposure = assess_currency_exposure(inputs)
    fx_risk = get_fx_risk_summary(inputs, fx_market, fx_scenarios)
    risk_data = assess_risks(inputs, metrics, fx_risk=fx_risk)
    scenario_data = run_scenario_analysis(inputs)
    sensitivity_data = calculate_full_sensitivity(inputs)
    final_decision = get_final_decision(metrics, risk_data, scenario_data)
    currency_strategy = recommend_currency_strategy(inputs, fx_market, fx_scenarios, fx_exposure)

    return {
        "status": "ok",
        "label": inputs.get("_label", inputs.get("project_label", "Project")),
        "name": inputs.get("project_name", "Unnamed project"),
        "currency": inputs.get("currency", "USD"),
        "inputs": inputs,
        "metrics": metrics,
        "fx_scenarios": fx_scenarios,
        "fx_exposure": fx_exposure,
        "fx_risk": fx_risk,
        "risk_data": risk_data,
        "scenario_data": scenario_data,
        "sensitivity_data": sensitivity_data,
        "final_decision": final_decision,
        "currency_strategy": currency_strategy,
        "warnings": warnings,
    }


def _build_row(bundle: Dict[str, Any], rates: Dict[str, Any]) -> Dict[str, Any]:
    m = bundle["metrics"]
    inputs = bundle["inputs"]
    ccy = bundle["currency"]
    scen = bundle["scenario_data"]
    risk = bundle["fx_risk"]
    strat = bundle["currency_strategy"]
    decision = bundle["final_decision"]
    base_npv = scen["base_case"]["npv"]
    best_npv = scen["best_case"]["npv"]
    worst_npv = scen["worst_case"]["npv"]

    return {
        "Project": bundle["label"],
        "Name": bundle["name"],
        "Currency": ccy,
        "Decision": decision["decision"],
        "Risk Level": bundle["risk_data"]["overall_level"],
        "FX Risk": risk["level"] if risk else "—",
        "FX Score": risk["score"] if risk else None,
        "NPV Swing %": risk["swing_pct"] if risk else 0.0,
        "Strategy": strat["recommendation_text"] if strat else "—",
        "Investment": float(m["initial_investment"]),
        "Investment USD": _to_usd(m["initial_investment"], ccy, rates),
        "NPV": float(m["npv"]),
        "NPV USD": _to_usd(m["npv"], ccy, rates),
        "IRR": float(m["irr"]),
        "MIRR": float(m["mirr"]),
        "PI": float(m["pi"]),
        "ROI": float(m["roi"]),
        "Payback": float(m["payback"]) if m["payback"] != float("inf") else None,
        "WACC": float(m["wacc"]),
        "Project Life": int(float(inputs.get("project_life", 0))),
        "Best NPV": best_npv,
        "Base NPV": base_npv,
        "Worst NPV": worst_npv,
        "Base NPV USD": _to_usd(base_npv, ccy, rates),
    }


def _safe_num(v: Any) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
        return f if f == f else None
    except (TypeError, ValueError):
        return None


def _rank_projects(df: pd.DataFrame) -> pd.DataFrame:
    """Equal-weight normalized composite across the comparison methods."""
    comp = pd.Series([0.0] * len(df), index=df.index)
    used = 0
    for key, (col, direction) in COMPARISON_METHODS.items():
        if col not in df.columns:
            continue
        vals = [_safe_num(v) for v in df[col]]
        if all(v is None for v in vals):
            continue
        if key == "Risk":
            vals = [RISK_RANK.get(str(v), 2) for v in df[col]]
        vmin, vmax = min(vals), max(vals)
        span = vmax - vmin
        for i in df.index:
            v = vals[i]
            if v is None or span == 0:
                comp.loc[i] += 0.5
            else:
                norm = (v - vmin) / span
                if direction == "lower":
                    norm = 1 - norm
                comp.loc[i] += norm
            used += 1

    if used:
        comp = comp / used

    df = df.copy()
    df["Composite Score"] = comp.round(4)
    df["Rank"] = comp.rank(ascending=False, method="min").astype(int)
    return df.sort_values("Rank").reset_index(drop=True)


def _build_recommendation(df: pd.DataFrame, evaluated: List[Dict[str, Any]]) -> Dict[str, Any]:
    if df.empty:
        return {"winner": None, "what": "No valid projects to compare.", "why": "", "evidence": [], "risks": "", "action": ""}

    first = df.iloc[0]
    others = df[df["Rank"] > 1]
    second = others.iloc[0] if len(others) else None
    winner = first["Project"]
    winner_name = first["Name"]

    evidence = []
    for key, (col, direction) in COMPARISON_METHODS.items():
        if col not in df.columns:
            continue
        win_v = _safe_num(first[col])
        sec_v = _safe_num(second[col]) if second is not None else None
        lead = (win_v >= sec_v) if (direction == "higher" and win_v is not None and sec_v is not None) else (win_v <= sec_v if (direction == "lower" and win_v is not None and sec_v is not None) else None)
        win_txt = f"{win_v:,.0f}" if (win_v is not None and col in ("NPV USD", "Base NPV USD")) else (f"{win_v:.2f} yrs" if (win_v is not None and col == "Payback") else (f"{win_v:.3f}" if (win_v is not None and col in ("PI", "Composite Score")) else (f"{win_v:.1%}" if win_v is not None else "N/A")))
        sec_txt = f"{sec_v:,.0f}" if (sec_v is not None and col in ("NPV USD", "Base NPV USD")) else (f"{sec_v:.2f} yrs" if (sec_v is not None and col == "Payback") else (f"{sec_v:.3f}" if (sec_v is not None and col in ("PI",)) else (f"{sec_v:.1%}" if sec_v is not None else "N/A")))
        if lead is None:
            evidence.append(f"{key}: {win_txt} (second: {sec_txt})")
        else:
            evidence.append(f"{key}: {win_txt} ({'leads' if lead else 'trails'} second {sec_txt})")

    score_v = _safe_num(first["Composite Score"])
    base_v = _safe_num(first["Base NPV USD"])
    winner_bundle = next((e for e in evaluated if e.get("label") == winner and e.get("status") == "ok"), None)

    risk_txt = "n/a"
    base_txt = f"{base_v:,.0f}" if base_v is not None else "n/a"
    fxd = ""
    if winner_bundle:
        risk_txt = winner_bundle["risk_data"]["overall_level"]
        fxr = winner_bundle["fx_risk"]
        if fxr:
            fxd = f" with {fxr['level']} FX risk ({fxr['swing_pct']:.1f}% NPV swing)"
        d = winner_bundle["final_decision"]
        fxd += f" and a per-project recommendation of {d['decision']}"

    why = (
        f"{winner_name} ranks first with the highest composite score "
        f"({score_v:.3f}) across an equal-weighted set of measures (NPV, IRR, MIRR, PI, "
        f"ROI, payback, base-case NPV and risk). Base-case NPV (USD equivalent): {base_txt}; "
        f"risk {risk_txt}{fxd}. The winner is decided entirely by the computed results — no "
        "currency (USD, ZAR or ZiG) is treated as automatically superior."
    )

    what = f"Project {winner} ({winner_name})"
    action = (
        f"Recommendation for management: proceed with Project {winner} ({winner_name}) under "
        f"the current assumptions, subject to normal governance and due diligence. "
        "Re-run this comparison whenever exchange rates change materially or when any project "
        "assumption is updated."
    )

    return {
        "winner": str(winner),
        "winner_name": winner_name,
        "rank_order": [r["Project"] for r in df.itertuples()],
        "what": what,
        "why": why,
        "evidence": evidence,
        "risks": risk_txt,
        "action": action,
        "score": float(score_v if score_v is not None else 0.0),
    }


def build_comparison(
    projects: List[Dict[str, Any]],
    fx_market: Dict[str, Any],
    fx_rates: Dict[str, Any],
    mode: str = "Two Projects",
) -> Dict[str, Any]:
    n = len(projects)
    if n not in (2, 3):
        raise ValueError("Comparison requires exactly 2 or 3 projects.")

    evaluated = [evaluate_project(p, fx_market) for p in projects]
    labels = [e.get("label", f"Project {PROJECT_LABELS[i]}") for i, e in enumerate(evaluated)]
    okay = [e for e in evaluated if e["status"] == "ok"]

    if not okay:
        return {
            "mode": mode,
            "n": n,
            "labels": labels,
            "evaluated": evaluated,
            "comparison_df": pd.DataFrame(),
            "ranking_df": pd.DataFrame(),
            "composite_scores": {},
            "recommendation": {"winner": None, "what": "No valid projects to compare.", "why": "", "evidence": [], "risks": "", "action": ""},
            "invalid": evaluated,
        }

    df = pd.DataFrame([_build_row(e, fx_rates) for e in okay])
    ranked = _rank_projects(df)
    rec = _build_recommendation(ranked, evaluated)

    return {
        "mode": mode,
        "n": n,
        "labels": labels,
        "evaluated": evaluated,
        "comparison_df": df,
        "ranking_df": ranked,
        "composite_scores": dict(zip(ranked["Project"], ranked["Composite Score"])),
        "recommendation": rec,
        "invalid": [e for e in evaluated if e["status"] != "ok"],
        "fx_rates": fx_rates,
    }


def template_name_for(template_id: str) -> str:
    for t in get_project_type_list():
        if t["id"] == template_id:
            return t["name"]
    return "Generic / Custom Project"