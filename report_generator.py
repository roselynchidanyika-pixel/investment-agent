import os
import tempfile
from datetime import datetime
from typing import Dict, Any, Optional

from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn


def generate_management_report(
    inputs: Dict[str, Any],
    metrics: Dict[str, Any],
    risk_data: Dict[str, Any],
    scenario_data: Dict[str, Any],
    sensitivity_data: Dict[str, Any],
    fx_data: Optional[Dict[str, Any]] = None,
    final_decision: Optional[Dict[str, Any]] = None,
    fx_market: Optional[Dict[str, Any]] = None,
    fx_scenarios: Optional[Dict[str, Any]] = None,
    fx_exposure: Optional[Dict[str, Any]] = None,
    currency_strategy: Optional[Dict[str, Any]] = None,
    fx_risk: Optional[Dict[str, Any]] = None,
) -> str:
    doc = Document()

    style = doc.styles["Normal"]
    font = style.font
    font.name = "Arial"
    font.size = Pt(10)

    _add_title_page(doc, inputs, metrics, final_decision)
    doc.add_page_break()

    _add_executive_summary(doc, inputs, metrics, risk_data, final_decision)
    _add_investment_proposal(doc, inputs)
    _add_input_assumptions(doc, inputs)
    _add_data_sources_section(doc)
    _add_methodology(doc)
    _add_capital_budgeting(doc, metrics)
    _add_dcf_valuation(doc, metrics, inputs)
    _add_npv_analysis(doc, metrics)
    _add_irr_analysis(doc, metrics)
    _add_mirr_analysis(doc, metrics)
    _add_roi_analysis(doc, metrics)
    _add_payback_analysis(doc, metrics)
    _add_profitability_index(doc, metrics)
    _add_risk_analysis(doc, risk_data)
    _add_scenario_analysis(doc, scenario_data)
    _add_sensitivity_analysis(doc, sensitivity_data)
    if fx_market:
        _add_fx_market_section(doc, fx_market)
    if fx_exposure or fx_scenarios:
        _add_fx_scenario_section(doc, fx_exposure, fx_scenarios, inputs)
    if currency_strategy:
        _add_fx_strategy_section(doc, currency_strategy, fx_risk, fx_market)
    if fx_data:
        _add_fx_section(doc, fx_data)
    _add_final_decision(doc, final_decision, metrics, risk_data, scenario_data, fx_risk, currency_strategy)
    _add_recommendations(doc, final_decision, metrics)
    _add_limitations(doc)

    output_path = os.path.join(tempfile.gettempdir(), f"Management_Report_{inputs.get('project_name', 'Project').replace(' ', '_')}.docx")
    doc.save(output_path)
    return output_path


def _add_title_page(doc, inputs, metrics, final_decision):
    for _ in range(6):
        doc.add_paragraph()

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("INVESTMENT DECISION\nMANAGEMENT REPORT")
    run.bold = True
    run.font.size = Pt(28)
    run.font.color.rgb = RGBColor(0, 51, 102)

    doc.add_paragraph()

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle.add_run(inputs.get("project_name", "Project"))
    run.font.size = Pt(18)
    run.font.color.rgb = RGBColor(0, 102, 153)

    doc.add_paragraph()

    date_para = doc.add_paragraph()
    date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = date_para.add_run(f"Generated: {datetime.now().strftime('%B %d, %Y')}")
    run.font.size = Pt(12)
    run.font.color.rgb = RGBColor(100, 100, 100)

    if final_decision:
        doc.add_paragraph()
        decision_para = doc.add_paragraph()
        decision_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        decision = final_decision.get("decision", "N/A")
        run = decision_para.add_run(f"RECOMMENDATION: {decision}")
        run.bold = True
        run.font.size = Pt(16)
        if decision == "ACCEPT":
            run.font.color.rgb = RGBColor(0, 128, 0)
        elif decision == "REJECT":
            run.font.color.rgb = RGBColor(200, 0, 0)
        else:
            run.font.color.rgb = RGBColor(200, 160, 0)


def _add_heading(doc, text, level=1):
    heading = doc.add_heading(text, level=level)
    for run in heading.runs:
        run.font.color.rgb = RGBColor(0, 51, 102)
    return heading


def _add_styled_table(doc, headers, rows, col_widths=None):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Light Grid Accent 1"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    for i, header in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = header
        for paragraph in cell.paragraphs:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in paragraph.runs:
                run.bold = True
                run.font.size = Pt(9)
                run.font.name = "Arial"

    for r_idx, row in enumerate(rows):
        for c_idx, value in enumerate(row):
            cell = table.rows[r_idx + 1].cells[c_idx]
            cell.text = str(value)
            for paragraph in cell.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in paragraph.runs:
                    run.font.size = Pt(9)
                    run.font.name = "Arial"

    doc.add_paragraph()
    return table


def _add_executive_summary(doc, inputs, metrics, risk_data, final_decision):
    _add_heading(doc, "1. Executive Summary")
    currency = inputs.get("currency", "USD")
    from data_validation import format_currency, format_pct

    if final_decision:
        decision = final_decision.get("decision", "N/A")
        reason = final_decision.get("reason", "")
    else:
        decision = metrics.get("npv_status", {}).get("decision", "N/A")
        reason = metrics.get("npv_status", {}).get("reason", "")

    doc.add_paragraph(f"Project: {inputs.get('project_name', 'N/A')}")
    doc.add_paragraph(f"Investment Amount: {format_currency(float(inputs.get('initial_investment', 0)), currency)}")
    doc.add_paragraph(f"Project Life: {int(float(inputs.get('project_life', 0)))} years")
    doc.add_paragraph()

    summary_rows = [
        ["NPV", format_currency(metrics["npv"], currency), metrics["npv_status"]["decision"]],
        ["IRR", format_pct(metrics["irr"]), metrics["irr_status"]["decision"]],
        ["MIRR", format_pct(metrics["mirr"]), metrics["mirr_status"]["decision"]],
        ["PI", f"{metrics['pi']:.2f}", metrics["pi_status"]["decision"]],
        ["ROI", format_pct(metrics["roi"]), metrics["roi_status"]["decision"]],
        ["Payback", f"{metrics['payback']:.1f} years" if metrics['payback'] != float('inf') else "N/A", metrics["payback_status"]["decision"]],
        ["Risk Level", risk_data["overall_level"], ""],
    ]
    _add_styled_table(doc, ["Metric", "Value", "Decision"], summary_rows)

    p = doc.add_paragraph()
    run = p.add_run(f"Final Recommendation: {decision}")
    run.bold = True
    run.font.size = Pt(14)
    if decision == "ACCEPT":
        run.font.color.rgb = RGBColor(0, 128, 0)
    elif decision == "REJECT":
        run.font.color.rgb = RGBColor(200, 0, 0)
    else:
        run.font.color.rgb = RGBColor(200, 160, 0)

    doc.add_paragraph(reason)


def _add_investment_proposal(doc, inputs):
    _add_heading(doc, "2. Investment Proposal")
    doc.add_paragraph(f"Project Name: {inputs.get('project_name', 'N/A')}")
    doc.add_paragraph(f"Project Description: {inputs.get('project_description', 'No description provided.')}")
    doc.add_paragraph(f"Currency: {inputs.get('currency', 'USD')}")
    doc.add_paragraph()


def _add_input_assumptions(doc, inputs):
    _add_heading(doc, "3. Input Assumptions")
    from data_validation import format_currency, format_pct
    currency = inputs.get("currency", "USD")

    assumptions = [
        ["Initial Investment", format_currency(float(inputs.get('initial_investment', 0)), currency)],
        ["Project Life", f"{int(float(inputs.get('project_life', 0)))} years"],
        ["Annual Revenue", format_currency(float(inputs.get('annual_revenue', 0)), currency)],
        ["Operating Costs", format_currency(float(inputs.get('operating_costs', 0)), currency)],
        ["Tax Rate", format_pct(float(inputs.get('tax_rate', 0.25)))],
        ["Working Capital", format_currency(float(inputs.get('working_capital', 0)), currency)],
        ["Terminal Value", format_currency(float(inputs.get('terminal_value', 0)), currency)],
        ["WACC", format_pct(float(inputs.get('wacc', 0.1)))],
        ["Financing Rate", format_pct(float(inputs.get('financing_rate', 0.08)))],
        ["Reinvestment Rate", format_pct(float(inputs.get('reinvestment_rate', 0.06)))],
        ["Revenue Growth", format_pct(float(inputs.get('revenue_growth', inputs.get('growth_rate', 0.03))))],
        ["Cost Growth", format_pct(float(inputs.get('cost_growth', inputs.get('growth_rate', 0.03))))],
        ["Terminal Growth", format_pct(float(inputs.get('terminal_growth', 0)))],
        ["Depreciation Rate", format_pct(float(inputs.get('depreciation_rate', 0.1)))],
    ]
    _add_styled_table(doc, ["Parameter", "Value"], assumptions)


def _add_data_sources_section(doc):
    _add_heading(doc, "4. Data Sources")
    doc.add_paragraph("All financial data in this report is derived from user-provided inputs and manual calculations.")
    doc.add_paragraph("Data Categories:", style="List Bullet")
    doc.add_paragraph("User-Provided Data: All project financial assumptions including revenues, costs, investment amounts, and rates", style="List Bullet 2")
    doc.add_paragraph("Model Assumptions: Straight-line depreciation, constant tax rates, and standard DCF methodology", style="List Bullet 2")
    doc.add_paragraph("Exchange Rates: Live rates obtained from open exchange rate APIs (where applicable)", style="List Bullet 2")
    doc.add_paragraph("No external market data or third-party financial databases are used without explicit user provision.", style="List Bullet")


def _add_methodology(doc):
    _add_heading(doc, "5. Methodology")
    methods = [
        ("Discounted Cash Flow (DCF)", "Future cash flows are discounted to present value using the Weighted Average Cost of Capital (WACC). Terminal values are calculated using the perpetuity growth method."),
        ("Net Present Value (NPV)", "Sum of all discounted cash flows including the initial investment. A positive NPV indicates value creation."),
        ("Internal Rate of Return (IRR)", "The discount rate at which NPV equals zero. Compared against WACC for decision making."),
        ("Modified IRR (MIRR)", "Adjusts for more realistic reinvestment and financing rate assumptions. Provides a more accurate return measure than standard IRR."),
        ("Profitability Index (PI)", "Ratio of the present value of future cash flows to the initial investment. PI > 1 indicates value creation per dollar invested."),
        ("Payback Period", "Time required to recover the initial investment from operating cash flows."),
        ("Risk Assessment", "Multi-factor analysis covering revenue, cost, interest rate, inflation, exchange rate, liquidity, recovery, and cash flow risks."),
        ("Scenario Analysis", "Best case (+20% revenue, -10% costs), Base case (as provided), Worst case (-20% revenue, +10% costs)."),
        ("Sensitivity Analysis", "One-at-a-time variation of key inputs to measure their impact on NPV and other metrics."),
    ]
    for title, desc in methods:
        p = doc.add_paragraph()
        run = p.add_run(f"{title}: ")
        run.bold = True
        p.add_run(desc)


def _add_capital_budgeting(doc, metrics):
    _add_heading(doc, "6. Capital Budgeting Analysis")
    from data_validation import format_currency

    table_data = metrics["cash_flow_table"]
    headers = [c for c in table_data.columns]
    rows = []
    for _, row in table_data.iterrows():
        row_vals = []
        for c in headers:
            v = row[c]
            if c == "Year":
                row_vals.append(int(v))
            else:
                row_vals.append(format_currency(v))
        rows.append(row_vals)
    _add_styled_table(doc, headers, rows)

    dcf_data = metrics["dcf_table"]
    dcf_headers = ["Year", "Net Cash Flow", "Discount Factor", "Present Value", "Cumulative PV"]
    dcf_rows = []
    for _, row in dcf_data.iterrows():
        dcf_rows.append([
            int(row["Year"]),
            format_currency(row["Free Cash Flow"]),
            f"{row['Discount Factor']:.4f}",
            format_currency(row["Present Value"]),
            format_currency(row["Cumulative Present Value"]),
        ])
    _add_styled_table(doc, dcf_headers, dcf_rows)


def _add_dcf_valuation(doc, metrics, inputs):
    _add_heading(doc, "7. DCF Valuation")
    from data_validation import format_currency, format_pct
    currency = inputs.get("currency", "USD")

    doc.add_paragraph(f"Discount Rate (WACC): {format_pct(metrics['wacc'])}")
    doc.add_paragraph(f"Total PV of Operating Cash Flows: {format_currency(metrics['total_pv_inflows'], currency)}")
    if metrics["terminal_value"] > 0:
        doc.add_paragraph(f"Terminal Value: {format_currency(metrics['terminal_value'], currency)}")
        pv_terminal = metrics["terminal_value"] / (1 + metrics["wacc"]) ** metrics["project_life"]
        doc.add_paragraph(f"PV of Terminal Value: {format_currency(pv_terminal, currency)}")
    doc.add_paragraph(f"Total DCF Value: {format_currency(metrics['dcf_value'], currency)}")
    doc.add_paragraph(f"Initial Investment: {format_currency(metrics['initial_investment'], currency)}")
    doc.add_paragraph(f"Net Value Created: {format_currency(metrics['dcf_value'] - metrics['initial_investment'], currency)}")

    doc.add_paragraph()
    if metrics["dcf_value"] >= metrics["initial_investment"]:
        doc.add_paragraph(
            f"The DCF value of {format_currency(metrics['dcf_value'], currency)} exceeds the initial investment "
            f"of {format_currency(metrics['initial_investment'], currency)}, indicating the project creates value."
        )
    else:
        doc.add_paragraph(
            f"The DCF value of {format_currency(metrics['dcf_value'], currency)} is below the initial investment "
            f"of {format_currency(metrics['initial_investment'], currency)}, indicating the project does not "
            f"create sufficient value to justify the investment."
        )


def _add_npv_analysis(doc, metrics):
    _add_heading(doc, "8. NPV Analysis")
    from data_validation import format_currency
    currency = metrics.get("currency", "USD")

    p = doc.add_paragraph()
    run = p.add_run(f"NPV: {format_currency(metrics['npv'], currency)}")
    run.bold = True
    doc.add_paragraph(f"Decision: {metrics['npv_status']['decision']}")
    doc.add_paragraph(f"Reason: {metrics['npv_status']['reason']}")


def _add_irr_analysis(doc, metrics):
    _add_heading(doc, "9. IRR Analysis")
    from data_validation import format_pct

    p = doc.add_paragraph()
    run = p.add_run(f"IRR: {format_pct(metrics['irr'])}")
    run.bold = True
    doc.add_paragraph(f"WACC: {format_pct(metrics['wacc'])}")
    doc.add_paragraph(f"Decision: {metrics['irr_status']['decision']}")
    doc.add_paragraph(f"Reason: {metrics['irr_status']['reason']}")


def _add_mirr_analysis(doc, metrics):
    _add_heading(doc, "10. MIRR Analysis")
    from data_validation import format_pct

    p = doc.add_paragraph()
    run = p.add_run(f"MIRR: {format_pct(metrics['mirr'])}")
    run.bold = True
    doc.add_paragraph(f"Financing Rate: {format_pct(metrics['financing_rate'])}")
    doc.add_paragraph(f"Reinvestment Rate: {format_pct(metrics['reinvestment_rate'])}")
    doc.add_paragraph(f"Decision: {metrics['mirr_status']['decision']}")
    doc.add_paragraph(f"Reason: {metrics['mirr_status']['reason']}")


def _add_roi_analysis(doc, metrics):
    _add_heading(doc, "11. ROI Analysis")
    from data_validation import format_pct

    p = doc.add_paragraph()
    run = p.add_run(f"ROI: {format_pct(metrics['roi'])}")
    run.bold = True
    doc.add_paragraph(f"Decision: {metrics['roi_status']['decision']}")
    doc.add_paragraph(f"Reason: {metrics['roi_status']['reason']}")


def _add_payback_analysis(doc, metrics):
    _add_heading(doc, "12. Payback Period Analysis")
    payback = metrics["payback"]
    payback_str = f"{payback:.1f} years" if payback != float("inf") else "Does not pay back"

    p = doc.add_paragraph()
    run = p.add_run(f"Payback Period: {payback_str}")
    run.bold = True
    doc.add_paragraph(f"Project Life: {int(metrics['project_life'])} years")
    doc.add_paragraph(f"Decision: {metrics['payback_status']['decision']}")
    doc.add_paragraph(f"Reason: {metrics['payback_status']['reason']}")


def _add_profitability_index(doc, metrics):
    _add_heading(doc, "13. Profitability Index")
    from data_validation import format_currency

    p = doc.add_paragraph()
    run = p.add_run(f"Profitability Index: {metrics['pi']:.2f}")
    run.bold = True
    doc.add_paragraph(f"PV of Future Cash Flows: {format_currency(metrics['total_pv_inflows'], metrics.get('currency', 'USD'))}")
    doc.add_paragraph(f"Initial Investment: {format_currency(metrics['initial_investment'], metrics.get('currency', 'USD'))}")
    doc.add_paragraph(f"Decision: {metrics['pi_status']['decision']}")
    doc.add_paragraph(f"Reason: {metrics['pi_status']['reason']}")


def _add_risk_analysis(doc, risk_data):
    _add_heading(doc, "14. Risk Analysis")
    doc.add_paragraph(f"Overall Risk Level: {risk_data['overall_level']} (Score: {risk_data['overall_score']:.1f}/10)")
    doc.add_paragraph()

    headers = ["Risk Factor", "Severity", "Impact", "Mitigation"]
    rows = []
    for risk in risk_data["risks"]:
        rows.append([risk["name"], risk["severity"], risk.get("impact_text", risk.get("impact", "")), risk["mitigation"][:80] + "..."])
    _add_styled_table(doc, headers, rows)

    for risk in risk_data["risks"]:
        p = doc.add_paragraph()
        run = p.add_run(f"{risk['name']} ({risk['severity']}): ")
        run.bold = True
        p.add_run(risk["explanation"])


def _add_scenario_analysis(doc, scenario_data):
    _add_heading(doc, "15. Scenario Analysis")
    from data_validation import format_currency, format_pct

    for label, key in [("Best Case", "best_case"), ("Base Case", "base_case"), ("Worst Case", "worst_case")]:
        scenario = scenario_data[key]
        _add_heading(doc, label, level=2)
        doc.add_paragraph(f"Description: {scenario.get('scenario_description', '')}")

        currency = scenario.get("currency", "USD")
        payback_str = f"{scenario['payback']:.1f} years" if scenario['payback'] != float("inf") else "N/A"

        rows = [
            ["NPV", format_currency(scenario["npv"], currency)],
            ["IRR", format_pct(scenario["irr"])],
            ["MIRR", format_pct(scenario["mirr"])],
            ["PI", f"{scenario['pi']:.2f}"],
            ["ROI", format_pct(scenario["roi"])],
            ["Payback", payback_str],
            ["Decision", scenario["npv_status"]["decision"]],
        ]
        _add_styled_table(doc, ["Metric", "Value"], rows)
        scenario_reason = scenario.get("scenario_reason", scenario["npv_status"]["reason"])
        doc.add_paragraph(f"Explanation: {scenario_reason}")


def _add_sensitivity_analysis(doc, sensitivity_data):
    _add_heading(doc, "16. Sensitivity Analysis")
    from data_validation import format_currency

    if sensitivity_data.get("ranking"):
        doc.add_paragraph("Variable Sensitivity Ranking (by NPV impact):")
        for i, item in enumerate(sensitivity_data["ranking"], 1):
            doc.add_paragraph(f"{i}. {item['variable']} (NPV range: ${item['npv_range']:,.0f})", style="List Number")

        doc.add_paragraph()
        doc.add_paragraph(
            f"Most sensitive variable: {sensitivity_data['most_sensitive']}. "
            f"Changes in this variable have the largest impact on project value."
        )
        doc.add_paragraph(
            f"Least sensitive variable: {sensitivity_data['least_sensitive']}. "
            f"Changes in this variable have the smallest impact on project value."
        )

    for item in sensitivity_data.get("ranking", []):
        label = item.get("label", item.get("variable", ""))
        _add_heading(doc, f"Sensitivity: {label}", level=2)
        doc.add_paragraph(
            f"NPV at -30%: {format_currency(item.get('npv_at_minus30', 0))} | "
            f"NPV at base: {format_currency(item.get('npv_at_base', 0))} | "
            f"NPV at +30%: {format_currency(item.get('npv_at_plus30', 0))}"
        )
        sens_data = sensitivity_data.get("sensitivities", {}).get(item.get("variable", ""))
        if sens_data:
            df = sens_data["results"]
            if not df.empty:
                headers = list(df.columns)
                rows = df.values.tolist()
                _add_styled_table(doc, headers, [[str(v) for v in row] for row in rows])


def _add_fx_market_section(doc, fx_market):
    _add_heading(doc, "17. FX Market Monitor")
    doc.add_paragraph(
        "Live exchange rates monitored for the multi-currency environment (USD / ZiG / ZAR). "
        "ZAR values are live where the API responds; ZiG values are managed estimates because no "
        "reliable public ZIG feed is available. No assumption is made about the future direction of "
        "any currency."
    )

    pairs = fx_market.get("pairs", [])
    rows = []
    for p in pairs:
        rows.append([
            p.get("pair", ""),
            f"{p.get('rate', 0):.4f}",
            f"{p.get('daily_change_pct', 0):+.2f}%",
            f"{p.get('month_trend_pct', 0):+.2f}%",
            "Live API" if p.get("source") == "live" else "Estimate",
        ])
    if rows:
        _add_styled_table(doc, ["Pair", "Current Rate", "Daily Change", "1-Month Trend", "Source"], rows)

    doc.add_paragraph()
    p = doc.add_paragraph()
    run = p.add_run(f"FX Risk Level: {fx_market.get('fx_risk_level', 'MODERATE')} ")
    run.bold = True
    p.add_run(f"(score {fx_market.get('fx_risk_score', 5.0):.1f}/10). "
              f"Updated {fx_market.get('as_of', datetime.now()).strftime('%Y-%m-%d %H:%M')}.")


def _add_fx_scenario_section(doc, fx_exposure, fx_scenarios, inputs):
    _add_heading(doc, "18. FX-Adjusted Investment Analysis")
    currency = inputs.get("currency", "USD")

    if fx_exposure:
        doc.add_paragraph("Currency Exposure:")
        exp_rows = [
            ["Revenue exposure", f"{fx_exposure.get('revenue_exposure', 0):.0%}"],
            ["Cost exposure", f"{fx_exposure.get('cost_exposure', 0):.0%}"],
            ["Investment exposure", f"{fx_exposure.get('investment_exposure', 0):.0%}"],
            ["Net exposure", f"{fx_exposure.get('level', 'LOW')} ({fx_exposure.get('net_exposure', 0):.0%})"],
        ]
        _add_styled_table(doc, ["Component", "Value"], exp_rows)
        doc.add_paragraph(fx_exposure.get("explanation", ""))

    if fx_scenarios:
        doc.add_paragraph()
        doc.add_paragraph("FX Scenario Analysis (±5%):")
        results = fx_scenarios.get("results", [])
        scen_rows = []
        for r in results:
            payback = r.get("payback", float("inf"))
            scen_rows.append([
                r.get("label", ""),
                f"{r.get('npv', 0):,.0f}",
                f"{r.get('npv_delta', 0):+,.0f}",
                f"{r.get('irr', 0):.1%}",
                f"{payback:.1f}" if payback != float("inf") else "N/A",
                r.get("npv_status", ""),
            ])
        if scen_rows:
            _add_styled_table(doc, ["Scenario", "NPV", "NPV Change", "IRR", "Payback (yrs)", "Decision"], scen_rows)

        doc.add_paragraph()
        p = doc.add_paragraph()
        run = p.add_run(f"Maximum NPV swing across scenarios: {fx_scenarios.get('max_npv_swing_pct', 0):.1f}% ")
        run.bold = True
        p.add_run(f"(FX sensitivity: {fx_scenarios.get('fx_sensitivity_level', 'LOW')}).")
        declined = fx_scenarios.get("scenarios_declined", [])
        if declined:
            doc.add_paragraph(f"Scenarios that would turn the project non-viable: {', '.join(declined)}.")
        else:
            doc.add_paragraph("The project remains viable under all ±5% exchange-rate scenarios.")


def _add_fx_strategy_section(doc, currency_strategy, fx_risk, fx_market):
    _add_heading(doc, "19. Currency Strategy Recommendation")

    strategy = currency_strategy.get("strategy", "REVIEW")
    rec_text = currency_strategy.get("recommendation_text", strategy)
    p = doc.add_paragraph()
    run = p.add_run(f"Recommended Currency Strategy: {rec_text}")
    run.bold = True
    run.font.size = Pt(14)
    run.font.color.rgb = RGBColor(0, 0, 128)

    if fx_risk:
        p = doc.add_paragraph()
        run = p.add_run(f"Project FX Risk: {fx_risk.get('level', 'MODERATE')} ")
        run.bold = True
        p.add_run(f"(score {fx_risk.get('score', 5.0):.1f}/10).")

    doc.add_paragraph(currency_strategy.get("reason", ""))

    p = doc.add_paragraph()
    run = p.add_run("Key FX Factors:")
    run.bold = True
    for factor in currency_strategy.get("key_fx_factors", []):
        doc.add_paragraph(factor, style="List Bullet")

    doc.add_paragraph(
        "This recommendation is based on live FX data where available, the project's currency "
        "requirements, expected cash flows, liquidity needs and the scenario analysis. It reflects "
        "current market conditions and does not assume that USD, ZiG or ZAR will appreciate or "
        "depreciate in the future — exchange-rate outcomes remain uncertain."
    )


def _add_fx_section(doc, fx_data):
    _add_heading(doc, "20. FX Exchange Rate Analysis")
    doc.add_paragraph("Live exchange rates were fetched for multi-currency comparison.")

    if "rates" in fx_data:
        rate_rows = []
        for pair, rate in fx_data["rates"].items():
            rate_rows.append([pair, f"{rate:.4f}"])
        if rate_rows:
            _add_styled_table(doc, ["Currency Pair", "Rate"], rate_rows)

    if "comparisons" in fx_data:
        doc.add_paragraph()
        doc.add_paragraph("Investment Comparison Across Currencies:")
        comp_rows = []
        for comp in fx_data["comparisons"]:
            comp_rows.append([
                comp.get("currency", ""),
                comp.get("investment_amount", ""),
                comp.get("equivalent_usd", ""),
            ])
        if comp_rows:
            _add_styled_table(doc, ["Currency", "Amount", "USD Equivalent"], comp_rows)


def _add_final_decision(doc, final_decision, metrics, risk_data, scenario_data, fx_risk=None, currency_strategy=None):
    _add_heading(doc, "21. Final Investment Decision")

    if not final_decision:
        doc.add_paragraph("Final decision could not be determined.")
        return

    decision = final_decision.get("decision", "N/A")
    reason = final_decision.get("reason", "")
    recommendation = final_decision.get("recommendation", "")

    doc.add_paragraph("Investment Decision Summary:")

    from data_validation import format_currency
    summary_rows = [
        ["Investment Decision", decision],
        ["Risk Score", (risk_data or {}).get("overall_level", "N/A")],
        ["FX Risk", (fx_risk or {}).get("level", "N/A")],
        ["Recommended Currency Strategy", (currency_strategy or {}).get("recommendation_text", "N/A")],
    ]
    if metrics and metrics.get("npv") is not None:
        summary_rows.append(["Net Present Value (NPV)", format_currency(metrics["npv"], "USD")])
    if metrics and metrics.get("irr") is not None:
        summary_rows.append(["Internal Rate of Return (IRR)", f"{metrics['irr']:.2%}"])
    if metrics and metrics.get("payback") is not None:
        pb = metrics["payback"]
        summary_rows.append(["Payback Period", f"{pb:.2f} years" if pb != float("inf") else "Never"])
    _add_styled_table(doc, ["Metric", "Value"], summary_rows)

    p = doc.add_paragraph()
    run = p.add_run(f"FINAL DECISION: {decision}")
    run.bold = True
    run.font.size = Pt(16)
    if decision == "ACCEPT":
        run.font.color.rgb = RGBColor(0, 128, 0)
    elif decision == "REJECT":
        run.font.color.rgb = RGBColor(200, 0, 0)
    else:
        run.font.color.rgb = RGBColor(200, 160, 0)

    doc.add_paragraph()
    p = doc.add_paragraph()
    run = p.add_run("Main Reason: ")
    run.bold = True
    p.add_run(final_decision.get("main_reason", reason))

    doc.add_paragraph()
    doc.add_paragraph("Supporting Evidence:")

    if "supporting_points" in final_decision:
        for point in final_decision["supporting_points"]:
            doc.add_paragraph(point, style="List Bullet")

    doc.add_paragraph()
    p = doc.add_paragraph()
    run = p.add_run("Recommendation: ")
    run.bold = True
    p.add_run(recommendation)


def _add_recommendations(doc, final_decision, metrics):
    _add_heading(doc, "22. Recommendations")

    if final_decision and final_decision.get("decision") == "ACCEPT":
        recs = [
            "Proceed with the investment subject to the conditions below.",
            "Establish clear milestones and performance metrics for ongoing monitoring.",
            "Set up regular review meetings to compare actual vs. projected performance.",
            "Maintain contingency reserves for unforeseen circumstances.",
            "Review the investment periodically against updated market conditions.",
        ]
    elif final_decision and final_decision.get("decision") == "REJECT":
        recs = [
            "Do not proceed under the current assumptions.",
            "Consider restructuring the project to improve financial viability.",
            "Negotiate better terms with suppliers or financing providers.",
            "Reassess revenue projections with updated market research.",
            "Consider alternative projects with better risk-adjusted returns.",
        ]
    else:
        recs = [
            "Conduct additional due diligence before making a final decision.",
            "Gather more market data to reduce uncertainty in key assumptions.",
            "Consider a phased investment approach to manage risk.",
            "Perform a detailed competitive analysis.",
            "Seek independent third-party validation of projections.",
        ]

    for rec in recs:
        doc.add_paragraph(rec, style="List Bullet")


def _add_limitations(doc):
    _add_heading(doc, "23. Limitations")
    limitations = [
        "This analysis is based entirely on user-provided inputs. The accuracy of results depends on the accuracy of these inputs.",
        "The model assumes constant annual revenues and costs (adjusted only by the specified growth rate).",
        "Depreciation is calculated using the straight-line method. Other depreciation methods may yield different tax shields.",
        "Terminal value is assumed to be a fixed amount provided by the user. More sophisticated terminal value models (e.g., perpetuity growth) may be appropriate for certain projects.",
        "Risk assessment is based on analytical indicators derived from the input data. It does not incorporate external market intelligence or proprietary risk models.",
        "Exchange rates are sourced from public APIs and may not reflect actual transaction rates available to the organization.",
        "The model does not account for inflation adjustments on revenues and costs unless specified through the growth rate.",
        "The analysis does not consider optionality, real options, or strategic value beyond the financial projections.",
        "Currency conversion comparisons are indicative only and do not account for transaction costs, capital controls, or regulatory constraints.",
        "This report is generated for informational purposes and should not be the sole basis for investment decisions.",
    ]
    for lim in limitations:
        doc.add_paragraph(lim, style="List Bullet")
