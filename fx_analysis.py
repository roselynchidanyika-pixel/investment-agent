import os
import json
import requests
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional, Tuple

from calculations import calculate_all_metrics

# Rates are stored as units of each currency per 1 USD.
FALLBACK_RATES = {"USD": 1.0, "ZIG": 13.50, "ZAR": 18.50}

# Persistence for the stored-rate history (live fetches + manual overrides).
FX_STORE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fx_rate_store.json")

# Board statuses (legend).
STATUS_LIVE = "LIVE"
STATUS_STORED = "STORED"
STATUS_STALE = "STALE"
STATUS_MANUAL = "MANUAL OVERRIDE"
STATUS_UNAVAILABLE = "UNAVAILABLE"

STALE_HOURS = 24.0

LIVE_SOURCES = {
    "open_er": "open.er-api.com",
    "frankfurter": "frankfurter.app (ECB)",
}

BOARD_PAIRS = ["USD/ZAR", "ZAR/USD", "USD/ZWG", "ZWG/USD", "ZAR/ZWG", "ZWG/ZAR"]

PAIR_MEANINGS = {
    "USD/ZAR": "South African rand per 1 US dollar",
    "ZAR/USD": "US dollars per 1 South African rand",
    "USD/ZWG": "Zimbabwe Gold (ZiG) per 1 US dollar",
    "ZWG/USD": "US dollars per 1 Zimbabwe Gold",
    "ZAR/ZWG": "Zimbabwe Gold per 1 South African rand",
    "ZWG/ZAR": "South African rand per 1 Zimbabwe Gold",
}

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


def _fetch_open_er() -> Dict[str, float]:
    """Fetch USD-based rates from open.er-api.com (preferred live source)."""
    try:
        resp = requests.get("https://open.er-api.com/v6/latest/USD", timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("result") == "success":
                api = data.get("rates", {})
                out = {}
                if api.get("ZAR"):
                    out["ZAR"] = float(api["ZAR"])
                if api.get("ZWG"):
                    out["ZWG"] = float(api["ZWG"])
                return out
    except Exception:
        pass
    return {}


def _fetch_frankfurter() -> Dict[str, float]:
    """Fallback live source: frankfurter.app / ECB."""
    try:
        resp = requests.get(
            "https://api.frankfurter.app/latest",
            params={"from": "USD", "to": "ZAR,ZWG"},
            timeout=8,
        )
        if resp.status_code == 200:
            data = resp.json()
            rates = data.get("rates", {})
            out = {}
            if rates.get("ZAR"):
                out["ZAR"] = float(rates["ZAR"])
            if rates.get("ZWG"):
                out["ZWG"] = float(rates["ZWG"])
            return out
    except Exception:
        pass
    return {}


def fetch_live_rates() -> Tuple[Dict[str, float], str]:
    """Fetch current USD/ZAR and USD/ZWG live rates.

    Returns (rates, source) where source is one of LIVE_SOURCES keys or "none".
    """
    live = _fetch_open_er()
    if live:
        return live, "open_er"
    live = _fetch_frankfurter()
    if live:
        return live, "frankfurter"
    return {}, "none"


def fetch_zar_trend() -> Tuple[float, float]:
    """Return (daily % change, 30-day trend %) for USD/ZAR from exchange-rate history."""
    history = _fetch_zar_history()
    daily, trend, _ = _daily_and_trend_for_zar(history)
    return daily, trend


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


def load_fx_store(path: Optional[str] = None) -> Dict[str, Any]:
    """Load the persisted stored-rate history (live fetches + manual overrides)."""
    try:
        p = path or FX_STORE_PATH
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_fx_store(store: Dict[str, Any], path: Optional[str] = None) -> None:
    """Persist the stored-rate history to disk. Never raises on failure."""
    try:
        p = path or FX_STORE_PATH
        with open(p, "w", encoding="utf-8") as f:
            json.dump(store, f, indent=2)
    except Exception:
        pass


def _parse_ts(raw: Any) -> Optional[datetime]:
    if isinstance(raw, datetime):
        return raw
    if raw is None:
        return None
    try:
        return datetime.fromisoformat(str(raw))
    except (ValueError, TypeError):
        return None


def _fmt_ts(ts: Optional[datetime]) -> str:
    if ts is None:
        return "—"
    return ts.strftime("%Y-%m-%dT%H:%M:%S") if ts.tzinfo is None else ts.isoformat(timespec="seconds")


def _resolve_base_entry(
    pair_key: str,
    live_rates: Dict[str, float],
    live_source: str,
    store: Dict[str, Any],
    overrides: Dict[str, Any],
    now: datetime,
) -> Dict[str, Any]:
    """Resolve a base pair (USD_ZAR / USD_ZWG) with full status precedence.

    Manual override always wins; then a fresh live rate; then stored history
    (STORED if <= 24h old, otherwise shown as STALE); finally UNAVAILABLE.
    """
    ov = overrides.get(pair_key) if isinstance(overrides.get(pair_key), dict) else None
    if ov:
        try:
            rate = float(ov.get("rate"))
        except (TypeError, ValueError):
            rate = None
        if rate:
            return {
                "rate": rate,
                "source_label": ov.get("source_label", "Manual override"),
                "timestamp": _parse_ts(ov.get("timestamp")) or now,
                "status": STATUS_MANUAL,
                "origin": "manual",
            }

    live_key = "ZWG" if pair_key == "USD_ZWG" else "ZAR"
    if live_rates.get(live_key):
        return {
            "rate": float(live_rates[live_key]),
            "source_label": LIVE_SOURCES.get(live_source, live_source or "live API"),
            "timestamp": now,
            "status": STATUS_LIVE,
            "origin": "live",
        }

    stored = store.get(pair_key) if isinstance(store.get(pair_key), dict) else None
    if stored:
        try:
            rate = float(stored.get("rate"))
        except (TypeError, ValueError):
            rate = None
        if rate:
            ts = _parse_ts(stored.get("timestamp"))
            age_hours = None
            if ts is not None:
                try:
                    age_hours = (now - ts).total_seconds() / 3600.0
                except TypeError:
                    age_hours = None
            status = STATUS_STORED if (age_hours is not None and age_hours <= STALE_HOURS) else STATUS_STALE
            return {
                "rate": rate,
                "source_label": stored.get("source_label", stored.get("source", "stored history")),
                "timestamp": ts,
                "status": status,
                "origin": stored.get("origin", "stored"),
            }

    return {"rate": None, "source_label": "—", "timestamp": None, "status": STATUS_UNAVAILABLE, "origin": None}


def _derived_label(a: str, b: Optional[str] = None) -> str:
    if b is None or a == b:
        return f"{a} (derived)"
    return f"{a} / {b} (derived)"


def _derived_status(statuses: List[str]) -> str:
    if any(s == STATUS_UNAVAILABLE for s in statuses):
        return STATUS_UNAVAILABLE
    if any(s == STATUS_STALE for s in statuses):
        return STATUS_STALE
    if any(s == STATUS_MANUAL for s in statuses):
        return STATUS_MANUAL
    if any(s == STATUS_STORED for s in statuses):
        return STATUS_STORED
    return STATUS_LIVE


def build_exchange_board(
    live_rates: Optional[Dict[str, float]] = None,
    live_source: str = "",
    store: Optional[Dict[str, Any]] = None,
    overrides: Optional[Dict[str, Any]] = None,
    now: Optional[datetime] = None,
    zar_daily: float = 0.0,
    zar_trend: float = 0.0,
) -> Dict[str, Any]:
    """Build the six-pair Live Exchange Rate Board with full status labelling.

    Every pair carries {pair, key, rate, status, source_label, timestamp,
    daily_change_pct, month_trend_pct, meaning}. A stale stored rate is never
    silently used — it is always shown with status STALE.
    """
    live_rates = live_rates or {}
    store = store or {}
    overrides = overrides or {}
    now = now if now is not None else datetime.now()

    base_zar = _resolve_base_entry("USD_ZAR", live_rates, live_source, store, overrides, now)
    base_zwg = _resolve_base_entry("USD_ZWG", live_rates, live_source, store, overrides, now)

    usd_zar = base_zar["rate"]
    usd_zwg = base_zwg["rate"]

    def row(pair_key, rate, status, source_label, timestamp, daily, trend):
        return {
            "pair": pair_key.replace("_", "/"),
            "key": pair_key,
            "rate": rate,
            "status": status,
            "source_label": source_label,
            "timestamp": timestamp,
            "daily_change_pct": daily,
            "month_trend_pct": trend,
            "meaning": PAIR_MEANINGS.get(pair_key.replace("_", "/"), pair_key),
        }

    rows = []

    # USD/ZAR and ZAR/USD
    rows.append(row("USD_ZAR", usd_zar, base_zar["status"], base_zar["source_label"],
                    base_zar["timestamp"], zar_daily, zar_trend))
    if usd_zar:
        rows.append(row("ZAR_USD", 1.0 / usd_zar,
                        _derived_status([base_zar["status"]]),
                        _derived_label(base_zar["source_label"]),
                        base_zar["timestamp"], -zar_daily, -zar_trend))
    else:
        rows.append(row("ZAR_USD", None, STATUS_UNAVAILABLE, "—", None, 0.0, 0.0))

    # USD/ZWG and ZWG/USD
    rows.append(row("USD_ZWG", usd_zwg, base_zwg["status"], base_zwg["source_label"],
                    base_zwg["timestamp"], 0.0, 0.0))
    if usd_zwg:
        rows.append(row("ZWG_USD", 1.0 / usd_zwg,
                        _derived_status([base_zwg["status"]]),
                        _derived_label(base_zwg["source_label"]),
                        base_zwg["timestamp"], 0.0, 0.0))
    else:
        rows.append(row("ZWG_USD", None, STATUS_UNAVAILABLE, "—", None, 0.0, 0.0))

    # ZAR/ZWG and ZWG/ZAR (cross pairs)
    if usd_zar and usd_zwg:
        cross_status = _derived_status([base_zar["status"], base_zwg["status"]])
        cross_src = _derived_label(base_zar["source_label"], base_zwg["source_label"])
        rows.append(row("ZAR_ZWG", usd_zwg / usd_zar, cross_status, cross_src, now, 0.0, 0.0))
        rows.append(row("ZWG_ZAR", usd_zar / usd_zwg, cross_status, cross_src, now, 0.0, 0.0))
    else:
        rows.append(row("ZAR_ZWG", None, STATUS_UNAVAILABLE,
                        "—" if not (usd_zar or usd_zwg) else _derived_label(base_zar["source_label"], base_zwg["source_label"]),
                        None, 0.0, 0.0))
        rows.append(row("ZWG_ZAR", None, STATUS_UNAVAILABLE,
                        "—" if not (usd_zar or usd_zwg) else _derived_label(base_zar["source_label"], base_zwg["source_label"]),
                        None, 0.0, 0.0))

    fx_risk_score, fx_risk_level = _compute_fx_risk(rows)

    effective_zwg_usd = usd_zwg or FALLBACK_RATES["ZIG"]
    effective_zar_usd = usd_zar or FALLBACK_RATES["ZAR"]

    return {
        "current": {
            "USD": 1.0,
            "ZIG": effective_zwg_usd,
            "ZWG": effective_zwg_usd,
            "ZAR": effective_zar_usd,
            "ZAR_ZWG": effective_zwg_usd / effective_zar_usd if effective_zar_usd else 0.0,
        },
        "pairs": rows,
        "as_of": now,
        "live_source": live_source,
        "fx_risk_level": fx_risk_level,
        "fx_risk_score": fx_risk_score,
        "is_live": any(r["status"] in (STATUS_LIVE, STATUS_STORED) for r in rows),
        "store_count": len(store),
    }


def get_fx_market() -> Dict[str, Any]:
    """Build a standalone FX market snapshot (live where available).

    Backward-compatible wrapper; the dashboard uses build_exchange_board with
    the persisted store and manual overrides instead.
    """
    live, source = fetch_live_rates()
    zar_daily, zar_trend = fetch_zar_trend()
    return build_exchange_board(
        live_rates=live,
        live_source=source,
        store=load_fx_store(),
        now=datetime.now(),
        zar_daily=zar_daily,
        zar_trend=zar_trend,
    )


def _compute_fx_risk(pairs: List[Dict[str, Any]]) -> Tuple[float, str]:
    score = 2.0  # baseline structural risk for an emerging-market, multi-currency setting
    for p in pairs:
        if p["pair"] in ("USD/ZWG", "ZWG/USD") and p.get("status") != STATUS_UNAVAILABLE:
            score += 1.0  # ZiG is a young, thinly traded currency — structural uncertainty
        if p.get("status") not in (STATUS_LIVE, STATUS_STORED):
            continue
        vol = max(abs(p.get("daily_change_pct", 0.0)), abs(p.get("month_trend_pct", 0.0)))
        if vol >= 5.0:
            score += 3.0
        elif vol >= 2.0:
            score += 2.0
        elif vol >= 0.5:
            score += 1.0
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