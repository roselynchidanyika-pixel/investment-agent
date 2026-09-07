"""FX service for the Integrated Investment Decision Agent for Capital Project Evaluation.

Provides LIVE exchange rates for ZIG (Zimbabwe Gold / ZiG), USD and ZAR using
free, no-key APIs, with graceful fallbacks. Shows how much of each currency you
need to fund a USD-based investment and which funding/return currency is most
profitable given expected local-currency depreciation.

Sources (no API keys required):
  - open.er-api.com/v6/latest/USD   (rates incl. ZWG/ZiG and ZAR)
  - cdn.jsdelivr.net fawazahmed0/currency-api (zwg, zar, daily snapshot)
  - api.frankfurter.app              (ECB — ZAR only when others fail)

ZiG is reported by these APIs under the ISO code "ZWG"; the app labels it "ZIG".

Rates are presented for information and planning. The user can always override
them manually (e.g., with the latest official Reserve Bank of Zimbabwe auction
rate). Any depreciation assumptions are model assumptions, not advice.
"""

from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone
from typing import Any

import pandas as pd

FXDISPLAY = ("USD", "ZIG", "ZAR")

# Reference fallback only used when every live source fails AND no manual rate
# has been entered. These are a starting point and MUST be overridden by the user.
DEFAULT_UNIT_PER_USD = {"USD": 1.0, "ZIG": 26.57, "ZAR": 15.97}

# Source order: primary -> fallbacks.
_SOURCES = [
    ("open.er-api.com", "https://open.er-api.com/v6/latest/USD"),
    (
        "currency-api (jsdelivr)",
        "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json",
    ),
    ("frankfurter (ECB)", "https://api.frankfurter.app/latest?from=USD"),
]

# If a source exposes ZiG under a different code, map it here.
_ZIG_CODES = ("ZWG", "ZIG", "ZWL")


def _http_json(url: str, timeout: int = 15) -> dict[str, Any]:
    req = urllib.request.Request(
        url, headers={"User-Agent": "investment-decision-agent/1.0"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def _parse_rates(payload: dict[str, Any], source: str) -> dict[str, float] | None:
    """Extract {USD, ZIG, ZAR} unit-per-USD from a source payload."""
    rates: dict[str, float] | None = None

    if source == "open.er-api.com":
        r = payload.get("rates")
        if isinstance(r, dict) and payload.get("base_code") == "USD":
            rates = {"USD": 1.0}
            for code in _ZIG_CODES:
                if code in r and isinstance(r[code], (int, float)):
                    rates["ZIG"] = float(r[code])
                    break
            if "ZAR" in r:
                rates["ZAR"] = float(r["ZAR"])
        return rates

    if source == "currency-api (jsdelivr)":
        usd = payload.get("usd") or payload.get("data", {}).get("usd")
        if isinstance(usd, dict):
            rates = {"USD": 1.0}
            for code in _ZIG_CODES:
                if code in usd and isinstance(usd[code], (int, float)):
                    rates["ZIG"] = float(usd[code])
                    break
            if "zar" in usd:
                rates["ZAR"] = float(usd["zar"])
        return rates

    if source == "frankfurter (ECB)":
        r = payload.get("rates")
        if isinstance(r, dict) and payload.get("base") == "USD":
            rates = {"USD": 1.0}
            if "ZAR" in r:
                rates["ZAR"] = float(r["ZAR"])
        return rates

    return None


def fetch_live_rates(timeout: int = 15, cached: dict | None = None) -> dict[str, Any]:
    """Try every live source in order. Returns a normalised rates dict.

    Always returns at least a usable (possibly fallback) structure:
      {
        "success": bool,
        "source": str,
        "fetched_at": iso-string,
        "rates": {"USD": 1.0, "ZIG": x, "ZAR": y},   # units per 1 USD
        "zig_live": bool,
        "message": str,
      }
    """
    if cached and cached.get("rates"):
        cached["cached"] = True
        return cached

    errors = []
    for source, url in _SOURCES:
        try:
            payload = _http_json(url, timeout=timeout)
            rates = _parse_rates(payload, source)
            if not rates:
                errors.append(f"{source}: no usable rate data")
                continue
            # Need ZIG and ZAR for the analysis.
            if "ZAR" not in rates:
                errors.append(f"{source}: ZAR missing")
                continue
            zig_live = "ZIG" in rates
            if not zig_live:
                rates["ZIG"] = DEFAULT_UNIT_PER_USD["ZIG"]
            return {
                "success": True,
                "source": source,
                "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "rates": rates,
                "zig_live": zig_live,
                "message": (
                    f"Live rates loaded from {source}. "
                    + (f"ZiG rate from market feed (code ZWG={rates['ZIG']:.4f}/USD)."
                       if zig_live else
                       f"ZiG rate: live feed unavailable — using reference "
                       f"{rates['ZIG']:.4f}/USD. Enter the current RBZ auction rate to override.")
                ),
            }
        except Exception as e:  # noqa: BLE001
            errors.append(f"{source}: {str(e)}")
            continue

    return {
        "success": False,
        "source": "none (offline)",
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rates": dict(DEFAULT_UNIT_PER_USD),
        "zig_live": False,
        "message": (
            "No live rate source could be reached. Using reference rates "
            f"{DEFAULT_UNIT_PER_USD['ZIG']:.2f} ZIG/USD and "
            f"{DEFAULT_UNIT_PER_USD['ZAR']:.2f} ZAR/USD. "
            "Please enter current rates manually. Errors: " + "; ".join(errors)
        ),
    }


def apply_overrides(fx: dict[str, Any], zig_per_usd: float | None, zar_per_usd: float | None) -> dict[str, Any]:
    """Return a copy of fx with any manual rate overrides applied."""
    out = dict(fx)
    rates = dict(fx.get("rates", {}))
    zig_live = bool(fx.get("zig_live"))
    if zig_per_usd is not None and zig_per_usd > 0:
        rates["ZIG"] = float(zig_per_usd)
        zig_live = False  # overridden by user
    if zar_per_usd is not None and zar_per_usd > 0:
        rates["ZAR"] = float(zar_per_usd)
    out["rates"] = rates
    out["zig_live"] = zig_live
    out["overrides"] = {
        "zig_per_usd": zig_per_usd,
        "zar_per_usd": zar_per_usd,
    }
    return out


def convert(amount: float, from_code: str, to_code: str, rates: dict[str, float]) -> float:
    """Convert amount from one currency to another via USD."""
    per_usd = rates.get(to_code)
    usd_value = amount / rates.get(from_code, 1.0)
    return usd_value * per_usd


def build_rate_table(fx: dict[str, Any]) -> pd.DataFrame:
    rates = fx["rates"]
    usd = rates.get("USD", 1.0)
    zig, zar = rates.get("ZIG"), rates.get("ZAR")
    rows = [
        {"Pair": "1 USD =", "ZIG": f"{zig:.4f}", "ZAR": f"{zar:.4f}"},
        {"Pair": "1 ZIG =", "ZIG": "1 ZIG", "ZAR": f"{zar / zig:.4f}" if zig else "n/a"},
        {"Pair": "1 ZAR =", "ZIG": f"{zig / zar:.4f}" if zar else "n/a", "ZAR": "1 ZAR"},
        {"Pair": "USD / ZIG", "ZIG": f"{usd / zig:.6f}" if zig else "n/a", "ZAR": f"{usd / zar:.6f}" if zar else "n/a"},
    ]
    return pd.DataFrame(rows)


def funding_analysis(
    investment_usd: float,
    fx: dict[str, Any],
    earn_mix: dict[str, float],
    expected_depreciation: dict[str, float],
) -> dict[str, Any]:
    """Compare how much ZIG/USD/ZAR is needed and which funding currency is most
    profitable, purely from live rates + user depreciation assumptions.

    - `investment_usd`: USD-equivalent capital outlay (from the analysis).
    - `earn_mix`: share of income held in each currency ({USD: 0.30, ZIG: 0.70, ZAR: 0.0}).
    - `expected_depreciation`: annual depreciation of each local currency vs USD
      ({ZIG: 0.35, ZAR: 0.08} meaning the currency loses 35%/8% of USD value/yr).

    Returns rows + a written funding recommendation.
    """
    rates = fx["rates"]
    rows = []
    for code in FXDISPLAY:
        per_usd = rates.get(code, 1.0)
        if not per_usd or per_usd <= 0:
            continue
        dep = expected_depreciation.get(code, 0.0)
        amount_needed = investment_usd * per_usd
        # USD value retained after holding the required amount 1 year (if delayed):
        usd_after_1yr = investment_usd / (1 + dep)
        rows.append(
            {
                "Currency": code,
                "Units per USD": per_usd,
                "Amount needed today": amount_needed,
                "Expected annual depreciation (vs USD)": dep * 100,
                "USD value after 1 yr of holding": usd_after_1yr,
                "Value retained": usd_after_1yr / investment_usd * 100 if investment_usd else 0,
            }
        )

    if not rows:
        return {
            "rows": pd.DataFrame(),
            "best_currency": "USD",
            "recommendation": "FX rates unavailable.",
            "blended_loss_pct": 0.0,
        }

    # Highest retained value wins (lowest depreciation).
    best = min(rows, key=lambda r: r["Expected annual depreciation (vs USD)"])
    best_cur = best["Currency"]

    # Blended carrying loss from an income mix earned in these currencies.
    total_mix = sum(earn_mix.get(c, 0.0) for c in FXDISPLAY) or 1.0
    blended_loss = sum(
        (earn_mix.get(c, 0.0) / total_mix)
        * (expected_depreciation.get(c, 0.0) / (1 + expected_depreciation.get(c, 0.0)))
        for c in FXDISPLAY
    )

    df = pd.DataFrame(rows)
    zig_dep = expected_depreciation.get("ZIG", 0.0) * 100
    zar_dep = expected_depreciation.get("ZAR", 0.0) * 100

    if best_cur == "USD":
        recommendation = (
            f"Funding in USD retains 100% of its USD value, the strongest option. "
            f"A ZIG-funded equivalent of {df.loc[df.Currency=='ZIG','Amount needed today'].iloc[0]:,.0f} ZIG "
            f"for an upfront conversion would lock today's rate; holding ZIG instead of converting exposes "
            f"your money to an assumed depreciation of about {zig_dep:.1f}%/yr. "
            f"ZAR is the cheaper local alternative if you must fund regionally, at an assumed "
            f"{zar_dep:.1f}%/yr depreciation. If you earn both ZIG and USD, the blended expected "
            f"carrying loss on unspent earnings is about {blended_loss*100:.1f}% of USD value per year — "
            "converting ZIG to USD promptly protects your purchasing power."
        )
    else:
        recommendation = (
            f"The lowest-depreciation funding currency is {best_cur} "
            f"(assumed {best['Expected annual depreciation (vs USD)']:.1f}%/yr). "
            f"Compare: ZIG is assumed to lose about {zig_dep:.1f}%/yr and ZAR about {zar_dep:.1f}%/yr of USD "
            "value. The USD investment amount converts to the local totals shown in the table "
            f"if you must fund from {best_cur}."
        )

    return {
        "rows": df,
        "best_currency": best_cur,
        "recommendation": recommendation,
        "blended_loss_pct": blended_loss * 100,
        "zig_depreciation_pct": zig_dep,
        "zar_depreciation_pct": zar_dep,
    }


def fx_summary_for_email(fx: dict[str, Any], funding: dict[str, Any]) -> list[str]:
    """Compact FX lines for the e-mail body."""
    rates = fx["rates"]
    lines = [
        "",
        "FX snapshot (per USD):",
        f"- ZiG: {rates.get('ZIG', float('nan')):.4f}  |  USD: 1.0000  |  ZAR: {rates.get('ZAR', float('nan')):.4f}",
    ]
    if funding and funding.get("rows") is not None and not funding["rows"].empty:
        best = funding.get("best_currency", "USD")
        lines.append(
            f"- Most favourable funding/return currency (lowest assumed depreciation): {best}."
        )
    return lines