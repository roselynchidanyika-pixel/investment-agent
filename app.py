"""Integrated Investment Decision Agent for Capital Project Evaluation.

A premium, decision-first capital-investment platform with a dark navy
institutional theme. All calculations are computed live by the underlying
engines in this package (calculations, risk, scenario, fx, three-project,
reporting). No result is hard-coded.

Run:  streamlit run app.py
"""

from __future__ import annotations

import html
import io
import os
import time
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import data_validation as dv
import email_service
import fx_rates as fx
import fx_service
import report_generator as rg
import three_project as tp
from calculations import (
    ProjectInputs,
    decision_for_irr,
    decision_for_mirr,
    decision_for_npv,
    decision_for_payback,
    decision_for_pi,
    decision_for_roi,
    run_analysis,
)
from risk_analysis import assess_risks
from scenario_analysis import (
    build_scenarios,
    run_sensitivity,
    sensitivity_interpretation,
)

st.set_page_config(
    page_title="Integrated Investment Decision Agent for Capital Project Evaluation",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Constants & theme
# ---------------------------------------------------------------------------

NAV_SECTIONS = [
    "Executive Dashboard",
    "Investment Cases",
    "Capital Budgeting",
    "DCF & Valuation",
    "Returns",
    "Risk Analysis",
    "FX & Multi-Currency",
    "Scenario Analysis",
    "Sensitivity Analysis",
    "Project Comparison",
    "AI Decision",
    "Reports",
    "Settings",
]

PROJECT_TYPES = [
    "New Project",
    "Business Expansion",
    "Asset Replacement",
    "Technology/Digital Investment",
    "International/Cross-Border Investment",
]

PROJECT_TYPE_DESCRIPTIONS = {
    "New Project": (
        "A brand-new investment with no pre-existing capacity. Key risks include unproven demand, "
        "construction and ramp-up delays, and the full cost of building the asset from scratch."
    ),
    "Business Expansion": (
        "Growing existing operations by adding capacity, products, markets, or channels, with "
        "synergies in shared infrastructure, customers, or staff. Watch cannibalisation and execution speed."
    ),
    "Asset Replacement": (
        "Replacing ageing or inefficient equipment with modern equivalents. Benefits come from lower "
        "operating costs, higher availability, and fewer breakdowns — often without adding revenue."
    ),
    "Technology/Digital Investment": (
        "Software, automation, digital platforms, or IT infrastructure. Benefits are frequently indirect "
        "(productivity, data, resilience) and require prudent assumptions and shorter useful lives."
    ),
    "International/Cross-Border Investment": (
        "Entering or expanding in a foreign market. Adds currency, country, political, regulatory and "
        "operational risk. Run through the FX & Multi-Currency section and re-check when rates move."
    ),
}

_CCY = fx.CCY_LABELS

_PALETTE = {
    "primary": "#38BDF8",
    "accent": "#22D3EE",
    "gold": "#FBBF24",
    "green": "#34D399",
    "red": "#F87171",
    "orange": "#F59E0B",
    "violet": "#A78BFA",
    "mutemplate": "#8CA3C3",
}

THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="st-"], [data-testid="stAppViewContainer"] {
  font-family: 'Inter', -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
}
[data-testid="stAppViewContainer"] {
  background: linear-gradient(160deg, #0B1220 0%, #0A1220 40%, #0D1428 100%);
  color: #E5E7EB;
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] {
  background: #0D1526;
  border-right: 1px solid rgba(148,163,184,0.10);
}
[data-testid="stSidebarNav"], [data-testid="stSidebarContent"] { background: transparent; }
.block-container { padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1500px; }

h1, h2, h3 { color: #F1F5F9; letter-spacing: -0.015em; font-weight: 700; }
h1 { font-size: 1.7rem; }
h2 { font-size: 1.25rem; }
p, li { color: #D3DCEA; }

/* Brand header in sidebar */
.vt-brand { color:#F1F5F9; font-size: 1.35rem; font-weight: 800; letter-spacing: 0.08em; margin: 0 0 2px 0; }
.vt-brand em { color:#38BDF8; font-style: normal; }
.vt-tagline { color:#8CA3C3; font-size: 0.72rem; letter-spacing: 0.18em; text-transform: uppercase; margin-bottom: 1rem; }

/* Section header */
.vt-section { border-bottom:1px solid rgba(148,163,184,0.12); padding-bottom:0.55rem; margin-bottom:1.1rem; }
.vt-section h1 { margin:0; }
.vt-section p { color:#8CA3C3; margin:0.25rem 0 0 0; font-size:0.9rem; }

/* KPI cards */
.vt-kpi {
  background: linear-gradient(180deg, rgba(23,37,66,0.55), rgba(13,23,46,0.85));
  border: 1px solid rgba(148,163,184,0.16);
  border-radius: 12px;
  padding: 14px 16px 12px 16px;
  height: 100%;
}
.vt-kpi .k-label { color:#8CA3C3; font-size:0.72rem; letter-spacing:0.12em; text-transform:uppercase; }
.vt-kpi .k-value { color:#F1F5F9; font-size:1.5rem; font-weight:700; margin-top:4px; }
.vt-kpi .k-sub { color:#B6C6DE; font-size:0.8rem; margin-top:4px; }
.vt-kpi .k-sub.accept { color:#34D399; }
.vt-kpi .k-sub.reject { color:#F87171; }
.vt-kpi .k-sub.review { color:#FBBF24; }
.vt-kpi .kbar { height:3px; border-radius:3px; margin-top:10px; }
@keyframes vtFill { from { width:0 } }
.vt-kpi .kbar span { display:block; height:3px; border-radius:3px; animation: vtFill 0.8s ease; }

/* Decision banner */
.vt-decision {
  border-radius: 14px;
  padding: 20px 22px;
  border: 1px solid;
  margin: 8px 0 18px 0;
  background: linear-gradient(135deg, rgba(23,37,66,0.55), rgba(13,23,46,0.9));
}
.vt-decision.accept { border-color: rgba(52,211,153,0.45); }
.vt-decision.reject { border-color: rgba(248,113,113,0.5); }
.vt-decision.review { border-color: rgba(251,191,36,0.5); }
.vt-decision .d-verdict { font-size:1.5rem; font-weight:800; letter-spacing:0.02em; }
.vt-decision .d-reason { color:#D3DCEA; margin-top:10px; line-height:1.55; }
.vt-decision.accept .d-verdict { color:#34D399; }
.vt-decision.reject .d-verdict { color:#F87171; }
.vt-decision.review .d-verdict { color:#FBBF24; }

/* Small stat chips */
.vt-chip {
  display:inline-block; border:1px solid rgba(56,189,248,0.35);
  background: rgba(56,189,248,0.08); color:#BDE5FF;
  border-radius:999px; padding:2px 10px; font-size:0.72rem; margin-right:6px;
}

/* Email preview panel */
.vt-email {
  background: rgba(11,18,32,0.7); border:1px solid rgba(148,163,184,0.25);
  border-radius:12px; padding:14px 16px; margin:6px 0 2px;
}
.vt-email-row { display:flex; gap:10px; padding:2px 0; font-size:0.86rem; color:#E5E7EB; }
.vt-email-key { flex:0 0 110px; color:#8CA3C3; font-weight:600; letter-spacing:0.06em; text-transform:uppercase; font-size:0.72rem; padding-top:3px; }
.vt-email-body {
  margin-top:10px; padding:10px 12px; border-radius:8px;
  background: rgba(2,6,15,0.55); border:1px solid rgba(148,163,184,0.18);
  color:#DBE4F0; font-family:"JetBrains Mono",Consolas,monospace; font-size:0.8rem;
  white-space:pre-wrap; word-break:break-word; line-height:1.5;
}

/* Inline generated report document */
.vt-report {
  background: rgba(11,18,32,0.75); border:1px solid rgba(56,189,248,0.28);
  border-radius:14px; padding:20px 22px; margin:8px 0 4px;
}
.vt-report-head { border-bottom:1px solid rgba(148,163,184,0.25); padding-bottom:12px; margin-bottom:6px; }
.vt-report-head .vr-brand { font-size:1.15rem; font-weight:800; letter-spacing:0.08em; color:#38BDF8; }
.vt-report-head .vr-brand em { color:#34D399; font-style:normal; }
.vt-report-head .vr-title { font-size:1.5rem; font-weight:700; color:#F1F5F9; margin-top:6px; }
.vt-report-head .vr-meta { color:#8CA3C3; font-size:0.78rem; margin-top:4px; }
.vt-report-sec {
  color:#7DD3FC; font-weight:700; letter-spacing:0.05em; text-transform:uppercase;
  font-size:0.78rem; margin:18px 0 8px; padding-bottom:4px; border-bottom:1px solid rgba(56,189,248,0.2);
}
.vt-badge {
  display:inline-block; border-radius:999px; padding:1px 10px; font-size:0.68rem;
  font-weight:700; letter-spacing:0.06em;
}
.vt-badge.accept { background:rgba(52,211,153,0.14); color:#34D399; border:1px solid rgba(52,211,153,0.4); }
.vt-badge.reject { background:rgba(248,113,113,0.14); color:#F87171; border:1px solid rgba(248,113,113,0.45); }
.vt-badge.review { background:rgba(251,191,36,0.14); color:#FBBF24; border:1px solid rgba(251,191,36,0.4); }
.vt-report-note { color:#D3DCEA; font-size:0.86rem; line-height:1.6; margin-top:8px; }
.vt-report-foot { color:#8CA3C3; font-size:0.75rem; margin-top:18px; border-top:1px solid rgba(148,163,184,0.2); padding-top:10px; }
.vt-tbl-wrap { overflow-x:auto; margin:6px 0 4px; }
table.vt-tbl { width:100%; border-collapse:collapse; font-size:0.78rem; color:#E2E8F0; }
table.vt-tbl th {
  background:rgba(56,189,248,0.1); color:#7DD3FC; text-align:left;
  padding:6px 10px; border-bottom:1px solid rgba(56,189,248,0.3); font-weight:600;
}
table.vt-tbl td { padding:5px 10px; border-bottom:1px solid rgba(148,163,184,0.12); color:#D3DCEA; }
table.vt-tbl tr:hover td { background:rgba(56,189,248,0.05); }
table.vt-tbl td.r { text-align:right; font-family:"JetBrains Mono",Consolas,monospace; }
table.vt-tbl td.c { text-align:center; }

/* Sidebar nav radio menu rows */
[data-testid="stSidebar"] div[role="radiogroup"] label {
  width: 100%;
  padding: 7px 10px;
  border-radius: 8px;
  margin-bottom: 2px;
  font-size: 0.88rem;
}
[data-testid="stSidebar"] div[role="radiogroup"] label:hover { background: rgba(56,189,248,0.07); }
[data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"],
[data-testid="stSidebar"] div[role="radiogroup"]:has(input:checked) label {
  background: linear-gradient(90deg, rgba(56,189,248,0.16), rgba(56,189,248,0.02));
  border: 1px solid rgba(56,189,248,0.28);
}
[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child { display:none; }

/* Expanders */
[data-testid="stExpander"] { background: rgba(16,26,50,0.5); border:1px solid rgba(148,163,184,0.12); border-radius:10px; }
[data-testid="stExpander"] details { background: transparent; }

/* Dataframes */
[data-testid="stDataFrame"] { border-radius:10px; overflow:hidden; }

/* Anti-white enforcement: every surface stays the dark navy theme */
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stSidebar"],
[data-testid="stHeader"] { background-color:#0B1220 !important; }
[data-testid="stSidebar"] { background-color:#0A1020 !important; }
[data-testid="main"] .block-container { max-width:1400px; padding-top:1.2rem; }

/* Inputs: dark boxes, no white fields */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stDateInput"] input,
[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
[data-testid="stMultiselect"] div[data-baseweb="select"] > div {
  background-color:#0E1626 !important;
  color:#E5E7EB !important;
  border-color:rgba(148,163,184,0.25) !important;
}
[data-testid="stTextInput"] input::placeholder,
[data-testid="stTextArea"] textarea::placeholder { color:#5A6E8C !important; }

/* Dropdown popups and option lists: dark, never white */
[data-baseweb="popover"],
div[data-testid="stPopover"],
[data-baseweb="popover"] div[role="listbox"],
[data-baseweb="popover"] [role="option"],
div[role="listbox"] { background-color:#131C2E !important; color:#E5E7EB !important; }
[data-baseweb="popover"] [role="option"]:hover,
div[role="listbox"] [role="option"]:hover { background-color:#1E2A45 !important; }

/* Hide the down-arrow chevrons everywhere (select / multiselect / baseweb) */
[data-testid="stSelectbox"] [data-testid="stIconMaterial"],
[data-testid="stMultiselect"] [data-testid="stIconMaterial"],
div[data-baseweb="select"] [data-testid="stIconMaterial"],
div[data-baseweb="select"] svg { display:none !important; }

/* Hide the up/down stepper arrows on number inputs */
[data-testid="stNumberInput"] button,
[data-testid="stNumberInput"] svg { display:none !important; }
[data-testid="stNumberInput"] input { text-align:right; }

/* File upload (Upload Case Data): dark theme, no arrows */
[data-testid="stFileUploaderDropzone"] {
  background-color:#0E1626 !important;
  border:1px dashed rgba(56,189,248,0.4) !important;
  color:#E5E7EB !important;
}
[data-testid="stFileUploaderDropzone"] svg { display:none !important; }
[data-testid="stFileUploaderDropzone"] button,
[data-testid="stFileUploaderDropzone"] [data-testid="stFileUploaderBrowseFile" i],
section[data-testid="stFileUploader"] button {
  background-color:#1E2A45 !important;
  color:#E5E7EB !important;
}
[data-testid="stFileUploaderDropzone"] [data-testid="stFileUploaderFile"] { border-color:rgba(148,163,184,0.25); }

/* Expanders: hide the arrow chevrons in the title rows, keep the boxes clean */
[data-testid="stExpander"] summary svg,
[data-testid="stExpander"] [data-testid="stExpanderIcon"],
[data-testid="stExpander"] [data-testid="stExpander"] summary > button svg { display:none !important; }

/* Buttons: dark, readable text inside light/filled buttons */
[data-testid="stButton"] button[kind="primary"],
[data-testid="stFormSubmitButton"] button[kind="primary"],
button[kind="primary"][data-testid="baseButton-primary"],
[data-testid="stDownloadButton"] button[kind="primary"] {
  color:#0B1220 !important; font-weight:700;
}
[data-testid="stButton"] button[kind="primary"]:hover,
[data-testid="stFormSubmitButton"] button[kind="primary"]:hover {
  color:#0B1220 !important;
}

/* Segmented control (Project Type): full dark theme */
[data-testid="stSegmentedControl"] [aria-checked="true"],
[data-testid="stSegmentedControl"] [data-checked="true"] {
  background: rgba(56,189,248,0.16) !important;
  color:#7DD3FC !important;
  border:1px solid rgba(56,189,248,0.4) !important;
}
[data-testid="stSegmentedControl"] [aria-checked="true"] *,
[data-testid="stSegmentedControl"] [data-checked="true"] * {
  color:#7DD3FC !important;
}
[data-testid="stSegmentedControl"] [aria-checked="false"],
[data-testid="stSegmentedControl"] [data-checked="false"] {
  color:#E5E7EB !important;
}

/* Dividers, captions, info */
hr { border-color: rgba(148,163,184,0.12); }
[data-testid="stCaptionContainer"] { color:#7E93B6; }
</style>
"""

_INJECTED = False


def inject_theme() -> None:
    global _INJECTED
    if _INJECTED:
        return
    st.markdown(THEME_CSS, unsafe_allow_html=True)
    _INJECTED = True


# ---------------------------------------------------------------------------
# Shared UI helpers
# ---------------------------------------------------------------------------

def fmt_money(v: float | None, ccy: str = "USD") -> str:
    if v is None or not np.isfinite(v):
        return "N/A"
    sym = f"{_CCY.get(ccy, ccy)} "
    return f"{sym}{v:,.0f}" if v >= 0 else f"({sym}{abs(v):,.0f})"


def fmt_pct(v: float | None) -> str:
    if v is None or not np.isfinite(v):
        return "N/A"
    return f"{v:.2f}%"


def fmt_num(v: float | None, digits: int = 2) -> str:
    if v is None or not np.isfinite(v):
        return "N/A"
    return f"{v:,.{digits}f}"


def status_tone(status: str) -> str:
    return {"ACCEPT": "accept", "REJECT": "reject", "REVIEW": "review"}.get(status, "review")


def section_header(title: str, subtitle: str | None = None):
    sub = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(f'<div class="vt-section"><h1>{title}</h1>{sub}</div>', unsafe_allow_html=True)


def kpi_row(items: list[tuple[str, str, str]]):
    """items: (label, value, sub) rendered as a responsive KPI strip."""
    cols = st.columns(len(items))
    for col, (label, value, sub) in zip(cols, items):
        col.markdown(
            f'<div class="vt-kpi"><div class="k-label">{label}</div>'
            f'<div class="k-value">{value}</div><div class="k-sub">{sub}</div></div>',
            unsafe_allow_html=True,
        )


def decision_banner(final: dict[str, str]):
    tone = status_tone(final["decision"])
    verdict = {
        "ACCEPT": "ACCEPT — PROCEED WITH INVESTMENT",
        "REJECT": "REJECT — DO NOT PROCEED",
        "REVIEW": "REVIEW — FURTHER ANALYSIS REQUIRED",
    }[final["decision"]]
    st.markdown(
        f'<div class="vt-decision {tone}"><div class="d-verdict">{verdict}</div>'
        f'<div class="d-reason">{final["reason"]}</div></div>',
        unsafe_allow_html=True,
    )


def empty_state(title: str, hint: str):
    st.markdown(
        f'<div class="vt-decision review"><div class="d-verdict">{title}</div>'
        f'<div class="d-reason">{hint}</div></div>',
        unsafe_allow_html=True,
    )


def plotly_dark(fig: go.Figure, title: str, height: int = 400) -> go.Figure:
    fig.update_layout(
        template="plotly_dark",
        title=dict(text=title, font=dict(color="#F1F5F9", size=14)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(12,20,42,0.55)",
        font=dict(family="Inter, sans-serif", color="#D3DCEA", size=11),
        height=height,
        hovermode="x unified",
        margin=dict(l=40, r=20, t=56, b=40),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(gridcolor="rgba(148,163,184,0.14)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(148,163,184,0.14)", zeroline=False)
    return fig


def data_colored(df: pd.DataFrame) -> pd.DataFrame:
    """Return a display copy with float formatting pleasant for dark UI."""
    out = df.copy()
    for col in out.columns:
        s = out[col]
        if pd.api.types.is_float_dtype(s):
            out[col] = s.map(lambda v: f"{v:,.2f}" if pd.notna(v) else "")
    return out


def get_state() -> dict[str, Any]:
    return st.session_state.setdefault("vtx", {})


# ---------------------------------------------------------------------------
# Engine wiring
# ---------------------------------------------------------------------------

def run_case(inputs: ProjectInputs) -> dict[str, Any]:
    with st.spinner("Running the full financial analysis..."):
        results = run_analysis(inputs)
        risk_results = assess_risks(results)
        scenarios = build_scenarios(results)
        sens_df, sens_summary = run_sensitivity(inputs, results)
        final = rg.decision_final(results, risk_results)
    state = get_state()
    state.update(
        {
            "inputs": inputs,
            "results": results,
            "risk_results": risk_results,
            "scenarios": scenarios,
            "sens_df": sens_df,
            "sens_summary": sens_summary,
            "final": final,
            "project_type": st.session_state.get("vtx_project_type", "New Project"),
        }
    )
    return state


def risk_score(risk_results: dict[str, Any]) -> int:
    scores = [r.score for r in risk_results.get("risks", [])]
    return max(scores) if scores else 1


def risk_label(score: int) -> str:
    return {1: "LOW", 2: "MODERATE", 3: "HIGH", 4: "VERY HIGH"}.get(score, "MODERATE")


# ---------------------------------------------------------------------------
# Sidebar: brand, navigation, case inputs
# ---------------------------------------------------------------------------

def render_sidebar() -> str:
    with st.sidebar:
        st.markdown(
            '<div class="vt-brand">Integrated Investment Decision Agent<em>.</em></div>'
            '<div class="vt-tagline">Capital Project Evaluation & Investment Decisions</div>',
            unsafe_allow_html=True,
        )
        section = st.radio("Navigate", NAV_SECTIONS, key="nav_section", label_visibility="collapsed")
        st.markdown("---")

        state = get_state()
        if state.get("results") is not None:
            st.caption(
                f"Active case: **{state['inputs'].project_name}** — "
                f"{state['final']['decision']}"
            )
            if st.button("Clear case", key="clear_case"):
                for key in [
                    "inputs", "results", "risk_results", "scenarios",
                    "sens_df", "sens_summary", "final", "project_type",
                ]:
                    st.session_state.get("vtx", {}).pop(key, None)
                st.rerun()

        with st.expander("Investment Inputs", expanded=True):
            ptype = st.segmented_control(
                "Project Type",
                PROJECT_TYPES,
                default=PROJECT_TYPES[0],
                key="vtx_ptype_buttons",
                selection_mode="single",
                help="Tap a button to choose the case type.",
            )
            ptype = ptype if ptype in PROJECT_TYPES else PROJECT_TYPES[0]
            st.caption(PROJECT_TYPE_DESCRIPTIONS.get(ptype, PROJECT_TYPE_DESCRIPTIONS[PROJECT_TYPES[0]]))
            _sidebar_input_form(ptype)

        with st.expander("Upload Case Data (CSV / Excel)", expanded=False):
            _sidebar_uploader(ptype)
    return section


def _sidebar_input_form(project_type: str) -> None:
    with st.form("valtexa_input_form"):
        c1, c2 = st.columns(2)
        project_name = c1.text_input("Project name", value=project_type)
        project_life = c2.number_input("Project life (years)", min_value=1.0, max_value=100.0, value=10.0, step=1.0)
        initial_investment = c1.number_input("Initial investment", min_value=0.0, value=1_000_000.0, step=50_000.0, format="%.0f")
        annual_revenues = c2.number_input("Annual revenues", min_value=0.0, value=350_000.0, step=10_000.0, format="%.0f")
        operating_costs = c1.number_input("Operating costs", min_value=0.0, value=80_000.0, step=10_000.0, format="%.0f")
        tax_rate = c2.number_input("Tax rate (%)", min_value=0.0, max_value=100.0, value=25.0, step=0.5)
        discount_rate = c1.number_input("WACC / Discount rate (%)", min_value=0.01, max_value=100.0, value=10.0, step=0.5)
        financing_rate = c2.number_input("Financing rate (%)", min_value=0.01, max_value=100.0, value=10.0, step=0.5)
        reinvestment_rate = c1.number_input("Reinvestment rate (%)", min_value=0.01, max_value=100.0, value=10.0, step=0.5)
        working_capital = c2.number_input("Working capital", min_value=0.0, value=0.0, step=10_000.0, format="%.0f")
        terminal_value = c1.number_input("Terminal value", min_value=0.0, value=0.0, step=50_000.0, format="%.0f")
        rev_growth = c2.number_input("Revenue growth (%/yr)", value=0.0, step=0.5)
        cost_growth = c1.number_input("Cost growth (%/yr)", value=0.0, step=0.5)
        terminal_growth = c2.number_input("Terminal growth (%/yr)", value=0.0, step=0.25)
        description = st.text_area(
            "Description (leave blank to use the Project Type description)",
            height=64,
            placeholder=PROJECT_TYPE_DESCRIPTIONS[project_type][:120] + "…",
        )
        submitted = st.form_submit_button("Run Analysis", type="primary")

    if submitted:
        validation = dv.validate_project_inputs(
            {
                "project_name": project_name,
                "project_life": project_life,
                "initial_investment": initial_investment,
                "annual_revenues": annual_revenues,
                "operating_costs": operating_costs,
                "tax_rate": tax_rate,
                "discount_rate": discount_rate,
                "working_capital": working_capital,
                "terminal_value": terminal_value,
                "growth_rate": rev_growth,
            }
        )
        if not validation.is_valid:
            st.error("Validation failed:" + "\n".join(f"\n- {e}" for e in validation.errors))
            return
        inputs = ProjectInputs(
            project_name=project_name,
            project_description=(description.strip() or PROJECT_TYPE_DESCRIPTIONS[project_type]),
            initial_investment=float(initial_investment),
            project_life=float(project_life),
            annual_revenues=float(annual_revenues),
            revenue_growth_rate=float(rev_growth),
            operating_costs=float(operating_costs),
            cost_growth_rate=float(cost_growth),
            tax_rate=float(tax_rate),
            working_capital=float(working_capital),
            terminal_value=float(terminal_value),
            terminal_growth_rate=float(terminal_growth),
            discount_rate=float(discount_rate),
            financing_rate=float(financing_rate),
            reinvestment_rate=float(reinvestment_rate),
        )
        run_case(inputs)
        st.success("Analysis complete. Open the Executive Dashboard.")


def _sidebar_uploader(project_type: str) -> None:
    f = st.file_uploader(
        f"CSV / Excel for '{project_type}'",
        type=["csv", "xlsx", "xls"],
        key=f"valtexa_upload_{project_type.replace('/', '_')}",
    )
    if f is None:
        return
    try:
        df = pd.read_csv(f) if f.name.lower().endswith(".csv") else pd.read_excel(f)
        vres, data = dv.validate_csv_upload(df)
        if not vres.is_valid:
            st.error("Upload validation failed:" + "\n".join(f"\n- {e}" for e in vres.errors))
            return
        for w in vres.warnings:
            st.warning(w)
        if not data:
            st.info("No usable project row found in the file.")
            return
        inputs = ProjectInputs(
            project_name=str(data.get("project_name") or f"{project_type} (uploaded)"),
            project_description=str(
                data.get("project_description") or f"{project_type} — from uploaded file {f.name}."
            ),
            initial_investment=float(data["initial_investment"]),
            project_life=float(data["project_life"]),
            annual_revenues=float(data["annual_revenues"]),
            operating_costs=float(data["operating_costs"]),
            tax_rate=float(data["tax_rate"]),
            working_capital=float(data.get("working_capital", 0)),
            terminal_value=float(data.get("terminal_value", 0)),
            discount_rate=float(data["discount_rate"]),
            financing_rate=float(data.get("financing_rate", data["discount_rate"])),
            reinvestment_rate=float(data.get("reinvestment_rate", data["discount_rate"])),
            revenue_growth_rate=float(data.get("growth_rate", 0)),
        )
        run_case(inputs)
        st.success(f"Uploaded {f.name} — case loaded and analysed.")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Failed to parse file: {exc}")


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

def build_cashflow_chart(results: dict[str, Any]) -> go.Figure:
    d = results["chart_data"]
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=d["years"], y=d["net_cash_flows"],
            name="Net cash flow (incl. terminal value)",
            marker_color="#1E3A8A",
            marker_line_color="#38BDF8", marker_line_width=0.6,
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=d["years"], y=d["cumulative_cash_flows"],
            name="Cumulative cash flow", mode="lines+markers",
            line=dict(color="#FBBF24", width=2.6),
        ),
        secondary_y=True,
    )
    fig.add_hline(y=0, line_dash="dash", line_color="rgba(148,163,184,0.4)")
    return plotly_dark(fig, "Annual & cumulative cash flows", 400)


def build_pv_chart(results: dict[str, Any]) -> go.Figure:
    d = results["chart_data"]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=d["years"], y=d["present_values"], name="Present value", marker_color="#38BDF8", opacity=0.85))
    fig.add_trace(
        go.Scatter(x=d["years"], y=d["cumulative_present_values"], name="Cumulative PV",
                   mode="lines+markers", line=dict(color="#FBBF24", width=2.4))
    )
    fig.add_hline(y=0, line_dash="dash", line_color="rgba(148,163,184,0.4)")
    return plotly_dark(fig, "Present values of cash flows (WACC-discounted)", 360)


def build_scenario_chart(scenarios: dict[str, Any]) -> go.Figure:
    labels = [s["label"] for s in scenarios.values()]
    npvs = [s["summary"]["npv"] for s in scenarios.values()]
    colors = ["#34D399", "#38BDF8", "#F87171"]
    fig = go.Figure(
        go.Bar(
            x=labels, y=npvs, marker_color=colors,
            text=[fmt_money(v) for v in npvs], textposition="outside",
        )
    )
    fig.add_hline(y=0, line_dash="dash", line_color="rgba(148,163,184,0.4)")
    return plotly_dark(fig, "Scenario NPV comparison", 340)


def build_sensitivity_chart(sens_df: pd.DataFrame) -> go.Figure:
    df = sens_df.sort_values("Spread")
    fig = go.Figure(
        go.Bar(
            y=df["Variable"], x=df["Spread"], orientation="h",
            marker_color="#38BDF8", opacity=0.9,
            text=[fmt_money(v) for v in df["Spread"]], textposition="outside",
        )
    )
    return plotly_dark(fig, "NPV sensitivity by variable (30% swing)", 380)


def build_risk_chart(risk_results: dict[str, Any]) -> go.Figure:
    risks = risk_results["risks"]
    names = [r.risk for r in risks]
    scores = [r.score for r in risks]
    colors = {1: "#34D399", 2: "#FBBF24", 3: "#F59E0B", 4: "#F87171"}
    fig = go.Figure(go.Bar(x=scores, y=names, orientation="h", marker_color=[colors[s] for s in scores]))
    fig.update_layout(xaxis=dict(range=[0, 4.6], tickmode="array", tickvals=[1, 2, 3, 4], ticktext=["Low", "Moderate", "High", "Very High"]))
    return plotly_dark(fig, "Risk severity profile", 360)


def build_dcf_val_chart(results: dict[str, Any], metrics: dict[str, Any]) -> go.Figure:
    fig = go.Figure(
        go.Waterfall(
            name="Value creation",
            orientation="v",
            measure=["absolute", "relative", "relative"],
            x=["PV of cash flows", "Initial investment", "Net present value"],
            y=[
                metrics["total_project_value"],
                -metrics["initial_investment"],
                metrics["npv"],
            ],
            connector={"line": {"color": "rgba(148,163,184,0.5)"}},
            increasing={"marker": {"color": "#34D399"}},
            decreasing={"marker": {"color": "#F87171"}},
            totals={"marker": {"color": "#38BDF8"}},
        )
    )
    return plotly_dark(fig, "Value creation bridge (DCF value vs investment, net of NPV)", 360)


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

def render_executive_dashboard():
    section_header(
        "Executive Dashboard",
        "Decision-first view: the recommendation, the value it creates, and the evidence, "
        "before everything else. Drill down through the left navigation.",
    )
    state = get_state()
    results = state.get("results")
    if results is None:
        empty_state(
            "No case analysed yet",
            "Enter the project's assumptions in the sidebar (Investment Inputs) and press "
            "Run Analysis, or upload a CSV/Excel case. The dashboard will then show the "
            "recommendation, KPIs, cash-flow analysis and risk."
        )
        return

    metrics = results["metrics"]
    final = state["final"]
    risk_results = state["risk_results"]
    scenarios = state["scenarios"]
    rscore = risk_score(risk_results)

    kpi_row(
        [
            ("Net Present Value", fmt_money(metrics["npv"]), f"WACC {fmt_pct(metrics['wacc'] if 'wacc' in metrics else metrics['discount_rate'])}"),
            ("Internal Rate of Return", fmt_pct(metrics["irr"]), f"MIRR {fmt_pct(metrics['mirr'])}"),
            ("Return on Investment", fmt_pct(metrics["roi"]), f"Payback {fmt_num(metrics['payback'])} yrs"),
            ("Risk Score", f"{risk_label(rscore)}",
             f"{rscore}/4 · {[r.risk for r in risk_results['risks'] if r.score == rscore][0] if risk_results['risks'] else '—'}"),
            ("Recommended Project", state["inputs"].project_name, final["decision"]),
        ]
    )

    st.markdown("#### Investment Decision")
    decision_banner(final)
    st.markdown(f"**Recommendation.** {final['recommendation']}")

    st.markdown("#### Value & Cash-Flow Profile")
    chart_col, table_col = st.columns([3, 2])
    with chart_col:
        st.plotly_chart(build_cashflow_chart(results), width="stretch")
        st.plotly_chart(build_dcf_val_chart(results, metrics), width="stretch")
    with table_col:
        with st.expander("Cash flow table", expanded=True):
            st.dataframe(data_colored(results["cash_flow_table"]), width="stretch", height=300)
        with st.expander("DCF table", expanded=True):
            st.dataframe(data_colored(results["dcf_table"]), width="stretch", height=300)

    p1, p2 = st.columns(2)
    with p1:
        st.markdown("#### Scenario Analysis")
        for key in ["best", "base", "worst"]:
            s = scenarios[key]
            sm = s["summary"]
            st.markdown(
                f'<div class="vt-kpi" style="margin-bottom:8px"><div class="k-label">{s["label"]}</div>'
                f'<div class="k-value">{fmt_money(sm["npv"])}</div>'
                f'<div class="k-sub {status_tone(sm['decision'])}">{sm["decision"]}</div></div>',
                unsafe_allow_html=True,
            )
    with p2:
        st.markdown("#### FX & Multi-Currency Exposure")
        board = fx.build_board_frame(_fx_live())
        st.dataframe(board, width="stretch", height=220)
        st.caption(
            "Rates used to convert any multi-currency position. Overrides always win; "
            "stale stored rates are labelled."
        )

    st.markdown("#### Project Ranking")
    tp_result = st.session_state.get("tp_result")
    if tp_result is not None:
        rank = tp_result["ranking_df"]
        st.dataframe(
            rank[["Rank", "Project", "Name", "Composite Score", "Risk"]].head(6),
            width="stretch", height=200,
        )
        st.caption("Ranking from the Three-Project Comparison. Re-run that section to update.")
    else:
        st.info(
            "No cross-project ranking yet. Open Project Comparison to score Projects A, B and C "
            "(in USD / ZAR / ZiG) and rank them."
        )


def render_investment_cases():
    section_header(
        "Investment Cases",
        "The active case and its assumptions at a glance. Cases are the single source that every "
        "section and report is computed from.",
    )
    state = get_state()
    inputs = state.get("inputs")
    if inputs is None:
        empty_state("No case loaded", "Enter inputs in the sidebar or upload a file.")
        return

    st.markdown(f"#### Active case — {inputs.project_name}")
    st.markdown(
        f'<span class="vt-chip">{state.get("project_type", "Case")}</span>'
        f'<span class="vt-chip">Life {inputs.project_life:.0f} yrs</span>'
        f'<span class="vt-chip">WACC {inputs.discount_rate:.2f}%</span>'
        f'<span class="vt-chip">Tax {inputs.tax_rate:.2f}%</span>',
        unsafe_allow_html=True,
    )
    st.markdown(inputs.project_description)

    assumption_rows = {
        "Project life (years)": f"{inputs.project_life:.0f}",
        "Initial investment": fmt_money(inputs.initial_investment),
        "Annual revenues": fmt_money(inputs.annual_revenues),
        "Revenue growth (%/yr)": fmt_num(inputs.revenue_growth_rate),
        "Operating costs": fmt_money(inputs.operating_costs),
        "Cost growth (%/yr)": fmt_num(inputs.cost_growth_rate),
        "Tax rate": fmt_pct(inputs.tax_rate),
        "WACC / discount rate": fmt_pct(inputs.discount_rate),
        "Financing rate": fmt_pct(inputs.financing_rate),
        "Reinvestment rate": fmt_pct(inputs.reinvestment_rate),
        "Working capital": fmt_money(inputs.working_capital),
        "Terminal value": fmt_money(inputs.terminal_value),
        "Terminal growth (%/yr)": fmt_num(inputs.terminal_growth_rate),
    }
    st.dataframe(
        pd.DataFrame({"Assumption": list(assumption_rows), "Value": list(assumption_rows.values())}),
        width="stretch", height=440,
    )


def render_capital_budgeting():
    section_header(
        "Capital Budgeting",
        "Cash-flow construction, payback and capital-efficiency thresholds.",
    )
    state = get_state()
    results = state.get("results")
    if results is None:
        empty_state("No case loaded", "Run an analysis from the sidebar first.")
        return
    metrics = results["metrics"]
    decisions = results["decisions"]

    kpi_row(
        [
            ("Payback period", f"{fmt_num(metrics['payback'])} yrs",
             f"vs life {metrics['project_life']:.0f} yrs — {decisions['payback']['status']}"),
            ("Profitability index", fmt_num(metrics["pi"], 3),
             f"{decisions['pi']['status']} — hurdle 1.00"),
            ("NPV", fmt_money(metrics["npv"]), decisions["npv"]["status"]),
            ("IRR vs WACC", f"{fmt_pct(metrics['irr'])} vs {fmt_pct(metrics['discount_rate'])}",
             decisions["irr"]["status"]),
        ]
    )
    st.plotly_chart(build_cashflow_chart(results), width="stretch")
    st.markdown(f"**Payback interpretation.** {decisions['payback']['reason']}")
    st.markdown(f"**PI interpretation.** {decisions['pi']['reason']}")
    with st.expander("Full cash-flow table", expanded=True):
        st.dataframe(data_colored(results["cash_flow_table"]), width="stretch")


def render_dcf_valuation():
    section_header(
        "DCF & Valuation",
        "Discounted cash-flow valuation of the case at the cost of capital.",
    )
    state = get_state()
    results = state.get("results")
    if results is None:
        empty_state("No case loaded", "Run an analysis from the sidebar first.")
        return
    metrics = results["metrics"]
    col1, col2 = st.columns(2)
    with col1:
        kpi_row(
            [
                ("Total project value (PV)", fmt_money(metrics["total_project_value"]),
                 f"Investment {fmt_money(metrics['initial_investment'])}"),
                ("PV of terminal value", fmt_money(metrics["pv_terminal"]), "Gordon / explicit terminal"),
                ("Net present value", fmt_money(metrics["npv"]), "Value minus investment"),
            ]
        )
    with col2:
        st.plotly_chart(build_dcf_val_chart(results, metrics), width="stretch")

    st.plotly_chart(build_pv_chart(results), width="stretch")
    with st.expander("DCF valuation table", expanded=True):
        st.dataframe(data_colored(results["dcf_table"]), width="stretch")
    st.info(
        "Method: each period's free cash flow is discounted at the WACC. Total project value is the "
        "present value of operating cash flows including terminal value; NPV subtracts the initial "
        "investment."
    )


def render_returns():
    section_header(
        "Returns",
        "Return measures: NPV, IRR, MIRR, ROI, holding-period and annualised returns.",
    )
    state = get_state()
    results = state.get("results")
    if results is None:
        empty_state("No case loaded", "Run an analysis from the sidebar first.")
        return
    metrics = results["metrics"]
    decisions = results["decisions"]

    kpi_row(
        [
            ("NPV", fmt_money(metrics["npv"]), decisions["npv"]["reason"]),
            ("IRR", fmt_pct(metrics["irr"]), decisions["irr"]["reason"]),
            ("MIRR", fmt_pct(metrics["mirr"]), decisions["mirr"]["reason"]),
            ("ROI", fmt_pct(metrics["roi"]),
             f"HPR {fmt_pct(metrics['holding_period_return'])} · annualised {fmt_pct(metrics['annualized_return'])}"),
        ]
    )
    st.markdown("### Thresholds & verdicts")
    for card in [
        ("NPV", metrics["npv"], decisions["npv"]),
        ("IRR", metrics["irr"], decisions["irr"]),
        ("MIRR", metrics["mirr"], decisions["mirr"]),
        ("ROI", metrics["roi"], decisions["roi"]),
        ("Profitability index", metrics["pi"], decisions["pi"]),
        ("Payback", metrics["payback"], decisions["payback"]),
    ]:
        tone = status_tone(card[2]["status"])
        st.markdown(
            f'<div class="vt-kpi" style="margin-bottom:8px"><div class="k-label">{card[0]} — {card[2]["status"]}</div>'
            f'<div class="k-value">{fmt_num(card[1])}</div>'
            f'<div class="k-sub">{card[2]["reason"]}</div></div>',
            unsafe_allow_html=True,
        )


def render_risk_analysis():
    section_header(
        "Risk Analysis",
        "Identified risk drivers, severities, mitigations and the overall risk verdict.",
    )
    state = get_state()
    risk_results = state.get("risk_results")
    if risk_results is None:
        empty_state("No case loaded", "Run an analysis from the sidebar first.")
        return
    rscore = risk_score(risk_results)
    kpi_row(
        [
            ("Overall risk", f"{risk_label(rscore)}", f"{rscore}/4 composite"),
            ("Risk drivers", str(len(risk_results["risks"])), "assessed"),
            ("Sensitivity lead", state.get("sens_summary", {}).get("most_sensitive", "—"), "most volatile variable"),
        ]
    )
    st.plotly_chart(build_risk_chart(risk_results), width="stretch")
    st.markdown(f"**Overall assessment.** {risk_results['overall_explanation']}")
    for r in risk_results["risks"]:
        st.markdown(
            f'<div class="vt-kpi" style="margin-bottom:8px"><div class="k-label">{r.risk} — {r.severity}</div>'
            f'<div class="k-sub">Impact: {r.impact}</div>'
            f'<div class="k-sub" style="margin-top:6px">{r.explanation}</div>'
            f'<div class="k-sub" style="color:#BDE5FF">Mitigation: {r.mitigation}</div></div>',
            unsafe_allow_html=True,
        )


def _fx_live() -> dict[str, fx.FxRate]:
    return st.session_state.setdefault("fx_ratemap", {})


def _funding_rates(ratemap: dict[str, fx.FxRate]) -> tuple[dict[str, float], bool]:
    """Units-per-USD rates {USD, ZIG, ZAR} for the fx_service funding engine.

    Returns (rates, all_live) where a missing ZiG/ZAR rate falls back to the
    documented reference value and `all_live` is False so the UI can warn.
    """
    def _per_usd(to_ccy: str) -> float | None:
        r = ratemap.get(f"USD/{to_ccy}")
        if r is not None and r.rate == r.rate and r.rate > 0:
            return float(r.rate)
        return None

    zig_live = _per_usd("ZWG")
    zar_live = _per_usd("ZAR")
    zig = zig_live if zig_live is not None else fx_service.DEFAULT_UNIT_PER_USD["ZIG"]
    zar = zar_live if zar_live is not None else fx_service.DEFAULT_UNIT_PER_USD["ZAR"]
    return {"USD": 1.0, "ZIG": zig, "ZAR": zar}, zig_live is not None and zar_live is not None


def _refresh_fx(fetch: bool = False) -> None:
    st.session_state.setdefault("fx_ratemap", {})
    st.session_state.setdefault("fx_last_fetch", 0.0)
    if fetch:
        _run_live_fetch()
    elif not st.session_state["fx_ratemap"]:
        st.session_state["fx_ratemap"] = fx.all_effective_rates()


def _run_live_fetch() -> None:
    """Fetch live market rates from the exchange-rate providers and persist them."""
    with st.spinner("Fetching live exchange rates..."):
        live = fx.fetch_live_rates()
    if live:
        fx.store_live_rates(live)
        st.session_state["fx_ratemap"] = live
        st.session_state["fx_last_fetch"] = time.time()
        st.success(f"Rates updated from {next(iter(live.values())).source}.")
    else:
        st.session_state["fx_ratemap"] = fx.all_effective_rates(_fx_live())
        st.warning(
            "Live rates unavailable (provider or network). Showing stored/override rates — "
            "stale values are labelled, never silently used."
        )


def _maybe_auto_fetch_fx() -> None:
    """Fetch live rates on open once per session (unless the user disabled it)."""
    if not bool(st.session_state.get("fx_auto", True)):
        return
    if st.session_state.get("fx_auto_done"):
        return
    st.session_state["fx_auto_done"] = True
    st.session_state["fx_requested"] = "refresh"


def render_fx_multicurrency():
    section_header(
        "FX & Multi-Currency",
        "USD / ZAR / ZiG across all six pairs. Live market rates are fetched automatically when "
        "the app opens; manual overrides always win and stored rates are labelled.",
    )
    st.checkbox(
        "Fetch live market rates on open",
        value=bool(st.session_state.get("fx_auto", True)),
        key="fx_auto",
    )
    _refresh_fx()

    c1, c2 = st.columns([2, 1])
    interval = c1.select_slider(
        "Auto-refresh",
        options=[0, 5, 10, 15, 30, 60],
        value=int(st.session_state.get("fx_interval", 0)),
        format_func=lambda v: "Off" if v == 0 else f"Every {v} minutes",
    )
    st.session_state["fx_interval"] = int(interval)
    if c2.button("Refresh Live Rates Now", type="primary"):
        st.session_state["fx_requested"] = "refresh"
        st.rerun()

    last = float(st.session_state.get("fx_last_fetch", 0.0))
    if interval > 0 and last > 0 and time.time() - last >= interval * 60:
        _refresh_fx(fetch=True)

    board = fx.build_board_frame(_fx_live())
    st.dataframe(board, width="stretch")
    st.caption(
        "LIVE — fresh from provider · MANUAL OVERRIDE — user-set, always wins · "
        "STORED — last fetched, still valid · STALE — older than 24h · UNAVAILABLE — no rate."
    )
    with st.expander("Manual rate overrides", expanded=False):
        pairs = [f"{a}/{b}" for a, b in fx.PAIRS]
        pair = st.radio(
            "Pair",
            pairs,
            horizontal=True,
            key="fx_ov_pair",
            label_visibility="collapsed",
        )
        rate = st.number_input(
            f"Manual rate for {pair}", min_value=0.0000001,
            value=float(st.session_state.get("fx_ov_val", 1.0)),
            step=0.01, format="%.6f", key="fx_ov_rate",
        )
        st.session_state["fx_ov_val"] = rate
        b1, b2 = st.columns(2)
        if b1.button("Set override"):
            try:
                fx.set_manual_override(pair, float(rate))
                _refresh_fx()
                st.success(f"Override stored for {pair}.")
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))
        if b2.button("Clear override"):
            fx.clear_manual_override(pair)
            _refresh_fx()
            st.success(f"Override cleared for {pair}.")
    with st.expander("Rate history (audit trail)", expanded=False):
        limit = st.slider("History rows", 5, 200, 40, 5)
        hist = fx.get_history(limit=min(limit, 200))
        if hist:
            st.dataframe(
                pd.DataFrame(hist).rename(
                    columns={"pair": "Pair", "rate": "Rate", "source": "Source",
                             "status": "Status", "ts": "Timestamp"}
                ),
                width="stretch",
            )
        else:
            st.info("No rate history yet. Fetch live rates to populate the audit trail.")

    with st.expander("How much to invest per currency & which funding currency is most profitable", expanded=True):
        state = get_state()
        inputs = state.get("inputs")
        invest_usd = float(inputs.initial_investment) if inputs is not None else 1_000_000.0
        if inputs is None:
            st.caption(
                "No active case loaded — using a default **USD 1,000,000** investment. "
                "Run an analysis from the sidebar to use the exact project outlay."
            )
        ratemap = _fx_live()
        rates, available = _funding_rates(ratemap)
        if not available:
            st.warning(
                "Live or override rates are missing for ZiG or ZAR. Reference rates are used "
                "below until you refresh live rates or set manual overrides above."
            )

        st.markdown("**Where your income is held** (people earning both ZiG and USD)")
        m1, m2, m3 = st.columns(3)
        usd_mix = m1.slider("USD (%)", 0, 100, 30, 5, key="fx_mix_usd")
        zig_mix = m2.slider("ZiG (%)", 0, 100, 70, 5, key="fx_mix_zig")
        zar_mix = m3.slider("ZAR (%)", 0, 100, 0, 5, key="fx_mix_zar")
        st.markdown("**Expected depreciation vs USD — model assumptions** (you override these)")
        d1, d2 = st.columns(2)
        zig_dep = d1.slider("ZiG annual depreciation (%)", 0.0, 90.0, 35.0, 5.0, key="fx_dep_zig")
        zar_dep = d2.slider("ZAR annual depreciation (%)", 0.0, 50.0, 8.0, 1.0, key="fx_dep_zar")

        funding = fx_service.funding_analysis(
            investment_usd=invest_usd,
            fx={"rates": rates},
            earn_mix={"USD": usd_mix, "ZIG": zig_mix, "ZAR": zar_mix},
            expected_depreciation={"USD": 0.0, "ZIG": zig_dep / 100.0, "ZAR": zar_dep / 100.0},
        )
        frame = funding["rows"].copy()
        frame["Currency"] = frame["Currency"].replace({"ZIG": "ZiG"})
        st.dataframe(data_colored(frame), width="stretch")
        st.markdown(
            f'<div class="vt-kpi"><div class="k-label">Most favourable funding/return currency: '
            f'{funding["best_currency"]}</div>'
            f'<div class="k-sub" style="margin-top:6px">{funding["recommendation"]}</div></div>',
            unsafe_allow_html=True,
        )

    with st.expander("Active case exposure converted to each currency", expanded=False):
        if inputs is None:
            st.info("No active case loaded. Run an analysis from the sidebar first.")
        else:
            fund_cols = {
                "initial_investment": "Initial investment",
                "annual_revenues": "Annual revenues",
                "operating_costs": "Operating costs",
                "working_capital": "Working capital",
                "terminal_value": "Terminal value",
            }
            expose = []
            for ccy in fx.CURRENCIES:
                row = {"Currency": _CCY[ccy]}
                for field, label in fund_cols.items():
                    val, _note = fx.convert_amount(getattr(inputs, field), "USD", ccy, ratemap)
                    row[label] = None if val is None else val
                expose.append(row)
            st.dataframe(
                pd.DataFrame(expose).set_index("Currency"),
                width="stretch",
            )
            st.caption(
                "Rates used come from the board above (live, override, stored or stale — as "
                "labelled). See Project Comparison for the full A/B/C case conversion."
            )


def render_scenario_analysis():
    section_header(
        "Scenario Analysis",
        "Best / Base / Worst case behaviour of the investment.",
    )
    state = get_state()
    scenarios = state.get("scenarios")
    if scenarios is None:
        empty_state("No case loaded", "Run an analysis from the sidebar first.")
        return
    st.plotly_chart(build_scenario_chart(scenarios), width="stretch")
    for key in ["best", "base", "worst"]:
        s = scenarios[key]
        sm = s["summary"]
        st.markdown(
            f'<div class="vt-kpi" style="margin-bottom:10px"><div class="k-label">{s["label"]}</div>'
            f'<div class="k-value">{fmt_money(sm["npv"])} · <span class="k-sub {status_tone(sm['decision'])}">{sm["decision"]}</span></div>'
            f'<div class="k-sub">IRR {fmt_pct(sm["irr"])} · MIRR {fmt_pct(sm["mirr"])} · ROI {fmt_pct(sm["roi"])} · '
            f'Payback {fmt_num(sm["payback"])} yrs · PI {fmt_num(sm["pi"])}</div>'
            f'<div class="k-sub" style="margin-top:6px">{sm["explanation"]}</div></div>',
            unsafe_allow_html=True,
        )


def render_sensitivity_analysis():
    section_header(
        "Sensitivity Analysis",
        "How much the NPV moves when each key assumption swings by ±30%.",
    )
    state = get_state()
    sens_df = state.get("sens_df")
    sens_summary = state.get("sens_summary")
    if sens_df is None:
        empty_state("No case loaded", "Run an analysis from the sidebar first.")
        return
    st.plotly_chart(build_sensitivity_chart(sens_df), width="stretch")
    st.info(sensitivity_interpretation(sens_summary))
    st.markdown(
        f"**Most sensitive:** {sens_summary['most_sensitive']} · "
        f"**Least sensitive:** {sens_summary['least_sensitive']}"
    )
    st.dataframe(data_colored(sens_df), width="stretch")


def render_project_comparison():
    section_header(
        "Project Comparison",
        "Rank Projects A, B and C across USD / ZAR / ZiG, optimise capital allocation "
        "(divisible or indivisible), and produce a board-ready recommendation.",
    )
    with st.expander("Comparison configuration", expanded=True):
        c = st.columns(3)
        comparison_currency = c[0].selectbox(
            "Comparison currency", fx.CURRENCIES, index=0,
            format_func=lambda x: _CCY[x], key="tp_cmpccy",
        )
        investment_type = c[1].selectbox(
            "Investment type", ["Divisible", "Indivisible"], key="tp_invtype",
        )
        budget = c[2].number_input(
            f"Investment budget ({comparison_currency})", min_value=0.0, value=0.0,
            step=100_000.0, format="%.0f", key="tp_budget",
        )
        methods_sel = st.multiselect(
            "Financial methods for ranking",
            tp.METHODS,
            default=["NPV", "IRR", "MIRR", "ROI", "PI", "Payback"],
            key="tp_methods",
        )
        include_risk = st.checkbox("Include risk & scenario analysis in the ranking", value=True, key="tp_risk")

    st.markdown("#### Project inputs (each in its own currency)")
    _comparison_input_panel("A")
    with st.expander("Project B — Inputs", expanded=False):
        _comparison_input_panel("B")
    with st.expander("Project C — Inputs", expanded=False):
        _comparison_input_panel("C")

    if st.button("Run Comparison", type="primary"):
        if not methods_sel:
            st.error("Select at least one financial method.")
            return
        ratemap = fx.all_effective_rates(_fx_live())
        specs = {
            letter: _tp_spec_from_widgets(letter)
            for letter in ("A", "B", "C")
        }
        config = tp.ComparisonConfig(
            projects=specs,
            comparison_currency=comparison_currency,
            methods=methods_sel,
            include_risk_and_scenarios=include_risk,
            investment_type=investment_type,
            budget=float(budget),
            ratemap=ratemap,
        )
        missing = _tp_ratemap_ready(config)
        if missing:
            st.error(
                "Exchange rates unavailable for: " + ", ".join(missing)
                + ". Set FX overrides or refresh rates first."
            )
            return
        with st.spinner("Running the comparison and optimisation..."):
            out = tp.compare_projects(config)
        st.session_state["tp_result"] = out
        st.session_state["tp_result_ccy"] = _CCY[comparison_currency]
        st.success("Comparison complete.")

    result = st.session_state.get("tp_result")
    if result is not None:
        _render_tp_result(result, st.session_state.get("tp_result_ccy", "USD"))


def _comparison_input_panel(letter: str):
    k = letter.lower()
    name = st.text_input(f"Project {letter} — name", f"Project {letter}", key=f"{k}_name")
    c1, c2 = st.columns(2)
    with c1:
        ccy = st.selectbox("Project currency", fx.CURRENCIES, format_func=lambda c: _CCY[c], key=f"{k}_ccy")
        st.number_input("Initial investment", min_value=0.0, value=1_000_000.0, step=50_000.0, format="%.0f", key=f"{k}_inv")
        st.number_input("Annual revenues", min_value=0.0, value=350_000.0, step=10_000.0, format="%.0f", key=f"{k}_rev")
        st.number_input("Operating costs", min_value=0.0, value=80_000.0, step=10_000.0, format="%.0f", key=f"{k}_cost")
        st.number_input("Tax rate (%)", min_value=0.0, max_value=100.0, value=25.0, step=0.5, key=f"{k}_tax")
        st.number_input("Discount rate / WACC (%)", min_value=0.01, max_value=100.0, value=10.0, step=0.5, key=f"{k}_disc")
    with c2:
        st.number_input("Project life (years)", min_value=1.0, max_value=100.0, value=10.0, step=1.0, key=f"{k}_life")
        st.number_input("Financing rate (%)", min_value=0.01, max_value=100.0, value=10.0, step=0.5, key=f"{k}_fin")
        st.number_input("Reinvestment rate (%)", min_value=0.01, max_value=100.0, value=10.0, step=0.5, key=f"{k}_rein")
        st.number_input("Working capital", min_value=0.0, value=0.0, step=10_000.0, format="%.0f", key=f"{k}_wc")
        st.number_input("Terminal value", min_value=0.0, value=0.0, step=50_000.0, format="%.0f", key=f"{k}_tv")
        st.number_input("Revenue growth (%/yr)", value=0.0, step=0.5, key=f"{k}_revg")
    st.text_area(f"Project {letter} — description", height=60, key=f"{k}_desc")


def _tp_spec_from_widgets(letter: str) -> tp.ProjectSpec:
    k = letter.lower()
    s = st.session_state
    return tp.ProjectSpec(
        name=str(s.get(f"{k}_name", f"Project {letter}")),
        description=str(s.get(f"{k}_desc", "")),
        currency=str(s[f"{k}_ccy"]),
        initial_investment=float(s[f"{k}_inv"]),
        annual_revenues=float(s[f"{k}_rev"]),
        operating_costs=float(s[f"{k}_cost"]),
        tax_rate=float(s[f"{k}_tax"]),
        discount_rate=float(s[f"{k}_disc"]),
        financing_rate=float(s[f"{k}_fin"]),
        reinvestment_rate=float(s[f"{k}_rein"]),
        project_life=float(s[f"{k}_life"]),
        working_capital=float(s[f"{k}_wc"]),
        terminal_value=float(s[f"{k}_tv"]),
        revenue_growth_rate=float(s.get(f"{k}_revg", 0)),
    )


def _tp_ratemap_ready(config: tp.ComparisonConfig) -> list[str]:
    missing = []
    currencies = [p.currency for p in config.projects.values()]
    currencies.append(config.comparison_currency)
    for ccy in set(currencies):
        if ccy == config.comparison_currency:
            continue
        direct = f"{ccy}/{config.comparison_currency}"
        inverse = f"{config.comparison_currency}/{ccy}"
        has_direct = config.ratemap.get(direct) is not None and config.ratemap.get(direct).rate == config.ratemap.get(direct).rate
        has_inv = config.ratemap.get(inverse) is not None and config.ratemap.get(inverse).rate == config.ratemap.get(inverse).rate
        ok = has_direct or has_inv
        if ccy != "USD" and not ok:
            via = f"{ccy}/USD"
            vu = f"USD/{config.comparison_currency}" if config.comparison_currency != "USD" else None
            has_via = config.ratemap.get(via) is not None and config.ratemap.get(via).rate == config.ratemap.get(via).rate
            has_vu = vu is None or (config.ratemap.get(vu) is not None and config.ratemap.get(vu).rate == config.ratemap.get(vu).rate)
            ok = has_via and has_vu
        if not ok:
            missing.append(f"{ccy} to {config.comparison_currency}")
    return list(dict.fromkeys(missing))


def _render_tp_result(out: dict[str, Any], ccy: str):
    rec = out["recommendation"]
    ranking = out["ranking_df"]
    optimism = out["optimisation"]

    st.markdown("#### Ranking")
    st.dataframe(
        ranking[["Rank", "Project", "Name", "Composite Score", "Risk"]], width="stretch"
    )
    for _, r in ranking.iterrows():
        st.markdown(
            f'<div class="vt-kpi" style="margin-bottom:8px"><div class="k-label">'
            f'#{int(r["Rank"])} · Project {r["Project"]} ({r["Name"]}) · score {r["Composite Score"]:.3f} · risk {r["Risk"]}</div>'
            f'<div class="k-sub">{rec.get(f"explanation_rank{int(r['Rank'])}", "")}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown(f"#### Capital Optimisation — {optimism['type']}")
    st.markdown(optimism["explanation"])
    if optimism["type"] == "Divisible":
        st.dataframe(optimism["allocation_df"], width="stretch")
    else:
        st.dataframe(optimism["combinations_df"], width="stretch")
        st.markdown(f"**Best combination:** {optimism.get('best_combination') or 'none within budget'}")

    st.markdown("#### Final Recommendation")
    st.markdown(f"**WHAT WON:** {rec['what']}")
    st.markdown(f"**WHY:** {rec['why']}")
    st.markdown("**EVIDENCE**")
    for e in rec["evidence"]:
        st.markdown(f"- {e}")
    st.markdown(f"**RISKS:** {rec['risks']}")
    st.markdown(f"**WHAT MANAGEMENT SHOULD DO:** {rec['action']}")

    st.markdown("#### Exchange Rates Used")
    rate_rows = []
    for pair, fr in out["rates"].items():
        rate_rows.append(
            {
                "Currency Pair": pair,
                "Rate Used": (None if fr.rate != fr.rate else fr.rate),
                "Source": fr.source,
                "Timestamp": (str(fr.ts)[:19].replace("T", " ") if fr.ts else "N/A"),
                "Live or Manual": fr.status,
            }
        )
    st.dataframe(pd.DataFrame(rate_rows), width="stretch")

    st.markdown("#### Management Report & Email")
    _tp_pdf_and_email(out)


def _tp_pdf_and_email(out: dict[str, Any]):
    pdf_bytes = None
    try:
        if not hasattr(rg, "build_three_project_pdf_report"):
            raise AttributeError(
                "build_three_project_pdf_report is missing from report_generator.py — "
                "update report_generator.py on the deployment."
            )
        pdf_bytes = rg.build_three_project_pdf_report(out)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Three-Project PDF generation failed: {exc}")

    if pdf_bytes is not None:
        st.download_button(
            "Download Comparison PDF",
            data=pdf_bytes,
            file_name="three_project_comparison_report.pdf",
            mime="application/pdf",
        )

    rec = out["recommendation"]
    with st.expander("Email the comparison report", expanded=False):
        to_email = st.text_input("Recipient email", key="tp_to")
        subject = st.text_input("Subject", "Integrated Investment Decision Agent — Three-Project Comparison Report", key="tp_subject")
        body = st.text_area(
            "Message (optional)",
            f"{rec['what']}\n\n{rec['why']}\n\nRISKS: {rec['risks']}\n\n"
            f"WHAT MANAGEMENT SHOULD DO: {rec['action']}",
            height=160, key="tp_body",
        )
        if st.button("SEND REPORT", type="primary"):
            _send(to_email, subject, body, [("three_project_comparison_report.pdf", pdf_bytes)] if pdf_bytes else [])


def _send(to_email: str, subject: str, body: str, attachments: list[tuple[str, bytes]]):
    ok, msg = email_service.send_email(
        to_email=to_email, subject=subject, body_text=body, attachments=attachments
    )
    if ok:
        st.success(msg)
    else:
        st.error(msg)


def render_ai_decision():
    section_header(
        "AI Decision",
        "The automated decision rationale — the recommendation first, then each piece of evidence.",
    )
    state = get_state()
    final = state.get("final")
    if final is None:
        empty_state("No case loaded", "Run an analysis from the sidebar first.")
        return
    results = state["results"]
    risk_results = state["risk_results"]
    scenarios = state["scenarios"]
    metrics = results["metrics"]

    decision_banner(final)
    st.markdown(f"**Recommendation.** {final['recommendation']}")
    st.markdown("**Evidence considered**")
    for e in final["reason"].splitlines():
        if e.startswith("- "):
            st.markdown(f"- {e[2:]}")

    rscore = risk_score(risk_results)
    st.markdown(f"**Risk overlay.** Overall risk is {risk_label(rscore)} ({rscore}/4). "
                f"{risk_results['overall_explanation']}")

    st.markdown("**Scenario stress**")
    for key in ["base", "worst"]:
        sm = scenarios[key]["summary"]
        verdict = "value is preserved (NPV ≥ 0)" if sm["npv"] >= 0 else "value is destroyed (NPV < 0)"
        st.markdown(f"- **{scenarios[key]['label']}:** {fmt_money(sm['npv'])} — {verdict} "
                    f"({sm['decision']}). {sm['explanation']}")

    st.markdown("**Management guidance**")
    st.info(final["recommendation"])


def _report_bytes(state: dict[str, Any]) -> tuple[bytes, bytes, bytes]:
    results = state["results"]
    scenarios = state["scenarios"]
    sens = state["sens_summary"]
    sens_df = state.get("sens_df", pd.DataFrame())
    risk = state["risk_results"]
    pdf = rg.build_pdf_report(results, scenarios, sens, risk)
    word = rg.build_word_report(results, scenarios, sens, risk)
    excel = _excel_bytes(results, scenarios, sens_df, risk)
    return pdf, word, excel


def _excel_bytes(results: dict[str, Any], scenarios: dict[str, Any], sens_df: pd.DataFrame, risk_results: dict[str, Any]) -> bytes:
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    wb = openpyxl.Workbook()
    thin = Side(style="thin", color="CCCCCC")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    header_fill = PatternFill("solid", fgColor="1F3A5F")
    header_font = Font(name="Arial", color="FFFFFF", bold=True)
    blue = Font(name="Arial", color="1F4E78")
    black = Font(name="Arial", color="000000")

    def style_sheet(ws, df, user_input_cols=None, result_idx=None):
        for c in ws[1]:
            c.font = header_font
            c.fill = header_fill
        for row in ws.iter_rows(min_row=2):
            for c in row:
                c.border = border
                c.font = black
                if isinstance(c.value, float) and c.value > 100:
                    c.number_format = "$#,##0;($#,##0)"
        if user_input_cols:
            for idx, col in enumerate(df.columns, start=1):
                if col in user_input_cols:
                    for row in ws.iter_rows(min_row=2, min_col=idx, max_col=idx):
                        for c in row:
                            c.font = blue
        if result_idx:
            for idx, col in enumerate(df.columns, start=1):
                if col in result_idx:
                    for row in ws.iter_rows(min_row=2, min_col=idx, max_col=idx):
                        for c in row:
                            c.fill = PatternFill("solid", fgColor="D6EAF8")
        ws.freeze_panes = "A2"

    ws = wb.active
    ws.title = "Capital Budgeting"
    style_sheet(ws, results["cash_flow_table"], user_input_cols={"Initial Investment", "Working Capital"})

    ws2 = wb.create_sheet("DCF Valuation")
    style_sheet(ws2, results["dcf_table"], result_idx={"Present Value"})

    ws3 = wb.create_sheet("Key Metrics")
    ws3.append(["Metric", "Value"])
    m = results["metrics"]
    for name, val in [
        ("Initial Investment", m["initial_investment"]), ("NPV", m["npv"]), ("IRR (%)", m["irr"]),
        ("MIRR (%)", m["mirr"]), ("Payback (years)", m["payback"]), ("Profitability Index", m["pi"]),
        ("ROI (%)", m["roi"]), ("Total Project Value", m["total_project_value"]),
        ("PV of Terminal Value", m["pv_terminal"]),
    ]:
        ws3.append([name, val])
    ws3["B1"].font = header_font

    ws4 = wb.create_sheet("Scenarios")
    ws4.append(["Scenario", "NPV", "IRR (%)", "MIRR (%)", "ROI (%)", "Payback", "PI", "Decision"])
    for key, s in scenarios.items():
        sm = s["summary"]
        ws4.append([s["label"], sm["npv"], sm["irr"], sm["mirr"], sm["roi"], sm["payback"], sm["pi"], sm["decision"]])
    style_sheet(ws4, pd.DataFrame([[c.value for c in row] for row in ws4.iter_rows(min_row=2)], columns=["Scenario", "NPV", "IRR (%)", "MIRR (%)", "ROI (%)", "Payback", "PI", "Decision"]))

    ws5 = wb.create_sheet("Sensitivity")
    style_sheet(ws5, sens_df)

    ws6 = wb.create_sheet("Risk Analysis")
    ws6.append(["Risk", "Severity", "Impact", "Explanation", "Mitigation"])
    for r in risk_results["risks"]:
        ws6.append([r.risk, r.severity, r.impact, r.explanation, r.mitigation])
    for c in ws6[1]:
        c.font = header_font
        c.fill = header_fill
    ws6.append([])
    ws6.append(["Overall Risk Level", risk_results["overall_risk"]])
    ws6.append(["Overall Explanation", risk_results["overall_explanation"]])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()


def _tbl_html(df: pd.DataFrame) -> str:
    """Render a DataFrame as a formatted HTML table for the report preview."""
    def cell(v):
        if pd.isna(v):
            return ""
        if isinstance(v, (int, float)):
            try:
                f = float(v)
            except (TypeError, ValueError):
                return str(v)
            return f"{f:,.0f}" if abs(f) >= 1 or f == 0 else f"{f:,.2f}"
        return str(v)

    rows = [[cell(v) for v in row] for row in df.values]
    frame = pd.DataFrame(rows, columns=[str(c) for c in df.columns])
    return frame.to_html(index=False, border=0, classes="vt-tbl", escape=True)


def _report_preview_html(state: dict[str, Any]) -> str:
    """The full generated report as live HTML — exactly the document that the PDF/Word/Excel
    downloads and the email attachment are built from."""
    from datetime import date

    results = state["results"]
    inputs = results["inputs"]
    metrics = results["metrics"]
    decisions = results["decisions"]
    final = state["final"]
    risk_results = state["risk_results"]
    scenarios = state["scenarios"]
    sens_df = state.get("sens_df", pd.DataFrame())
    today = date.today().strftime("%d %b %Y")

    badge = lambda s: f'<span class="vt-badge {status_tone(s)}">{s}</span>' if s else ""

    def money(v):
        return fmt_money(v) if v is not None and np.isfinite(v) else "N/A"

    def pct(v):
        return fmt_pct(v) if v is not None and np.isfinite(v) else "N/A"

    metric_rows = "".join(
        f"<tr><td>{label}</td><td class='r'>{value}</td><td>{badge(stat)}</td></tr>"
        for label, value, stat in [
            ("Initial investment", money(inputs.initial_investment), ""),
            ("Net present value", money(metrics["npv"]), decisions["npv"]["status"]),
            ("Internal rate of return", pct(metrics["irr"]), decisions["irr"]["status"]),
            ("Modified IRR", pct(metrics["mirr"]), decisions["mirr"]["status"]),
            ("Return on investment", pct(metrics["roi"]), decisions["roi"]["status"]),
            ("Profitability index", fmt_num(metrics["pi"], 3), decisions["pi"]["status"]),
            ("Payback (years)", fmt_num(metrics["payback"]), decisions["payback"]["status"]),
        ]
    )

    scenario_rows = "".join(
        f"<tr><td>{s['label']}</td><td class='r'>{money(sm['npv'])}</td>"
        f"<td class='r'>{pct(sm['irr'])}</td><td class='r'>{pct(sm['roi'])}</td>"
        f"<td>{badge(sm['decision'])}</td><td>{sm['explanation']}</td></tr>"
        for key, s in scenarios.items()
        for sm in [s["summary"]]
    )

    risk_rows = "".join(
        f"<tr><td>{r.risk}</td><td class='c'>{r.severity}</td><td>{r.explanation}</td>"
        f"<td>{r.mitigation}</td></tr>"
        for r in risk_results["risks"]
    )

    sens_rows = ""
    if not sens_df.empty:
        sf = sens_df.head(10)
        for idx, row in sf.iterrows():
            parts = " | ".join(f"{c}: {v}" for c, v in row.items() if pd.notna(v))
            sens_rows += f'<tr><td class="c">{int(idx) + 1}</td><td>{parts}</td></tr>'

    cash_block = f"<div class='vt-tbl-wrap'>{_tbl_html(results['cash_flow_table'])}</div>"
    dcf_block = f"<div class='vt-tbl-wrap'>{_tbl_html(results['dcf_table'])}</div>"

    return f"""
<div class="vt-report">
  <div class="vt-report-head">
    <div class="vr-brand">Integrated Investment Decision Agent<em>.</em></div>
    <div class="vr-title">Investment Case Report</div>
    <div class="vr-meta">{today} &middot; generated live from the case · {final["decision"]}</div>
  </div>

  <div class="vt-report-sec">1. Executive Decision</div>
  <div class="vt-decision {status_tone(final['decision'])}">
    <div class="d-verdict">{final["decision"]}</div>
    <div class="d-reason">{final["reason"]}</div>
  </div>
  <div class="vt-report-note"><b>Recommendation.</b> {final["recommendation"]}</div>

  <div class="vt-report-sec">2. Key Metrics & Verification</div>
  <div class="vt-tbl-wrap">
    <table class="vt-tbl"><thead><tr><th>Metric</th><th>Value</th><th>Verdict</th></tr></thead>
    <tbody>{metric_rows}</tbody></table>
  </div>

  <div class="vt-report-sec">3. Capital Budgeting — Cash-Flow Schedule</div>
  {cash_block}

  <div class="vt-report-sec">4. DCF & Valuation — Present Value by Year</div>
  {dcf_block}

  <div class="vt-report-sec">5. Scenario Analysis</div>
  <div class="vt-tbl-wrap">
    <table class="vt-tbl"><thead><tr><th>Scenario</th><th>NPV</th><th>IRR</th><th>ROI</th><th>Decision</th><th>Rationale</th></tr></thead>
    <tbody>{scenario_rows}</tbody></table>
  </div>

  <div class="vt-report-sec">6. Sensitivity (top drivers)</div>
  <div class="vt-tbl-wrap">
    <table class="vt-tbl"><thead><tr><th>#</th><th>Driver and its impact</th></tr></thead>
    <tbody>{sens_rows}</tbody></table>
  </div>

  <div class="vt-report-sec">7. Risk Register</div>
  <div class="vt-tbl-wrap">
    <table class="vt-tbl"><thead><tr><th>Risk</th><th>Severity</th><th>Explanation</th><th>Mitigation</th></tr></thead>
    <tbody>{risk_rows}</tbody></table>
  </div>
  <div class="vt-report-note"><b>Overall risk:</b> {risk_results["overall_risk"]}. {risk_results["overall_explanation"]}</div>

  <div class="vt-report-sec">8. Conclusion</div>
  <div class="vt-report-note">{final["recommendation"]}</div>
  <div class="vt-report-foot">Prepared by the Integrated Investment Decision Agent — every figure above is computed live from the case
  assumptions. Download the PDF / Word / Excel below for a print-ready version of this document.</div>
</div>
"""


def render_reports():
    section_header(
        "Reports & Distribution",
        "Export deliverables (PDF, Word, Excel) and email the report to any recipient "
        "with one action. The sender is configured from secrets — never from the UI.",
    )
    state = get_state()
    results = state.get("results")
    if results is None:
        empty_state("No case loaded", "Run an analysis from the sidebar first.")
        return

    st.markdown("#### Report document — full content preview")
    st.markdown(_report_preview_html(state), unsafe_allow_html=True)
    st.caption(
        "This is the complete generated report, rendered live from the case. The PDF, Word and "
        "Excel downloads below contain exactly the same content."
    )

    pdf, word, excel = _report_bytes(state)
    c1, c2, c3 = st.columns(3)
    c1.download_button("Download PDF Report", data=pdf, file_name="valtexa_investment_report.pdf", mime="application/pdf")
    c2.download_button("Download Word Report", data=word, file_name="valtexa_investment_report.docx",
                       mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    c3.download_button("Download Excel Workbook", data=excel, file_name="valtexa_investment_analysis.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    st.markdown("---")
    st.markdown("#### Email & Distribution")
    status = email_service.sender_status()
    if status["configured"]:
        st.success(
            f"Sender ready — {status['from_addr']} via {status['host']}:{status['port']} "
            f"(login {status['username']}). Password is stored in secrets only and is never "
            "shown here or requested in the app."
        )
    else:
        st.error(
            "Sender is NOT configured. Add an [smtp] section to .streamlit/secrets.toml "
            "(or set SMTP_HOST / SMTP_PORT / SMTP_USERNAME / SMTP_PASSWORD / SMTP_FROM in "
            "environment variables or Streamlit Cloud secrets) and restart the app. "
            "You can still compose and preview the full email below — it will be sent the "
            "moment the sender is configured."
        )

    c1, c2 = st.columns([2, 1])
    to_email = c1.text_input("Recipient email", placeholder="analyst@company.com")
    subject = c2.text_input("Subject", f"Integrated Investment Decision Agent — Investment Report — {results['inputs'].project_name}")
    message = st.text_area(
        "Message (optional)",
        email_service.build_email_body(
            results["metrics"], state["risk_results"]["overall_risk"],
            state["final"]["decision"], state["final"]["reason"], results["inputs"].project_name,
        ),
        height=180,
    )
    attachments = [
        ("valtexa_investment_report.pdf", pdf),
        ("valtexa_investment_analysis.xlsx", excel),
    ]

    with st.expander("Email preview — complete contents of the message", expanded=False):
        st.markdown(
            f"""
<div class="vt-email">
  <div class="vt-email-row"><span class="vt-email-key">To</span>{html.escape(to_email) or "<em>not set</em>"}</div>
  <div class="vt-email-row"><span class="vt-email-key">Subject</span>{html.escape(subject)}</div>
  <div class="vt-email-row"><span class="vt-email-key">Attachments</span>{html.escape(", ".join(n for n, _ in attachments))}</div>
  <pre class="vt-email-body">{html.escape(message)}</pre>
</div>
""",
            unsafe_allow_html=True,
        )
        st.caption(
            "This is exactly what SEND REPORT delivers to the recipient. Nothing below (To, "
            "Subject, Message) requires a sender — the sender is only needed at delivery time."
        )

    if st.button("SEND REPORT", type="primary"):
        ok, msg = email_service.validate_recipient(to_email)
        if not ok:
            st.error(msg)
        elif not status["configured"]:
            st.error(
                "Not sent — the sender is not configured. Add an [smtp] section to "
                ".streamlit/secrets.toml (or set SMTP_HOST / SMTP_PORT / SMTP_USERNAME / "
                "SMTP_PASSWORD / SMTP_FROM in environment variables or Streamlit Cloud "
                "secrets) and restart the app. The complete message contents are shown in "
                "the 'Email preview' expander above and will be delivered unchanged."
            )
        else:
            with st.spinner("Sending..."):
                ok, msg = email_service.send_email(
                    to_email=to_email, subject=subject, body_text=message,
                    attachments=attachments,
                )
            if ok:
                st.success(msg)
            else:
                st.error(msg)


def render_settings():
    section_header(
        "Settings",
        "Platform configuration, sender status and deployment notes. Sensitive values are "
        "never displayed or requested — they live in secrets only.",
    )
    st.markdown("#### Sender (SMTP / API) configuration")
    status = email_service.sender_status()
    st.dataframe(
        pd.DataFrame(
            {
                "Setting": ["Configured", "Host", "Port", "Login (username)", "Password", "From address", "Source"],
                "Value": [
                    "Yes" if status["configured"] else "No",
                    status["host"], status["port"], status["username"],
                    status["password"] or "not set", status["from_addr"], status["source"],
                ],
            }
        ),
        width="stretch", height=200,
    )
    st.caption(
        "To change the sender: edit .streamlit/secrets.toml (local) or the Secrets tab "
        "(Streamlit Cloud). Restart the app afterwards. Passwords are read into memory only."
    )
    if status["configured"] and st.button("Test sender connection (no email is sent)"):
        ok, msg = email_service.test_connection()
        if ok:
            st.success(msg)
        else:
            st.error(msg)

    st.markdown("#### Case data")
    state = get_state()
    if state.get("results") is not None:
        st.markdown(
            f"Active case: **{state['inputs'].project_name}** ({state['final']['decision']}). "
            "Clear it from the sidebar to start over."
        )
    else:
        st.markdown("No active case.")

    st.markdown("#### Platform")
    st.markdown(
        """
- **Engines**: `calculations.py`, `risk_analysis.py`, `scenario_analysis.py`, `fx_rates.py`,
  `three_project.py`, `report_generator.py`, `email_service.py`, `data_validation.py`.
- Every figure in the Integrated Investment Decision Agent is computed live from the case inputs — nothing is pre-computed or hard-coded.
- Reports are produced as PDF, Word and Excel and can be emailed to any valid recipient.
- The sender is configured only through `.streamlit/secrets.toml` or `SMTP_*` environment/secrets
  variables. The user never supplies the sender password and credentials are never exposed.
"""
    )
    with st.expander("How to configure the sender"):
        st.markdown(
            """
Create or edit `.streamlit/secrets.toml` in the project folder:

```toml
[smtp]
host = "smtp.gmail.com"
port = "587"
username = "sender@yourdomain.com"
password = "app-password-or-token"
from_addr = "Integrated Investment Decision Agent <sender@yourdomain.com>"
```

For Gmail, use an App Password. On Streamlit Cloud use **Settings, Secrets** with the same
`[smtp]` keys, or the `SMTP_HOST` / `SMTP_PORT` / `SMTP_USERNAME` / `SMTP_PASSWORD` / `SMTP_FROM`
environment variables. Restart the app once configured.
"""
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    inject_theme()
    section = render_sidebar()
    _maybe_auto_fetch_fx()
    if "refresh" in st.session_state.get("fx_requested", ""):
        _run_live_fetch()
        st.session_state.pop("fx_requested", None)
    if section == "Executive Dashboard":
        render_executive_dashboard()
    elif section == "Investment Cases":
        render_investment_cases()
    elif section == "Capital Budgeting":
        render_capital_budgeting()
    elif section == "DCF & Valuation":
        render_dcf_valuation()
    elif section == "Returns":
        render_returns()
    elif section == "Risk Analysis":
        render_risk_analysis()
    elif section == "FX & Multi-Currency":
        render_fx_multicurrency()
    elif section == "Scenario Analysis":
        render_scenario_analysis()
    elif section == "Sensitivity Analysis":
        render_sensitivity_analysis()
    elif section == "Project Comparison":
        render_project_comparison()
    elif section == "AI Decision":
        render_ai_decision()
    elif section == "Reports":
        render_reports()
    else:
        render_settings()


if __name__ == "__main__":
    main()