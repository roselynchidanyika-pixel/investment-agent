import requests
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional, Tuple

from calculations import calculate_all_metrics

# Rates are stored as units of each currency per 1 USD.
FALLBACK_RATES = {"USD": 1.0, "ZIG": 13.50, "ZAR": 18.50}

TREND_DAYS = 30

FX_SCENARIOS = [
    {"id": "zig_plus5", "label": "ZiG +5%", "description": "Zimbabwe Gold (ZiG) strengthens by 5% against the US dollar."},
    {"id": "zig_minus5", "label": "ZiG -5%", "description": "Zimbabwe Gold (ZiG) weakens by 5% against the US dollar."},
    {"id": "usd_plus5", "label": "USD +5%", "description": "US dollar strengthens by 5% against ZiG and ZAR."},
    {"id": "usd_minus5", "label": "USD -5%", "description": "US dollar weakens by 5% against ZiG and ZAR."},
    {"id": "zar_plus5", "label": "ZAR +5%", "description": "South African rand strengthens by 5% against the US dollar."},
    {"id": "zar_minus5", "label": "ZAR -5%", "description": "South African rand weakens by 5% against the US dollar."},
]

STRATEGY_OPTIONS = ["USE_ZIG", "PRESERVE_USD", "CONVERT_USD_TO_ZIG", "HOLD_USD", "REVIEW"]

STRATEGY_TEXT = {
    "USE_ZIG": "USE ZiG",
    "PRESERVE_USD": "PRESERVE USD",
    "CONVERT_USD_TO_ZIG": "CONVERT USD TO ZiG",
    "HOLD_USD": "HOLD USD",
    "REVIEW": "REVIEW",
}


def _fetch_current_rates() -> Tuple[Dict[str, float], str]:
    """Fetch current rates from public APIs; falls back to managed reference rates."""
    rates = dict(FALLBACK_RATES)
    source = "estimate"
    try:
        resp = requests.get("https://open.er-api.com/v6/latest/USD", timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("result") == "success":
                api = data.get("rates", {})
                if "ZAR" in api and api["ZAR"]:
                    rates["ZAR"] = float(api["ZAR"])
                    source = "live"
    except Exception:
        pass
    return rates, source


def _fetch_zar_history() -> Dict[str, float]:
    """Fetch ~30 days of ZAR history; returns {date_str: zar_per_usd}."""
    history = {}
    try:
        today = date.today()
        start = today - timedelta(days=TREND_DAYS + 5)
        resp = requests.get(
            "https://api.exchangerate-api.com/history",
            params={"base": "USD", "start_date": start.isoformat(), "end_date": today.isoformat()},
            timeout=8,
        )
        if resp.status_code == 200:
            data = resp.json()
            rates_by_date = data.get("rates", {})
            for day, day_rates in rates_by_date.items():
                if isinstance(day_rates, dict) and "ZAR" in day_rates:
                    try:
                        history[day] = float(day_rates["ZAR"])
                    except (TypeError, ValueError):
                        continue
    except Exception:
        pass
    return history


def _daily_and_trend_for_zar(history: Dict[str, float]) -> Tuple[float, float, str]:
    if not history:
        return 0.0, 0.0, "estimate"
    dates = sorted(history.keys())
    latest = history[dates[-1]]
    prev = history[dates[-2]] if len(dates) >= 2 else latest
    first = history[dates[0]]
    daily = ((latest - prev) / prev) * 100.0 if prev else 0.0
    trend = ((latest - first) / first) * 100.0 if first else 0.0
    return daily, trend, "live"


def get_fx_market() -> Dict[str, Any]:
    """Build the FX market snapshot used across the dashboard."""
    rates, source = _fetch_current_rates()
    history = _fetch_zar_history()
    zar_daily, zar_trend, zar_source = _daily_and_trend_for_zar(history)
    now = datetime.now()

    zig_usd = rates["ZIG"] if rates["ZIG"] else 0.0
    zar_usd = rates["ZAR"] if rates["ZAR"] else 0.0

    pairs = [
        {"pair": "USD/ZiG", "rate": zig_usd, "rate_ccy": "ZiG",
         "daily_change_pct": 0.0, "month_trend_pct": 0.0, "source": "estimate",
         "meaning": "Zimbabwe Gold per 1 US dollar"},
        {"pair": "ZiG/USD", "rate": 1.0 / zig_usd if zig_usd else 0.0, "rate_ccy": "USD",
         "daily_change_pct": 0.0, "month_trend_pct": 0.0, "source": "estimate",
         "meaning": "US dollars per 1 Zimbabwe Gold"},
        {"pair": "USD/ZAR", "rate": zar_usd, "rate_ccy": "ZAR",
         "daily_change_pct": zar_daily, "month_trend_pct": zar_trend, "source": zar_source,
         "meaning": "South African rand per 1 US dollar"},
        {"pair": "ZAR/USD", "rate": 1.0 / zar_usd if zar_usd else 0.0, "rate_ccy": "USD",
         "daily_change_pct": -zar_daily, "month_trend_pct": -zar_trend, "source": zar_source,
         "meaning": "US dollars per 1 South African rand"},
    ]

    fx_risk_score, fx_risk_level = _compute_fx_risk(pairs)

    return {
        "current": rates,
        "pairs": pairs,
        "as_of": now,
        "source": source,
        "fx_risk_level": fx_risk_level,
        "fx_risk_score": fx_risk_score,
        "is_live": any(p["source"] == "live" for p in pairs),
    }


def _compute_fx_risk(pairs: List[Dict[str, Any]]) -> Tuple[float, str]:
    score = 2.0  # baseline structural risk for an emerging-market, multi-currency setting
    for p in pairs:
        if p.get("source") != "live":
            continue
        vol = max(abs(p.get("daily_change_pct", 0.0)), abs(p.get("month_trend_pct", 0.0)))
        if vol >= 5.0:
            score += 3.0
        elif vol >= 2.0:
            score += 2.0
        elif vol >= 0.5:
            score += 1.0
    if any(p["pair"] == "USD/ZiG" for p in pairs):
        score += 1.0  # ZiG is a young, thinly traded currency — structural uncertainty
    score = min(10.0, max(1.0, round(score, 1)))

    if score <= 3.0:
        level = "LOW"
    elif score <= 5.0:
        level = "MODERATE"
    else:
        level = "HIGH"
    return score, level


def _pair_moves(scenario_id: str) -> Dict[str, float]:
    """Change in the value of each currency relative to USD. + = currency strengthens vs USD."""
    moves = {"USD": 0.0, "ZIG": 0.0, "ZAR": 0.0}
    if scenario_id == "zig_plus5":
        moves["ZIG"] = 0.05
    elif scenario_id == "zig_minus5":
        moves["ZIG"] = -0.05
    elif scenario_id == "usd_plus5":
        # USD strengthens 5% -> ZiG & ZAR weaken by 1/1.05 - 1
        moves["ZIG"] = 1 / 1.05 - 1
        moves["ZAR"] = 1 / 1.05 - 1
    elif scenario_id == "usd_minus5":
        moves["ZIG"] = 1 / 0.95 - 1
        moves["ZAR"] = 1 / 0.95 - 1
    elif scenario_id == "zar_plus5":
        moves["ZAR"] = 0.05
    elif scenario_id == "zar_minus5":
        moves["ZAR"] = -0.05
    return moves


def _rel_move(currency: str, base: str, moves: Dict[str, float]) -> float:
    """Change of `currency` relative to `base`, given changes vs USD."""
    num = 1.0 + moves.get(currency, 0.0)
    den = 1.0 + moves.get(base, 0.0)
    if den == 0:
        return 0.0
    return num / den - 1.0


def _primary_foreign_currency(base: str) -> str:
    if base in ("ZAR",):
        return "USD"
    if base == "ZIG":
        return "USD"
    return "ZIG"


def _clamped(value, low=0.0, high=1.0) -> float:
    return min(high, max(low, float(value)))


def apply_fx_scenario_adjustment(inputs: Dict[str, Any], scenario_id: str) -> Dict[str, Any]:
    """Adjust inputs for an FX move. Returns a copy of inputs with revenue/cost/investment scaled."""
    base = str(inputs.get("currency", "USD")).upper()
    moves = _pair_moves(scenario_id)

    zig_rev = _clamped(inputs.get("zig_revenue_share", 0.0))
    zar_rev = _clamped(inputs.get("zar_revenue_share", 0.0))
    usd_rev = _clamped(1.0 - zig_rev - zar_rev)
    zig_cost = _clamped(inputs.get("zig_cost_share", 0.0))
    zar_cost = _clamped(inputs.get("zar_cost_share", 0.0))
    usd_cost = _clamped(1.0 - zig_cost - zar_cost)

    currencies = ["USD", "ZIG", "ZAR"]
    foreign_rev = {c: 0.0 for c in currencies}
    foreign_rev["ZIG"] = zig_rev if base != "ZIG" else 0.0
    foreign_rev["ZAR"] = zar_rev if base != "ZAR" else 0.0
    foreign_rev["USD"] = usd_rev if base != "USD" else 0.0

    foreign_cost = {c: 0.0 for c in currencies}
    foreign_cost["ZIG"] = zig_cost if base != "ZIG" else 0.0
    foreign_cost["ZAR"] = zar_cost if base != "ZAR" else 0.0
    foreign_cost["USD"] = usd_cost if base != "USD" else 0.0

    rev_mult = 1.0 + sum(_rel_move(c, base, moves) * share for c, share in foreign_rev.items())
    cost_mult = 1.0 + sum(_rel_move(c, base, moves) * share for c, share in foreign_cost.items())

    inv_fx_share = _clamped(inputs.get("investment_fx_share", 0.0))
    primary_foreign = _primary_foreign_currency(base)
    inv_mult = 1.0 + inv_fx_share * _rel_move(primary_foreign, base, moves)

    adjusted = dict(inputs)
    adjusted["annual_revenue"] = float(inputs.get("annual_revenue", 0.0)) * rev_mult
    adjusted["operating_costs"] = float(inputs.get("operating_costs", 0.0)) * cost_mult
    adjusted["initial_investment"] = float(inputs.get("initial_investment", 0.0)) * inv_mult
    return adjusted


def run_fx_scenario_analysis(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Run ±5% FX scenarios and recompute full project metrics for each."""
    base_case = calculate_all_metrics(inputs)
    results = []
    details = {}

    for scenario in FX_SCENARIOS:
        adjusted = apply_fx_scenario_adjustment(inputs, scenario["id"])
        metrics = calculate_all_metrics(adjusted)
        cash_flow_total = sum(metrics.get("cash_flows", [])[1:])
        npv_delta = metrics["npv"] - base_case["npv"]
        results.append({
            "scenario_id": scenario["id"],
            "label": scenario["label"],
            "description": scenario["description"],
            "npv": metrics["npv"],
            "npv_delta": npv_delta,
            "irr": metrics["irr"],
            "payback": metrics["payback"],
            "cash_flow_total": cash_flow_total,
            "investment_cost": metrics["initial_investment"],
            "npv_status": metrics["npv_status"]["decision"],
        })
        details[scenario["id"]] = {
            "metrics": metrics,
            "adjusted_inputs": adjusted,
            "npv_delta": npv_delta,
        }

    base_npv = base_case["npv"]
    if base_npv == 0:
        base_npv = max((abs(r["npv"]) for r in results), default=0) or 1.0

    max_delta = max((abs(r["npv_delta"]) / abs(base_npv)) for r in results) if results else 0.0
    max_delta = min(max_delta, 100.0)

    worst_acc = [r for r in results if r["npv_status"] == "REJECT"]

    if max_delta >= 0.20:
        fx_sensitivity_level = "HIGH"
    elif max_delta >= 0.07:
        fx_sensitivity_level = "MODERATE"
    else:
        fx_sensitivity_level = "LOW"

    import pandas as pd

    table = pd.DataFrame([{
        "Scenario": r["label"],
        "NPV": r["npv"],
        "NPV Change": f"{((r['npv'] - base_case['npv']) / base_npv) * 100:+.1f}%",
        "IRR": r["irr"],
        "Payback (yrs)": r["payback"] if r["payback"] != float("inf") else "N/A",
        "Cash Flows": r["cash_flow_total"],
        "Investment Cost": r["investment_cost"],
        "Decision": r["npv_status"],
    } for r in results])

    return {
        "base_case_npv": base_case["npv"],
        "base_case_irr": base_case["irr"],
        "results": results,
        "details": details,
        "table": table,
        "max_npv_swing_pct": max_delta * 100.0,
        "fx_sensitivity_level": fx_sensitivity_level,
        "scenarios_declined": [r["label"] for r in worst_acc],
    }


def assess_currency_exposure(inputs: Dict[str, Any]) -> Dict[str, Any]:
    base = str(inputs.get("currency", "USD")).upper()
    zig_rev = _clamped(inputs.get("zig_revenue_share", 0.0))
    zar_rev = _clamped(inputs.get("zar_revenue_share", 0.0))
    zig_cost = _clamped(inputs.get("zig_cost_share", 0.0))
    zar_cost = _clamped(inputs.get("zar_cost_share", 0.0))
    inv_fx = _clamped(inputs.get("investment_fx_share", 0.0))

    if base == "USD":
        rev_fx = zig_rev + zar_rev
        cost_fx = zig_cost + zar_cost
    elif base in ("ZIG", "ZAR"):
        usd_rev = _clamped(1.0 - zig_rev - zar_rev)
        usd_cost = _clamped(1.0 - zig_cost - zar_cost)
        if base == "ZIG":
            rev_fx = zar_rev + usd_rev
            cost_fx = zar_cost + usd_cost
        else:
            rev_fx = zig_rev + usd_rev
            cost_fx = zig_cost + usd_cost
    else:
        rev_fx = zig_rev + zar_rev
        cost_fx = zig_cost + zar_cost

    net = 0.5 * rev_fx + 0.3 * cost_fx + 0.2 * inv_fx
    score = round(min(10.0, net * 10.0), 1)

    if score <= 3.0:
        level = "LOW"
    elif score <= 6.0:
        level = "MODERATE"
    else:
        level = "HIGH"

    explanation = (
        f"Approximately {rev_fx:.0%} of revenue, {cost_fx:.0%} of operating costs and "
        f"{inv_fx:.0%} of the investment outlay are exposed to currency movements relative to "
        f"the base currency ({base}). Exchange-rate shifts change the base-currency-equivalent value "
        f"of these flows, which feeds directly through to NPV, IRR and payback in the FX scenario analysis."
    )
    return {
        "level": level,
        "score": score,
        "net_exposure": net,
        "revenue_exposure": rev_fx,
        "cost_exposure": cost_fx,
        "investment_exposure": inv_fx,
        "explanation": explanation,
    }


def recommend_currency_strategy(
    inputs: Dict[str, Any],
    fx_market: Dict[str, Any],
    fx_scenarios: Dict[str, Any],
    exposure: Dict[str, Any],
) -> Dict[str, Any]:
    base = str(inputs.get("currency", "USD")).upper()
    fx_risk_level = fx_market.get("fx_risk_level", "MODERATE")
    fx_risk_score = fx_market.get("fx_risk_score", 5.0)

    net_exposure = exposure.get("net_exposure", 0.0)
    rev_fx = exposure.get("revenue_exposure", 0.0)
    cost_fx = exposure.get("cost_exposure", 0.0)
    inv_fx = exposure.get("investment_exposure", 0.0)

    liquidity_months = float(inputs.get("liquidity_buffer_months", 6))
    npv_swing = abs(fx_scenarios.get("max_npv_swing_pct", 0.0))
    scenario_npvs = [r["npv"] for r in fx_scenarios.get("results", [])]
    min_npv = min(scenario_npvs) if scenario_npvs else 0.0
    max_npv = max(scenario_npvs) if scenario_npvs else 0.0

    zig_rev = _clamped(inputs.get("zig_revenue_share", 0.0))
    zig_cost = _clamped(inputs.get("zig_cost_share", 0.0))
    zar_rev = _clamped(inputs.get("zar_revenue_share", 0.0))
    usd_rev_share = _clamped(1.0 - zig_rev - zar_rev)

    local_operations = (zig_rev + zig_cost) / 2.0
    if base == "ZIG":
        local_operations = max(local_operations, (1 - zar_rev - usd_rev_share + zig_cost) / 2.0)
    hard_currency_revenue = usd_rev_share if base == "USD" else usd_rev_share + (0.0 if base == "ZAR" else 0.0)

    scores = {s: 0.0 for s in STRATEGY_OPTIONS}

    if local_operations >= 0.7 and fx_risk_level in ("LOW", "MODERATE") and npv_swing < 15:
        scores["USE_ZIG"] += 3
    if base != "USD" and hard_currency_revenue < 0.3 and fx_risk_level != "HIGH":
        scores["USE_ZIG"] += 1

    if hard_currency_revenue >= 0.5:
        scores["PRESERVE_USD"] += 3
    if fx_risk_level == "HIGH" and hard_currency_revenue >= 0.3:
        scores["PRESERVE_USD"] += 2
    if npv_swing >= 15 and hard_currency_revenue >= 0.3:
        scores["PRESERVE_USD"] += 1

    if zig_cost >= 0.5 and hard_currency_revenue >= 0.3 and fx_risk_level in ("LOW", "MODERATE"):
        scores["CONVERT_USD_TO_ZIG"] += 3
    if zig_cost >= 0.3 and inv_fx <= 0.3 and npv_swing < 15:
        scores["CONVERT_USD_TO_ZIG"] += 1

    if net_exposure <= 0.3 and fx_risk_level == "LOW":
        scores["HOLD_USD"] += 3
    if net_exposure <= 0.5 and liquidity_months >= 4:
        scores["HOLD_USD"] += 1

    if (fx_risk_level == "HIGH" and net_exposure >= 0.5) or npv_swing >= 25:
        scores["REVIEW"] += 4
    if fx_risk_level == "HIGH" and liquidity_months < 3:
        scores["REVIEW"] += 2

    strategy = max(scores, key=scores.get)
    runner_up = sorted(scores.items(), key=lambda kv: -kv[1])[1][0]

    key_factors = [
        f"FX risk is assessed as {fx_risk_level} (score {fx_risk_score:.1f}/10) based on observed "
        f"30-day volatility where live data is available.",
        f"Net currency exposure is {exposure['level']}: {rev_fx:.0%} of revenue and {cost_fx:.0%} of "
        f"operating costs are sensitive to exchange-rate movements.",
        f"Across the ±5% FX scenarios, NPV ranges from {format_num(min_npv)} to {format_num(max_npv)} "
        f"(a maximum swing of {npv_swing:.1f}%).",
        f"Liquidity buffer: {liquidity_months:.0f} months of operating cover.",
        f"Base currency of the project is {base}.",
    ]

    if strategy == "USE_ZIG":
        reason = (
            f"The project operates predominantly in the local currency ({zig_rev:.0%} of revenue, "
            f"{zig_cost:.0%} of costs in ZiG) with {fx_risk_level} FX risk. Running the project in ZiG "
            f"removes conversion costs and keeps earnings in the currency in which operating costs are paid. "
            f"There is uncertainty in the forward ZiG rate; this recommendation is based on the current balance "
            f"of exposure and the scenario analysis, not on any assumption about the future direction of the "
            f"ZiG exchange rate — monitor actual in-market rates."
        )
    elif strategy == "PRESERVE_USD":
        reason = (
            f"Foreign-currency revenue represents a material share of cash inflow and FX risk is "
            f"{fx_risk_level}. Under the ±5% scenarios project NPV moves by up to {npv_swing:.1f}%. "
            f"Holding export earnings in USD protects the purchasing power of those cash flows against "
            f"adverse currency moves. This is a risk-management position based on current volatility and "
            f"scenario outcomes — it is not a directional forecast of USD, ZiG or ZAR values."
        )
    elif strategy == "CONVERT_USD_TO_ZIG":
        reason = (
            f"A large share of operating costs ({zig_cost:.0%}) are paid in ZiG while USD inflows exceed "
            f"USD-denominated needs (imported content {inv_fx:.0%}). Converting surplus USD to ZiG only for "
            f"cost coverage reduces conversion friction and matches cash inflows to outflows. The recommendation "
            f"rests on the scenario analysis (NPV swing {npv_swing:.1f}%) and current FX risk "
            f"({fx_risk_level}); future exchange-rate outcomes remain uncertain and should be monitored."
        )
    elif strategy == "HOLD_USD":
        reason = (
            f"Currency exposure is low (net {net_exposure:.0%}) and current FX risk is {fx_risk_level}. "
            f"No active currency repositioning is indicated; holding the project's USD bias with the existing "
            f"{liquidity_months:.0f}-month liquidity buffer is adequate. Rates could still move, so periodic "
            f"re-assessment of the exposure mix is recommended."
        )
    else:
        reason = (
            f"Signals are currently conflicting: FX risk is {fx_risk_level}, net exposure is "
            f"{net_exposure:.0%}, and the ±5% scenarios swing NPV by {npv_swing:.1f}%. Before committing to "
            f"a currency position, re-examine the exposure mix, hedge costs and liquidity headroom. The appropriate "
            f"action depends on monitored in-market rates; no currency's future value is assumed in this assessment."
        )

    return {
        "strategy": strategy,
        "recommendation_text": STRATEGY_TEXT.get(strategy, strategy),
        "reason": reason,
        "key_fx_factors": key_factors,
        "runner_up": runner_up,
        "fx_risk_level": fx_risk_level,
        "fx_risk_score": fx_risk_score,
        "max_npv_swing_pct": npv_swing,
        "npv_range": (min_npv, max_npv),
        "net_exposure": net_exposure,
        "is_review": strategy == "REVIEW",
    }


def format_num(value: float) -> str:
    return f"{value:,.0f}"


def get_fx_risk_summary(inputs: Dict[str, Any], fx_market: Dict[str, Any], fx_scenarios: Dict[str, Any]) -> Dict[str, Any]:
    exposure = assess_currency_exposure(inputs)
    swing = abs(fx_scenarios.get("max_npv_swing_pct", 0.0))

    score = fx_market.get("fx_risk_score", 5.0)
    if swing >= 20.0:
        score = min(10.0, score + 2.0)
    elif swing >= 7.0:
        score = min(10.0, score + 1.0)

    if float(score) <= 3.0:
        level = "LOW"
    elif float(score) <= 5.0:
        level = "MODERATE"
    else:
        level = "HIGH"

    return {
        "level": level,
        "score": round(float(score), 1),
        "exposure": exposure,
        "swing_pct": swing,
        "explanation": (
            f"FX risk for this project is assessed as {level} (score {score:.1f}/10). The project's net "
            f"currency exposure is {exposure['level']}, and NPV moves by up to {swing:.1f}% across the "
            f"±5% exchange-rate scenarios. Rates are live where available; ZiG values are estimates "
            f"pending a public ZIG feed."
        ),
    }