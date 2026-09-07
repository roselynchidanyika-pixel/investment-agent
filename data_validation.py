import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any

REQUIRED_FIELDS = {
    "project_name": str,
    "project_description": str,
    "initial_investment": (int, float),
    "project_life": (int, float),
    "annual_revenue": (int, float),
    "operating_costs": (int, float),
    "tax_rate": (int, float),
    "working_capital": (int, float),
    "terminal_value": (int, float),
    "wacc": (int, float),
    "financing_rate": (int, float),
    "reinvestment_rate": (int, float),
}

OPTIONAL_FIELDS = {
    "growth_rate": (int, float),
    "revenue_growth": (int, float),
    "cost_growth": (int, float),
    "terminal_growth": (int, float),
    "depreciation_rate": (int, float),
    "currency": str,
    "description": str,
    "zig_revenue_share": (int, float),
    "zig_cost_share": (int, float),
    "zar_revenue_share": (int, float),
    "zar_cost_share": (int, float),
    "investment_fx_share": (int, float),
    "liquidity_buffer_months": (int, float),
}

EXTREME_THRESHOLDS = {
    "tax_rate": (0.0, 0.80),
    "wacc": (0.0, 0.50),
    "financing_rate": (0.0, 0.50),
    "reinvestment_rate": (-0.10, 0.30),
    "project_life": (1, 100),
    "operating_costs": (0, None),
    "revenue_growth": (-0.50, 0.50),
    "cost_growth": (-0.50, 0.50),
    "terminal_growth": (-0.20, 0.30),
    "zig_revenue_share": (0.0, 1.0),
    "zig_cost_share": (0.0, 1.0),
    "zar_revenue_share": (0.0, 1.0),
    "zar_cost_share": (0.0, 1.0),
    "investment_fx_share": (0.0, 1.0),
    "liquidity_buffer_months": (0, 60),
}

RATE_FIELDS = [
    "growth_rate", "revenue_growth", "cost_growth", "terminal_growth",
    "depreciation_rate", "tax_rate", "wacc", "financing_rate", "reinvestment_rate",
    "zig_revenue_share", "zig_cost_share", "zar_revenue_share", "zar_cost_share",
    "investment_fx_share",
]

SHARE_FIELDS = [
    "zig_revenue_share", "zig_cost_share", "zar_revenue_share", "zar_cost_share",
    "investment_fx_share",
]


def validate_project_inputs(data: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
    errors = []
    warnings = []

    for field, expected_type in REQUIRED_FIELDS.items():
        if field not in data or data[field] is None or str(data[field]).strip() == "":
            errors.append(f"Missing required field: '{field}'. This field is required for analysis.")
            continue
        if not isinstance(expected_type, tuple):
            expected_type = (expected_type,)
        if not isinstance(data[field], expected_type):
            try:
                if data[field] in (int, float):
                    pass
                elif isinstance(data[field], str):
                    if expected_type != (str,):
                        try:
                            data[field] = float(data[field])
                        except (ValueError, TypeError):
                            errors.append(f"Field '{field}' must be numeric. Got: '{data[field]}'")
            except Exception:
                errors.append(f"Field '{field}' has invalid type. Expected: {expected_type}")

    for field, expected_type in OPTIONAL_FIELDS.items():
        if field in data and data[field] is not None and str(data[field]).strip() != "":
            if not isinstance(expected_type, tuple):
                expected_type = (expected_type,)
            if not isinstance(data[field], expected_type):
                try:
                    if isinstance(data[field], str) and expected_type != (str,):
                        data[field] = float(data[field])
                except (ValueError, TypeError):
                    warnings.append(f"Optional field '{field}' has invalid type and was ignored.")

    for group, base in (("zig_revenue_share", "zar_revenue_share"), ("zig_cost_share", "zar_cost_share")):
        try:
            a = float(data.get(group, 0) or 0)
            b = float(data.get(base, 0) or 0)
            if a + b > 1.0 + 1e-9:
                errors.append(
                    f"The shares for '{group}' and '{base}' sum to {a + b:.0%}, which exceeds 100%. "
                    "Please adjust the currency exposure shares."
                )
        except (ValueError, TypeError):
            pass

    numeric_fields = ["initial_investment", "annual_revenue", "operating_costs",
                      "working_capital", "terminal_value"]
    for field in numeric_fields:
        if field in data:
            try:
                val = float(data[field])
                if val < 0:
                    errors.append(f"Field '{field}' cannot be negative (value: {val}).")
            except (ValueError, TypeError):
                pass

    if "initial_investment" in data:
        try:
            inv = float(data["initial_investment"])
            if inv == 0:
                warnings.append("Initial investment is zero. This is unusual — please confirm.")
            elif inv < 0:
                errors.append("Initial investment cannot be negative.")
            elif inv > 1_000_000_000_000:
                warnings.append(f"Initial investment (${inv:,.0f}) is extremely large. Please verify.")
        except (ValueError, TypeError):
            pass

    for field, (low, high) in EXTREME_THRESHOLDS.items():
        if field in data:
            try:
                val = float(data[field])
                if low is not None and val < low:
                    errors.append(f"Field '{field}' = {val} is below acceptable minimum ({low}).")
                if high is not None and val > high:
                    warnings.append(f"Field '{field}' = {val} is unusually high (max recommended: {high}).")
            except (ValueError, TypeError):
                pass

    if "annual_revenue" in data and "operating_costs" in data:
        try:
            rev = float(data["annual_revenue"])
            cost = float(data["operating_costs"])
            if cost > rev:
                warnings.append(
                    f"Operating costs (${cost:,.0f}) exceed annual revenue (${rev:,.0f}). "
                    "This results in operating losses each year."
                )
        except (ValueError, TypeError):
            pass

    for rf in RATE_FIELDS:
        if rf in data:
            try:
                val = float(data[rf])
                if val is None or val != val:
                    continue
            except (ValueError, TypeError):
                pass

    if "terminal_growth" in data and "wacc" in data:
        try:
            tg = float(data["terminal_growth"])
            wacc = float(data["wacc"])
            if tg >= wacc:
                errors.append(
                    f"Terminal growth ({tg:.1%}) must be below the WACC ({wacc:.1%}) "
                    "for the Gordon growth model to produce a valid terminal value."
                )
        except (ValueError, TypeError):
            pass

    if "wacc" in data and "financing_rate" in data:
        try:
            wacc = float(data["wacc"])
            fin = float(data["financing_rate"])
            if fin > wacc * 2:
                warnings.append(
                    f"Financing rate ({fin:.1%}) is significantly higher than WACC ({wacc:.1%}). "
                    "This may indicate unusual capital structure assumptions."
                )
        except (ValueError, TypeError):
            pass

    if "project_life" in data:
        try:
            life = float(data["project_life"])
            if life != int(life):
                warnings.append("Project life has been rounded to the nearest whole year.")
                data["project_life"] = int(round(life))
        except (ValueError, TypeError):
            pass

    is_valid = len(errors) == 0
    return is_valid, errors, warnings


def validate_uploaded_data(df: pd.DataFrame) -> Tuple[bool, List[str], List[str], Dict[str, Any]]:
    errors = []
    warnings = []
    parsed_data = {}

    if df.empty:
        errors.append("The uploaded file is empty. Please check your data.")
        return False, errors, warnings, parsed_data

    if "parameter" in df.columns and "value" in df.columns:
        for _, row in df.iterrows():
            param = str(row["parameter"]).strip().lower().replace(" ", "_")
            val = row["value"]
            parsed_data[param] = val
    else:
        if len(df) == 1:
            for col in df.columns:
                parsed_data[col.strip().lower().replace(" ", "_")] = df[col].iloc[0]
        else:
            first_col = df.columns[0].strip().lower().replace(" ", "_")
            second_col = df.columns[1].strip().lower().replace(" ", "_") if len(df.columns) > 1 else "value"
            for _, row in df.iterrows():
                parsed_data[str(row.iloc[0]).strip().lower().replace(" ", "_")] = row.iloc[1]

    if not parsed_data:
        errors.append("Could not parse any data from the uploaded file.")
        return False, errors, warnings, parsed_data

    is_valid, val_errors, val_warnings = validate_project_inputs(parsed_data)
    errors.extend(val_errors)
    warnings.extend(val_warnings)

    return is_valid, errors, warnings, parsed_data


def get_default_inputs() -> Dict[str, Any]:
    return {
        "project_name": "",
        "project_description": "",
        "initial_investment": 0.0,
        "project_life": 5,
        "annual_revenue": 0.0,
        "operating_costs": 0.0,
        "tax_rate": 0.25,
        "working_capital": 0.0,
        "terminal_value": 0.0,
        "wacc": 0.10,
        "financing_rate": 0.08,
        "reinvestment_rate": 0.06,
        "growth_rate": 0.03,
        "revenue_growth": 0.03,
        "cost_growth": 0.03,
        "terminal_growth": 0.0,
        "depreciation_rate": 0.10,
        "currency": "USD",
        "zig_revenue_share": 0.0,
        "zig_cost_share": 0.0,
        "zar_revenue_share": 0.0,
        "zar_cost_share": 0.0,
        "investment_fx_share": 0.0,
        "liquidity_buffer_months": 6.0,
    }


def format_currency(value: float, currency: str = "USD") -> str:
    symbols = {"USD": "$", "ZIG": "ZIG ", "ZAR": "R ", "GBP": "\u00a3", "EUR": "\u20ac"}
    sym = symbols.get(currency.upper(), currency + " ")
    if value < 0:
        return f"({sym}{abs(value):,.0f})"
    return f"{sym}{value:,.0f}"


def format_pct(value: float) -> str:
    return f"{value:.1%}"


def determine_risk_level(score: float) -> str:
    if score <= 3:
        return "LOW"
    elif score <= 6:
        return "MEDIUM"
    elif score <= 8:
        return "HIGH"
    else:
        return "VERY HIGH"


def explain_metric(metric_name: str, value: float, threshold: float,
                   higher_is_better: bool = True) -> Dict[str, str]:
    if higher_is_better:
        favorable = value >= threshold
    else:
        favorable = value <= threshold

    decision = "ACCEPT" if favorable else "REJECT"

    explanations = {
        "NPV": {
            "accept": (
                f"The NPV of {format_currency(value)} is positive, indicating the project "
                f"creates value above the required return. The present value of expected cash flows "
                f"exceeds the initial investment by this amount."
            ),
            "reject": (
                f"The NPV of {format_currency(value)} is negative, meaning the present value of "
                f"expected future cash flows is lower than the initial investment. The project "
                f"destroys value at the specified discount rate and is not financially favourable."
            ),
        },
        "IRR": {
            "accept": (
                f"The IRR of {format_pct(value)} exceeds the required return (WACC) of {format_pct(threshold)}. "
                f"The project is expected to generate returns above its cost of capital."
            ),
            "reject": (
                f"The IRR of {format_pct(value)} is below the required return (WACC) of {format_pct(threshold)}. "
                f"The project does not generate sufficient returns to compensate for its cost of capital."
            ),
        },
        "MIRR": {
            "accept": (
                f"The MIRR of {format_pct(value)} exceeds the required return of {format_pct(threshold)}. "
                f"Under the specified financing and reinvestment assumptions, the project creates value."
            ),
            "reject": (
                f"The MIRR of {format_pct(value)} is below the required return of {format_pct(threshold)}. "
                f"The project's reinvestment-adjusted return is insufficient under current assumptions."
            ),
        },
        "PI": {
            "accept": (
                f"The Profitability Index of {value:.2f} is above 1.0, meaning the present value of "
                f"future cash inflows exceeds the initial investment by {(value-1)*100:.1f}%."
            ),
            "reject": (
                f"The Profitability Index of {value:.2f} is below 1.0, meaning the present value of "
                f"future cash inflows is less than the initial investment. The project does not "
                f"generate sufficient value per dollar invested."
            ),
        },
        "Payback": {
            "accept": (
                f"The payback period of {value:.1f} years is within the project life of {int(threshold)} years. "
                f"The initial investment is recovered within the expected operating period."
            ),
            "reject": (
                f"The payback period of {value:.1f} years exceeds the project life of {int(threshold)} years. "
                f"The initial investment is not recovered within the expected operating period."
            ),
        },
        "ROI": {
            "accept": (
                f"The ROI of {format_pct(value)} is positive, indicating the project generates "
                f"a net return relative to the initial investment."
            ),
            "reject": (
                f"The ROI of {format_pct(value)} is negative, indicating the project generates "
                f"an overall loss relative to the initial investment."
            ),
        },
    }

    key = metric_name.upper().replace(" ", "")
    if key in explanations:
        reason = explanations[key]["accept"] if favorable else explanations[key]["reject"]
    else:
        if favorable:
            reason = f"The {metric_name} of {value} meets or exceeds the benchmark of {threshold}."
        else:
            reason = f"The {metric_name} of {value} is below the benchmark of {threshold}."

    return {"decision": decision, "reason": reason}
