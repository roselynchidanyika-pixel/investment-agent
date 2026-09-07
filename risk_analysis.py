from typing import Dict, List, Any
import numpy as np


IMPACT_TEXT = {
    "LOW": "Limited",
    "MODERATE": "Moderate",
    "HIGH": "Significant",
    "VERY HIGH": "Severe",
}


def assess_risks(inputs: Dict[str, Any], metrics: Dict[str, Any],
                fx_risk: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    risks = []

    risks.append(assess_revenue_risk(inputs, metrics))
    risks.append(assess_cost_risk(inputs, metrics))
    risks.append(assess_wacc_risk(inputs, metrics))
    risks.append(assess_value_creation_risk(inputs, metrics))
    risks.append(assess_recovery_risk(inputs, metrics))
    risks.append(assess_cashflow_timing_risk(inputs, metrics))
    risks.append(assess_inflation_risk(inputs, metrics))
    risks.append(assess_liquidity_risk(inputs, metrics))
    risks.append(assess_profitability_risk(inputs, metrics))

    weights = [1, 1, 1, 1, 1, 1, 1, 1, 1]
    if fx_risk is not None:
        risks.append(assess_fx_risk(inputs, metrics, fx_risk))
        weights.append(1)
    else:
        fx_risk = {}

    overall_score = np.average(
        [r["severity_score"] for r in risks],
        weights=weights,
    )

    if overall_score <= 3:
        overall_level = "LOW"
    elif overall_score <= 5:
        overall_level = "MODERATE"
    elif overall_score <= 7:
        overall_level = "HIGH"
    else:
        overall_level = "VERY HIGH"

    return {
        "risks": risks,
        "overall_score": overall_score,
        "overall_level": overall_level,
        "fx_risk": fx_risk,
    }


def _make_risk(name: str, impact: str, severity: str, score: int,
               explanation: str, mitigation: str) -> Dict[str, Any]:
    if impact not in IMPACT_TEXT:
        impact = "MODERATE"
    return {
        "name": name,
        "impact": impact,
        "impact_text": IMPACT_TEXT[impact],
        "severity": severity,
        "severity_score": score,
        "explanation": explanation,
        "mitigation": mitigation,
    }


def assess_revenue_risk(inputs: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
    revenue = float(inputs.get("annual_revenue", 0))
    costs = float(inputs.get("operating_costs", 0))

    if revenue > 0:
        margin = (revenue - costs) / revenue
    else:
        margin = -1

    if margin < 0.10:
        severity, score, impact = "HIGH", 8, "HIGH"
        explanation = (
            f"Operating costs consume {costs/revenue:.0%} of revenues. The gross margin is only {margin:.1%}, "
            f"leaving minimal buffer against revenue shortfalls. A modest decline in volume or price could "
            f"push the project into operating losses."
        )
        mitigation = (
            "Diversify revenue streams, secure long-term contracts, build revenue reserves, "
            "and implement flexible pricing strategies."
        )
    elif margin < 0.25:
        severity, score, impact = "MODERATE", 5, "MODERATE"
        explanation = (
            f"Operating costs consume {costs/revenue:.0%} of revenues. Moderate margins provide some buffer, "
            f"but meaningful revenue deviations could still erode profitability."
        )
        mitigation = (
            "Monitor market conditions regularly, maintain cost flexibility, "
            "and develop contingency plans for revenue shortfalls."
        )
    else:
        severity, score, impact = "LOW", 2, "LOW"
        explanation = (
            f"Operating costs consume just {costs/revenue:.0%} of revenues. Healthy gross margins "
            f"provide a buffer against moderate revenue deviations."
        )
        mitigation = "Maintain routine market monitoring to sustain the favourable margin position."

    return _make_risk("Revenue Risk", impact, severity, score, explanation, mitigation)


def assess_cost_risk(inputs: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
    revenue = float(inputs.get("annual_revenue", 0))
    costs = float(inputs.get("operating_costs", 0))
    investment = float(inputs.get("initial_investment", 0))

    if investment > 0:
        cost_intensity = costs / investment
    else:
        cost_intensity = 0.5

    if revenue > 0 and costs > revenue * 0.75:
        severity, score, impact = "HIGH", 7, "HIGH"
        explanation = (
            f"Operating costs are {costs/revenue:.0%} of revenue, leaving a thin margin. Cost escalation "
            f"beyond assumptions will rapidly compress profitability."
        )
        mitigation = "Negotiate fixed-price contracts, implement strict cost controls, and build cost contingency."
    elif revenue > 0 and costs > revenue * 0.5:
        severity, score, impact = "MODERATE", 5, "MODERATE"
        explanation = (
            f"Operating costs are {costs/revenue:.0%} of revenue. Cost escalation is a relevant "
            f"but manageable risk given the current margins."
        )
        mitigation = "Benchmark cost assumptions and hedge input-price exposure where possible."
    else:
        severity, score, impact = "LOW", 2, "LOW"
        explanation = (
            f"Operating costs are {costs/revenue:.0%} of revenue. Costs are well contained relative to the "
            f"revenue base, providing good headroom against escalation."
        )
        mitigation = "Maintain routine cost tracking and monitoring."

    return _make_risk("Operating-Cost Risk", impact, severity, score, explanation, mitigation)


def assess_wacc_risk(inputs: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
    wacc = float(inputs.get("wacc", 0.1))
    irr = metrics.get("irr", 0)
    spread = irr - wacc

    if spread < 0:
        severity, score, impact = "HIGH", 8, "HIGH"
        explanation = (
            f"The project IRR ({irr:.1%}) is below the discount rate ({wacc:.1%}). The project does not "
            f"generate returns above its cost of capital, and any rise in rates worsens the position."
        )
        mitigation = "Consider restructuring capital, refinancing, or renegotiating the discount rate."
    elif spread < 0.02:
        severity, score, impact = "MODERATE", 5, "MODERATE"
        explanation = (
            f"The project IRR ({irr:.1%}) provides a cushion of only {spread:.1%} over the discount rate "
            f"({wacc:.1%}). Modest rises in the cost of capital could strip the project of its return advantage."
        )
        mitigation = "Lock in financing rates and evaluate rate-sensitive performance risks."
    else:
        severity, score, impact = "LOW", 2, "LOW"
        explanation = (
            f"The project IRR ({irr:.1%}) provides a cushion of {spread:.1%} over the discount rate "
            f"({wacc:.1%}). The project can absorb meaningful rises in the cost of capital."
        )
        mitigation = "Continue to monitor the rate environment but risk is contained."

    return _make_risk("WACC / Interest-Rate Risk", impact, severity, score, explanation, mitigation)


def assess_value_creation_risk(inputs: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
    npv = metrics.get("npv", 0)
    initial_investment = float(inputs.get("initial_investment", 0))

    if initial_investment == 0:
        return _make_risk("Value-Creation (Breakeven) Risk", "MODERATE", "MODERATE", 5,
                          "Cannot assess value-creation breakeven without an initial investment.",
                          "Provide investment data.")

    ratio = npv / initial_investment

    if npv < 0:
        severity, score, impact = "VERY HIGH", 9, "VERY HIGH"
        explanation = (
            f"NPV of ${npv:,.0f} is negative. The project does not recover its cost of capital, "
            f"and even the base case destroys value."
        )
        mitigation = "Refrain from investing until assumptions are materially improved."
    elif ratio < 0.10:
        severity, score, impact = "MODERATE", 5, "MODERATE"
        explanation = (
            f"NPV of ${npv:,.0f} is only {ratio:.1%} of the initial investment of ${initial_investment:,.0f}. "
            f"The margin above breakeven is thin; plausible deviations could reverse the outcome."
        )
        mitigation = "Stress-test revenue and cost assumptions and monitor variance closely."
    else:
        severity, score, impact = "LOW", 2, "LOW"
        explanation = (
            f"NPV of ${npv:,.0f} exceeds 10% of the initial investment (${ratio:.1%}), providing a robust "
            f"buffer against reasonably foreseeable deviations from the base case."
        )
        mitigation = "Standard monitoring and variance reporting."

    return _make_risk("Value-Creation (Breakeven) Risk", impact, severity, score, explanation, mitigation)


def assess_recovery_risk(inputs: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
    payback = metrics.get("payback", float("inf"))
    project_life = float(inputs.get("project_life", 10))

    if payback == float("inf") or payback > project_life:
        severity, score, impact = "VERY HIGH", 9, "VERY HIGH"
        explanation = (
            f"Payback of {payback:.1f} years exceeds the {int(project_life)}-year project life. "
            f"The initial investment is never recovered within the operating window."
        )
        mitigation = "Reconsider investment size or extend project life if feasible."
    elif payback > project_life * 0.7:
        severity, score, impact = "MODERATE", 5, "MODERATE"
        explanation = (
            f"Payback of {payback:.1f} years is late in the {int(project_life)}-year project life, "
            f"leaving limited time to recoup capital and generate surplus."
        )
        mitigation = "Accelerate revenue collection and tighten cost control."
    else:
        severity, score, impact = "LOW", 2, "LOW"
        explanation = (
            f"Payback of {payback:.1f} years is well within the {int(project_life)}-year project life, "
            f"providing early capital recovery and reducing liquidity exposure."
        )
        mitigation = "Maintain current cash-collection discipline."

    return _make_risk("Investment-Recovery (Payback) Risk", impact, severity, score, explanation, mitigation)


def assess_cashflow_timing_risk(inputs: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
    cash_flows = metrics.get("cash_flows", [])
    if len(cash_flows) < 2:
        return _make_risk("Cash-Flow Timing Risk", "MODERATE", "MODERATE", 5,
                          "Insufficient data to assess cash-flow timing.",
                          "Provide more data.")

    first_years_negative = sum(1 for cf in cash_flows[1:3] if cf < 0) if len(cash_flows) >= 3 else 0

    if first_years_negative >= 2:
        severity, score, impact = "HIGH", 7, "HIGH"
        explanation = (
            "The project generates negative operating cash flows in the first two operating years. "
            "This delays value creation and increases timing risk."
        )
        mitigation = "Structure financing to bridge early-period cash gaps."
    elif first_years_negative == 1:
        severity, score, impact = "MODERATE", 5, "MODERATE"
        explanation = (
            "One of the first two years has negative cash flow. Timing risk is present but limited."
        )
        mitigation = "Monitor early cash flows and maintain liquidity buffers."
    else:
        severity, score, impact = "LOW", 2, "LOW"
        explanation = (
            "The project begins generating net cash flow immediately, reducing cash-flow timing risk "
            "relative to the base case."
        )
        mitigation = "Sustain early-phase execution discipline."

    return _make_risk("Cash-Flow Timing Risk", impact, severity, score, explanation, mitigation)


def assess_inflation_risk(inputs: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
    revenue_growth = float(inputs.get("revenue_growth", inputs.get("growth_rate", 0)))
    cost_growth = float(inputs.get("cost_growth", inputs.get("growth_rate", 0)))

    if revenue_growth == 0 and cost_growth == 0:
        severity, score, impact = "MODERATE", 5, "MODERATE"
        explanation = (
            "No explicit growth assumptions were entered. Cash flows are modelled in nominal terms "
            "with no inflation adjustment, so inflation risk is largely unmeasured and potentially understated."
        )
        mitigation = "Add explicit revenue and cost growth assumptions to model inflation explicitly."
    elif cost_growth > revenue_growth:
        severity, score, impact = "MODERATE", 5, "MODERATE"
        explanation = (
            f"Cost growth ({cost_growth:.1%}) exceeds revenue growth ({revenue_growth:.1%}). "
            f"Margins compress over time, exposing the project to inflation-driven cost pressure."
        )
        mitigation = "Re-align cost and revenue escalators."
    else:
        severity, score, impact = "LOW", 2, "LOW"
        explanation = (
            f"Revenue growth ({revenue_growth:.1%}) meets or exceeds cost growth ({cost_growth:.1%}), "
            f"suggesting margins are preserved in real terms against inflation."
        )
        mitigation = "Keep inflation assumptions under periodic review."

    return _make_risk("Inflation Risk", impact, severity, score, explanation, mitigation)


def assess_liquidity_risk(inputs: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
    payback = metrics.get("payback", float("inf"))
    project_life = float(inputs.get("project_life", 10))

    if payback == float("inf"):
        severity, score, impact = "VERY HIGH", 9, "VERY HIGH"
        explanation = "Capital is never recovered, leaving liquidity permanently committed at risk."
        mitigation = "Reconsider the investment entirely."
    elif payback > project_life * 0.6:
        severity, score, impact = "MODERATE", 5, "MODERATE"
        explanation = (
            f"Capital is recovered over {payback:.1f} years based on the payback profile, tying up "
            f"liquidity until recovery completes. Liquidity stays restricted during this window."
        )
        mitigation = "Monitor debt-covenant headroom and maintain contingency credit lines."
    else:
        severity, score, impact = "LOW", 2, "LOW"
        explanation = (
            f"Payback of {payback:.1f} years releases liquidity relatively early in the "
            f"{int(project_life)}-year life, limiting the period capital is tied up."
        )
        mitigation = "Maintain standard liquidity reserves."

    return _make_risk("Liquidity Risk", impact, severity, score, explanation, mitigation)


def assess_profitability_risk(inputs: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
    roi = metrics.get("roi", 0)

    if roi < 0:
        severity, score, impact = "VERY HIGH", 9, "VERY HIGH"
        explanation = (
            f"ROI of {roi:.1%} is negative. The project generates a total return below its committed capital, "
            f"indicating a loss over the project life."
        )
        mitigation = "Do not proceed without substantial restructuring."
    elif roi < 0.10:
        severity, score, impact = "MODERATE", 5, "MODERATE"
        explanation = (
            f"ROI of {roi:.1%} is modest for the capital deployed. Returns may not adequately compensate "
            f"for risk over the project's long horizon."
        )
        mitigation = "Re-evaluate return expectations vs. opportunity cost of capital."
    else:
        severity, score, impact = "LOW", 2, "LOW"
        explanation = (
            f"ROI of {roi:.1%} provides a strong total return relative to the initial investment."
        )
        mitigation = "Retain the current approach while tracking actual vs budgeted performance."

    return _make_risk("Profitability-Sustainability Risk", impact, severity, score, explanation, mitigation)


def assess_fx_risk(inputs: Dict[str, Any], metrics: Dict[str, Any],
                   fx_risk: Dict[str, Any]) -> Dict[str, Any]:
    level = (fx_risk.get("level") or "MODERATE").upper()
    score_in = float(fx_risk.get("score") or 5.0)
    exposure = fx_risk.get("exposure", {}) or {}

    exp_level = (exposure.get("level") or "MODERATE").upper()
    swing = abs(float(fx_risk.get("swing_pct") or 0.0))

    base = 0.0
    if level == "LOW":
        base = 2.0
    elif level == "MODERATE":
        base = 4.0
    else:
        base = 7.0

    if exp_level == "HIGH":
        base += 2.0
    elif exp_level == "MODERATE":
        base += 1.0

    if swing >= 15:
        base += 2.0
    elif swing >= 7:
        base += 1.0

    score = int(round(min(10.0, max(1.0, base))))

    if score <= 3:
        severity, impact = "LOW", "LOW"
    elif score <= 5:
        severity, impact = "MODERATE", "MODERATE"
    elif score <= 7:
        severity, impact = "HIGH", "HIGH"
    else:
        severity, impact = "VERY HIGH", "VERY HIGH"

    explanation = (
        f"Market FX risk is {level} (score {score_in:.1f}/10) and the project's net currency exposure "
        f"is {exp_level}. Across the ±5% exchange-rate scenarios NPV moves by up to {swing:.1f}%. "
        f"Any material move in USD / ZiG / ZAR changes the project's cash flows, NPV, IRR and payback "
        f"in the base currency. This risk is driven by live market volatility where a data feed is "
        f"available; ZiG estimates carry additional uncertainty."
    )
    mitigation = (
        "Match revenue and cost currencies (natural hedging), hold USD cash when foreign inflows are "
        "large, convert to ZiG only for near-term local obligations, and re-run the FX scenario analysis "
        "whenever rates move materially."
    )

    return _make_risk("Currency / FX Risk", impact, severity, score, explanation, mitigation)


def get_risk_summary(risk_data: Dict[str, Any]) -> str:
    overall = risk_data["overall_level"]
    score = risk_data["overall_score"]

    high_risks = [r for r in risk_data["risks"] if r["severity"] in ("HIGH", "VERY HIGH")]
    med_risks = [r for r in risk_data["risks"] if r["severity"] == "MODERATE"]
    low_risks = [r for r in risk_data["risks"] if r["severity"] == "LOW"]

    lines = [
        f"**Overall Risk Level: {overall}** (Score: {score:.1f}/10)",
        f"- High risks: {len(high_risks)}",
        f"- Moderate risks: {len(med_risks)}",
        f"- Low risks: {len(low_risks)}",
        "",
    ]

    if high_risks:
        lines.append("**Key Concerns:**")
        for r in high_risks:
            lines.append(f"- {r['name']}: {r['explanation'][:100]}...")

    return "\n".join(lines)
