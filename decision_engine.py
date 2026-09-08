"""Shared final-decision logic used by single-project and comparison flows."""

from typing import Any, Dict


def get_final_decision(metrics: Dict[str, Any], risk_data: Dict[str, Any], scenario_data: Dict[str, Any]) -> Dict[str, Any]:
    accept_score = 0
    reject_score = 0
    reasons_for = []
    reasons_against = []

    if metrics["npv_status"]["decision"] == "ACCEPT":
        accept_score += 3
        reasons_for.append("NPV is positive, indicating the project creates value above the required return.")
    else:
        reject_score += 3
        reasons_against.append("NPV is negative, indicating value destruction.")

    if metrics["irr_status"]["decision"] == "ACCEPT":
        accept_score += 2
        reasons_for.append(f"IRR ({metrics['irr']:.1%}) exceeds WACC ({metrics['wacc']:.1%}).")
    else:
        reject_score += 2
        reasons_against.append(f"IRR ({metrics['irr']:.1%}) is below WACC ({metrics['wacc']:.1%}).")

    if metrics["mirr_status"]["decision"] == "ACCEPT":
        accept_score += 2
        reasons_for.append(f"MIRR ({metrics['mirr']:.1%}) exceeds the required return.")
    else:
        reject_score += 2
        reasons_against.append(f"MIRR ({metrics['mirr']:.1%}) is below the required return.")

    if metrics["pi_status"]["decision"] == "ACCEPT":
        accept_score += 1
        reasons_for.append(f"Profitability Index ({metrics['pi']:.2f}) is above 1.0.")
    else:
        reject_score += 1
        reasons_against.append(f"Profitability Index ({metrics['pi']:.2f}) is below 1.0.")

    if metrics["payback_status"]["decision"] == "ACCEPT":
        accept_score += 1
        reasons_for.append("Payback period is within the project life.")
    else:
        reject_score += 1
        reasons_against.append("Payback period exceeds the project life.")

    if metrics["roi_status"]["decision"] == "ACCEPT":
        accept_score += 1
        reasons_for.append("ROI is positive.")
    else:
        reject_score += 1
        reasons_against.append("ROI is negative.")

    risk_level = risk_data.get("overall_level", "MEDIUM")
    if risk_level in ("LOW",):
        accept_score += 1
        reasons_for.append(f"Risk level is {risk_level}.")
    elif risk_level in ("HIGH", "VERY HIGH"):
        reject_score += 1
        reasons_against.append(f"Risk level is {risk_level}.")

    worst_case = scenario_data.get("worst_case", {})
    if worst_case.get("npv_status", {}).get("decision") == "REJECT":
        reject_score += 1
        reasons_against.append("Worst-case scenario produces negative NPV.")
    else:
        accept_score += 1
        reasons_for.append("Even the worst-case scenario remains viable.")

    total = accept_score + reject_score
    accept_ratio = accept_score / total if total > 0 else 0.5

    if accept_ratio >= 0.65:
        decision = "ACCEPT"
    elif accept_ratio <= 0.35:
        decision = "REJECT"
    else:
        decision = "REVIEW"

    if decision == "ACCEPT":
        recommendation = (
            "The project demonstrates strong financial fundamentals across multiple metrics. "
            "Management should proceed with the investment, subject to ongoing monitoring of "
            "key assumptions and regular performance reviews against projections."
        )
    elif decision == "REJECT":
        recommendation = (
            "Do not proceed under the current assumptions. Management should reconsider project costs, "
            "expected revenues, financing structure, or required return before reassessment. "
            "Alternative projects with better risk-adjusted returns should be evaluated."
        )
    else:
        recommendation = (
            "The project presents mixed signals. Management should conduct additional due diligence, "
            "gather more market data, and consider a phased investment approach. "
            "Key assumptions should be stress-tested further before a final commitment."
        )

    all_reasons = []
    for r in reasons_for:
        all_reasons.append(f"[+] {r}")
    for r in reasons_against:
        all_reasons.append(f"[-] {r}")

    if decision == "ACCEPT":
        main_reason = (
            "The project clears most financial thresholds: NPV is positive, returns compare "
            "favourably with the cost of capital, and risk is assessed as LOW."
        )
    elif decision == "REJECT":
        main_reason = (
            "The project fails most financial thresholds: NPV is negative, returns are below "
            "the cost of capital, and the risk profile is unfavourable."
        )
    else:
        main_reason = (
            "The project presents mixed financial signals across the primary metrics, "
            "warranting further review before commitment."
        )

    return {
        "decision": decision,
        "accept_score": accept_score,
        "reject_score": reject_score,
        "reasons_for": reasons_for,
        "reasons_against": reasons_against,
        "supporting_points": all_reasons,
        "reason": "; ".join(reasons_for[:2] + reasons_against[:2]) if (reasons_for or reasons_against) else "Insufficient data.",
        "main_reason": main_reason,
        "recommendation": recommendation,
    }
