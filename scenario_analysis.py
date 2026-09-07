from typing import Dict, List, Any
from calculations import calculate_all_metrics


def run_scenario_analysis(inputs: Dict[str, Any]) -> Dict[str, Any]:
    base_case = calculate_all_metrics(inputs)

    best_case_inputs = create_best_case(inputs)
    best_case = calculate_all_metrics(best_case_inputs)

    worst_case_inputs = create_worst_case(inputs)
    worst_case = calculate_all_metrics(worst_case_inputs)

    base_decision = base_case["npv_status"]["decision"]
    best_decision = best_case["npv_status"]["decision"]
    worst_decision = worst_case["npv_status"]["decision"]

    base_case["scenario_label"] = "Base Case"
    best_case["scenario_label"] = "Best Case"
    worst_case["scenario_label"] = "Worst Case"

    base_case["scenario_description"] = (
        f"Base case assumes revenues of ${float(inputs.get('annual_revenue', 0)):,.0f}, "
        f"operating costs of ${float(inputs.get('operating_costs', 0)):,.0f}, "
        f"and WACC of {float(inputs.get('wacc', 0.1)):.1%}."
    )
    best_case["scenario_description"] = (
        "Best case assumes optimistic conditions: revenues increased by 20%, "
        "operating costs reduced by 10%, and WACC reduced by 2%."
    )
    worst_case["scenario_description"] = (
        "Worst case assumes pessimistic conditions: revenues reduced by 20%, "
        "operating costs increased by 10%, and WACC increased by 2%."
    )

    return {
        "base_case": base_case,
        "best_case": best_case,
        "worst_case": worst_case,
        "scenario_comparison": build_comparison_table(base_case, best_case, worst_case),
    }


def create_best_case(inputs: Dict[str, Any]) -> Dict[str, Any]:
    modified = dict(inputs)
    modified["annual_revenue"] = float(inputs.get("annual_revenue", 0)) * 1.20
    modified["operating_costs"] = float(inputs.get("operating_costs", 0)) * 0.90
    modified["wacc"] = max(0.01, float(inputs.get("wacc", 0.1)) - 0.02)
    modified["terminal_value"] = float(inputs.get("terminal_value", 0)) * 1.25
    return modified


def create_worst_case(inputs: Dict[str, Any]) -> Dict[str, Any]:
    modified = dict(inputs)
    modified["annual_revenue"] = float(inputs.get("annual_revenue", 0)) * 0.80
    modified["operating_costs"] = float(inputs.get("operating_costs", 0)) * 1.10
    modified["wacc"] = min(0.50, float(inputs.get("wacc", 0.1)) + 0.02)
    modified["terminal_value"] = float(inputs.get("terminal_value", 0)) * 0.75
    return modified


def build_scenario_reason(scenario_data: Dict[str, Any]) -> str:
    npv = scenario_data["npv"]
    decision = scenario_data["npv_status"]["decision"]
    statuses = [
        ("NPV", scenario_data["npv_status"]["decision"]),
        ("IRR", scenario_data["irr_status"]["decision"]),
        ("MIRR", scenario_data["mirr_status"]["decision"]),
        ("Payback", scenario_data["payback_status"]["decision"]),
        ("PI", scenario_data["pi_status"]["decision"]),
        ("ROI", scenario_data["roi_status"]["decision"]),
    ]

    favorable = [s for _, s in statuses if s == "ACCEPT"]
    unfavorable = [s for _, s in statuses if s == "REJECT"]

    total = len(statuses)
    if decision == "ACCEPT":
        return (
            f"All primary financial metrics ({len(favorable)} of {total}) meet or exceed their required "
            f"thresholds. The project is expected to create value after accounting for the cost of capital, "
            f"timing, recovery and return on investment."
        )
    elif decision == "REJECT":
        return (
            f"Most financial metrics ({len(unfavorable)} of {total}) are unfavourable. The preponderance "
            f"of evidence argues against proceeding under the current assumptions."
        )
    else:
        return (
            f"Financial metrics are mixed ({len(favorable)} favourable, {len(unfavorable)} unfavourable). "
            f"Additional evidence is required before a final commitment."
        )


def run_scenario_analysis(inputs: Dict[str, Any]) -> Dict[str, Any]:
    base_case = calculate_all_metrics(inputs)

    best_case_inputs = create_best_case(inputs)
    best_case = calculate_all_metrics(best_case_inputs)

    worst_case_inputs = create_worst_case(inputs)
    worst_case = calculate_all_metrics(worst_case_inputs)

    base_case["scenario_label"] = "Base Case"
    best_case["scenario_label"] = "Best Case"
    worst_case["scenario_label"] = "Worst Case"

    base_case["scenario_description"] = (
        f"Base case assumes revenues of ${float(inputs.get('annual_revenue', 0)):,.0f}, "
        f"operating costs of ${float(inputs.get('operating_costs', 0)):,.0f}, "
        f"and WACC of {float(inputs.get('wacc', 0.1)):.1%}."
    )
    best_case["scenario_description"] = (
        "Best case assumes optimistic conditions: revenues increased by 20%, "
        "operating costs reduced by 10%, and WACC reduced by 2%."
    )
    worst_case["scenario_description"] = (
        "Worst case assumes pessimistic conditions: revenues reduced by 20%, "
        "operating costs increased by 10%, and WACC increased by 2%."
    )

    base_case["scenario_reason"] = build_scenario_reason(base_case)
    best_case["scenario_reason"] = build_scenario_reason(best_case)
    worst_case["scenario_reason"] = build_scenario_reason(worst_case)

    return {
        "base_case": base_case,
        "best_case": best_case,
        "worst_case": worst_case,
        "scenario_comparison": build_comparison_table(base_case, best_case, worst_case),
    }


def build_comparison_table(base: Dict, best: Dict, worst: Dict) -> Dict[str, Any]:
    import pandas as pd

    rows = []
    for label, data in [("Best Case", best), ("Base Case", base), ("Worst Case", worst)]:
        rows.append({
            "Scenario": label,
            "NPV": data["npv"],
            "IRR": data["irr"],
            "MIRR": data["mirr"],
            "PI": data["pi"],
            "ROI": data["roi"],
            "Payback (years)": data["payback"] if data["payback"] != float("inf") else "N/A",
            "Decision": data["npv_status"]["decision"],
        })

    df = pd.DataFrame(rows)

    return {"table": df, "scenarios": {"best": best, "base": base, "worst": worst}}


def explain_scenario(scenario_data: Dict[str, Any]) -> str:
    label = scenario_data.get("scenario_label", "Scenario")
    npv = scenario_data["npv"]
    decision = scenario_data["npv_status"]["decision"]
    reason = scenario_data.get("scenario_reason", scenario_data["npv_status"]["reason"])

    from data_validation import format_currency, format_pct

    lines = [
        f"### {label}",
        f"**NPV:** {format_currency(npv)}",
        f"**IRR:** {format_pct(scenario_data['irr'])}",
        f"**MIRR:** {format_pct(scenario_data['mirr'])}",
        f"**Decision:** {decision}",
        "",
        f"**Reason:** {reason}",
    ]

    return "\n".join(lines)
