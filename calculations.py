import numpy as np
import pandas as pd
from scipy.optimize import brentq
from typing import Dict, List, Any, Optional, Tuple


def calculate_cash_flows(inputs: Dict[str, Any]) -> Dict[str, Any]:
    initial_investment = float(inputs["initial_investment"])
    project_life = int(float(inputs["project_life"]))
    annual_revenue = float(inputs["annual_revenue"])
    operating_costs = float(inputs["operating_costs"])
    tax_rate = float(inputs["tax_rate"])
    working_capital = float(inputs.get("working_capital", 0))
    terminal_value = float(inputs.get("terminal_value", 0))
    wacc = float(inputs["wacc"])
    financing_rate = float(inputs.get("financing_rate", wacc))
    reinvestment_rate = float(inputs.get("reinvestment_rate", wacc))
    revenue_growth = float(inputs.get("revenue_growth", inputs.get("growth_rate", 0)))
    cost_growth = float(inputs.get("cost_growth", inputs.get("growth_rate", 0)))
    terminal_growth = float(inputs.get("terminal_growth", 0))
    depreciation_rate = float(inputs.get("depreciation_rate", 0))
    currency = inputs.get("currency", "USD")

    depreciation = initial_investment * depreciation_rate if depreciation_rate > 0 else initial_investment / project_life

    if terminal_value == 0 and terminal_growth > 0 and wacc > terminal_growth:
        depreciation = initial_investment * depreciation_rate if depreciation_rate > 0 else initial_investment / project_life
        last_revenue = annual_revenue * (1 + revenue_growth) ** (project_life - 1)
        last_costs = operating_costs * (1 + cost_growth) ** (project_life - 1)
        last_ebit = last_revenue - last_costs - depreciation
        last_tax = last_ebit * tax_rate if last_ebit > 0 else 0
        last_ocf = (last_ebit - last_tax) + depreciation
        terminal_value = (last_ocf * (1 + terminal_growth)) / (wacc - terminal_growth)

    years = list(range(0, project_life + 1))
    cash_flows = []
    discount_factors = []
    present_values = []
    cumulative_cash_flows = []

    detailed_rows = []
    cumulative = 0.0

    for year in years:
        if year == 0:
            cf = -(initial_investment + working_capital)
            cash_flows.append(cf)
            discount_factors.append(1.0)
            present_values.append(cf)
            cumulative += cf
            cumulative_cash_flows.append(cumulative)

            detailed_rows.append({
                "Year": 0,
                "Revenue": 0, "Operating Costs": 0, "EBITDA": 0,
                "Depreciation": 0, "EBIT": 0, "Tax": 0, "NOPAT": 0,
                "OCF": 0, "Initial Investment": -initial_investment,
                "Working Capital": -working_capital, "Terminal Value": 0,
                "Net Cash Flow": cf,
            })
        else:
            rev = annual_revenue * (1 + revenue_growth) ** (year - 1)
            costs = operating_costs * (1 + cost_growth) ** (year - 1)
            ebitda = rev - costs
            ebit = ebitda - depreciation
            tax = ebit * tax_rate if ebit > 0 else 0
            nopat = ebit - tax
            ocf = nopat + depreciation

            inv_outflow = 0
            wc_outflow = 0
            wc_recovery = 0
            tv_inflow = 0

            if year == 1 and working_capital > 0:
                wc_outflow = -working_capital

            if year == project_life:
                wc_recovery = working_capital
                tv_inflow = terminal_value

            net_cf = ocf + inv_outflow + wc_outflow + wc_recovery + tv_inflow

            cash_flows.append(net_cf)
            df = 1 / (1 + wacc) ** year
            discount_factors.append(df)
            pv = net_cf * df
            present_values.append(pv)
            cumulative += net_cf
            cumulative_cash_flows.append(cumulative)

            detailed_rows.append({
                "Year": year,
                "Revenue": rev, "Operating Costs": costs, "EBITDA": ebitda,
                "Depreciation": depreciation, "EBIT": ebit, "Tax": tax, "NOPAT": nopat,
                "OCF": ocf, "Initial Investment": 0,
                "Working Capital": wc_outflow + wc_recovery, "Terminal Value": tv_inflow,
                "Net Cash Flow": net_cf,
            })

    total_pv_inflows = sum(present_values[1:])
    npv = sum(present_values)
    pi = total_pv_inflows / initial_investment if initial_investment != 0 else 0
    roi = (sum(cash_flows[1:]) - initial_investment) / initial_investment if initial_investment != 0 else 0

    irr = calculate_irr(cash_flows)
    mirr = calculate_mIRR(cash_flows, financing_rate, reinvestment_rate)
    payback = calculate_payback(cash_flows)

    holding_period_return = sum(cash_flows[1:]) / initial_investment if initial_investment != 0 else 0
    annualized_return = (1 + holding_period_return) ** (1 / project_life) - 1 if project_life > 0 else 0

    dcf_value = total_pv_inflows + (terminal_value / (1 + wacc) ** project_life) if terminal_value > 0 else total_pv_inflows

    cash_flow_table = pd.DataFrame(detailed_rows)

    dcf_table = pd.DataFrame({
        "Year": years,
        "Free Cash Flow": cash_flows,
        "Discount Factor": discount_factors,
        "Present Value": present_values,
        "Cumulative Present Value": np.cumsum(present_values),
    })

    return {
        "cash_flows": cash_flows,
        "years": years,
        "discount_factors": discount_factors,
        "present_values": present_values,
        "cumulative_cash_flows": cumulative_cash_flows,
        "cash_flow_table": cash_flow_table,
        "dcf_table": dcf_table,
        "npv": npv,
        "irr": irr,
        "mirr": mirr,
        "payback": payback,
        "pi": pi,
        "roi": roi,
        "total_pv_inflows": total_pv_inflows,
        "dcf_value": dcf_value,
        "holding_period_return": holding_period_return,
        "annualized_return": annualized_return,
        "initial_investment": initial_investment,
        "project_life": project_life,
        "wacc": wacc,
        "financing_rate": financing_rate,
        "reinvestment_rate": reinvestment_rate,
        "terminal_value": terminal_value,
        "working_capital": working_capital,
        "tax_rate": tax_rate,
        "depreciation": depreciation,
        "currency": currency,
    }


def calculate_irr(cash_flows: List[float]) -> float:
    if len(cash_flows) < 2:
        return 0.0

    positive = any(cf > 0 for cf in cash_flows[1:])
    negative = any(cf < 0 for cf in cash_flows)

    if not positive or not negative:
        if positive and cash_flows[0] >= 0:
            return 1.0
        return 0.0

    try:
        def npv_func(r):
            return sum(cf / (1 + r) ** t for t, cf in enumerate(cash_flows))

        irr = brentq(npv_func, -0.5, 10.0, maxiter=1000, xtol=1e-12)
        return irr
    except (ValueError, RuntimeError):
        try:
            rates = np.linspace(-0.49, 5.0, 10000)
            npvs = [sum(cf / (1 + r) ** t for t, cf in enumerate(cash_flows)) for r in rates]
            idx = np.argmin(np.abs(npvs))
            return float(rates[idx])
        except Exception:
            return 0.0


def calculate_mIRR(cash_flows: List[float], finance_rate: float, reinvestment_rate: float) -> float:
    n = len(cash_flows) - 1
    if n <= 0:
        return 0.0

    pv_negatives = 0.0
    fv_positives = 0.0

    for t, cf in enumerate(cash_flows):
        if cf < 0:
            pv_negatives += cf / (1 + finance_rate) ** t
        elif cf > 0:
            fv_positives += cf * (1 + reinvestment_rate) ** (n - t)

    if pv_negatives == 0 or fv_positives <= 0:
        return 0.0

    pv_negatives = abs(pv_negatives)

    try:
        mirr = (fv_positives / pv_negatives) ** (1.0 / n) - 1
        if np.isnan(mirr) or np.isinf(mirr):
            return 0.0
        return mirr
    except (ZeroDivisionError, ValueError):
        return 0.0


def calculate_payback(cash_flows: List[float]) -> float:
    cumulative = 0.0
    for i, cf in enumerate(cash_flows):
        cumulative += cf
        if cumulative >= 0 and i > 0:
            prev_cumulative = cumulative - cf
            if cf != 0:
                fraction = -prev_cumulative / cf
            else:
                fraction = 0
            return (i - 1) + fraction

    if cumulative < 0:
        return float("inf")
    return len(cash_flows)


def get_metric_status(metric_name: str, value: float, threshold: float,
                      higher_is_better: bool = True) -> Dict[str, str]:
    from data_validation import explain_metric, format_currency, format_pct

    if higher_is_better:
        favorable = value >= threshold
    else:
        favorable = value <= threshold

    decision = "ACCEPT" if favorable else "REJECT"
    result = explain_metric(metric_name, value, threshold, higher_is_better)

    return {
        "value": value,
        "threshold": threshold,
        "decision": decision,
        "reason": result["reason"],
        "favorable": favorable,
    }


def calculate_all_metrics(inputs: Dict[str, Any]) -> Dict[str, Any]:
    cf_result = calculate_cash_flows(inputs)

    wacc = cf_result["wacc"]
    project_life = cf_result["project_life"]

    npv_status = get_metric_status("NPV", cf_result["npv"], 0, higher_is_better=True)
    irr_status = get_metric_status("IRR", cf_result["irr"], wacc, higher_is_better=True)
    mirr_status = get_metric_status("MIRR", cf_result["mirr"], wacc, higher_is_better=True)
    pi_status = get_metric_status("PI", cf_result["pi"], 1.0, higher_is_better=True)
    payback_status = get_metric_status("Payback", cf_result["payback"], project_life, higher_is_better=False)
    roi_status = get_metric_status("ROI", cf_result["roi"], 0, higher_is_better=True)

    cf_result["npv_status"] = npv_status
    cf_result["irr_status"] = irr_status
    cf_result["mirr_status"] = mirr_status
    cf_result["pi_status"] = pi_status
    cf_result["payback_status"] = payback_status
    cf_result["roi_status"] = roi_status

    cf_result["irr_status"]["wacc"] = wacc
    cf_result["mirr_status"]["wacc"] = wacc

    return cf_result


def calculate_sensitivity(inputs: Dict[str, Any], variable: str,
                          changes: Optional[List[float]] = None) -> Dict[str, Any]:
    if changes is None:
        changes = [-0.30, 0.0, 0.30]

    base_value = float(inputs.get(variable, 0))
    if base_value == 0 and variable not in ("revenue_growth", "cost_growth"):
        base_value = 1.0

    results = []

    for change in changes:
        modified = dict(inputs)
        if variable in ("wacc", "tax_rate", "financing_rate", "reinvestment_rate"):
            modified[variable] = max(0, min(1.0, base_value + change))
        else:
            modified[variable] = base_value * (1 + change) if base_value != 0 else change

        try:
            metrics = calculate_all_metrics(modified)
            results.append({
                "variation": change,
                "variation_pct": f"{change:+.0%}",
                "npv": metrics["npv"],
                "irr": metrics["irr"],
                "mirr": metrics["mirr"],
                "pi": metrics["pi"],
                "payback": metrics["payback"],
                "roi": metrics["roi"],
            })
        except Exception:
            continue

    df = pd.DataFrame(results)

    npv_range = 0
    npv_at_base = base_npv = 0
    if len(df) > 0:
        npv_range = df["npv"].max() - df["npv"].min()
        base_row = df[df["variation"] == 0]
        if not base_row.empty:
            base_npv = base_row["npv"].iloc[0]
        else:
            base_npv = np.nan

    npv_minus = np.interp(-0.30, df["variation"], df["npv"]) if len(df) >= 2 else base_npv
    npv_plus = np.interp(0.30, df["variation"], df["npv"]) if len(df) >= 2 else base_npv

    return {
        "variable": variable,
        "base_value": base_value,
        "results": df,
        "npv_range": npv_range,
        "npv_at_base": base_npv,
        "npv_at_minus30": npv_minus,
        "npv_at_plus30": npv_plus,
    }


def calculate_full_sensitivity(inputs: Dict[str, Any]) -> Dict[str, Any]:
    variables = ["wacc", "annual_revenue", "operating_costs", "initial_investment"]
    revenue_growth = inputs.get("revenue_growth", inputs.get("growth_rate", 0))
    cost_growth = inputs.get("cost_growth", inputs.get("growth_rate", 0))

    variable_labels = {
        "wacc": "Discount Rate (WACC)",
        "annual_revenue": "Annual Revenues",
        "operating_costs": "Operating Costs",
        "initial_investment": "Initial Investment",
        "revenue_growth": "Revenue Growth",
        "cost_growth": "Cost Growth",
    }

    sensitivities = {}
    for var in variables:
        if var in inputs:
            sens = calculate_sensitivity(inputs, var)
            sens["label"] = variable_labels.get(var, var)
            sensitivities[var] = sens

    if revenue_growth:
        sens = calculate_sensitivity(inputs, "revenue_growth")
        sens["label"] = "Revenue Growth"
        sensitivities["revenue_growth"] = sens

    if cost_growth:
        sens = calculate_sensitivity(inputs, "cost_growth")
        sens["label"] = "Cost Growth"
        sensitivities["cost_growth"] = sens

    ranking = []
    for var, sens in sensitivities.items():
        ranking.append({
            "variable": var,
            "label": sens.get("label", var),
            "npv_range": sens["npv_range"],
            "npv_at_base": sens.get("npv_at_base", 0),
            "npv_at_minus30": sens.get("npv_at_minus30", 0),
            "npv_at_plus30": sens.get("npv_at_plus30", 0),
        })

    ranked = sorted(ranking, key=lambda x: x["npv_range"], reverse=True)

    return {
        "sensitivities": sensitivities,
        "ranking": ranked,
        "most_sensitive": ranked[0]["label"] if ranked else None,
        "least_sensitive": ranked[-1]["label"] if ranked else None,
    }
