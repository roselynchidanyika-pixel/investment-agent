from typing import Dict, Any, List, Optional


PROJECT_TYPES: List[Dict[str, Any]] = [
    {
        "id": "generic",
        "name": "Generic / Custom Project",
        "description": (
            "A general-purpose capital investment. Use this option when your project does not fit "
            "one of the predefined categories, or to preserve full manual control of every assumption."
        ),
        "inputs": {},
    },
    {
        "id": "solar_energy_expansion",
        "name": "Solar Energy Expansion",
        "description": (
            "Investment in solar systems and energy infrastructure to reduce electricity costs "
            "and improve business continuity."
        ),
        "inputs": {
            "project_name": "Solar Energy Expansion",
            "initial_investment": 500000.0,
            "project_life": 20,
            "annual_revenue": 120000.0,
            "operating_costs": 20000.0,
            "tax_rate": 0.25,
            "working_capital": 10000.0,
            "terminal_value": 0.0,
            "wacc": 0.12,
            "financing_rate": 0.09,
            "reinvestment_rate": 0.05,
            "revenue_growth": 0.03,
            "cost_growth": 0.03,
            "terminal_growth": 0.00,
            "depreciation_rate": 0.05,
            "currency": "USD",
            "zig_revenue_share": 0.60,
            "zig_cost_share": 0.90,
            "zar_revenue_share": 0.10,
            "zar_cost_share": 0.00,
            "investment_fx_share": 0.50,
            "liquidity_buffer_months": 3,
        },
    },
    {
        "id": "manufacturing_capacity_upgrade",
        "name": "Manufacturing Capacity Upgrade",
        "description": (
            "Investment in machinery and equipment to increase production capacity and efficiency."
        ),
        "inputs": {
            "project_name": "Manufacturing Capacity Upgrade",
            "initial_investment": 800000.0,
            "project_life": 10,
            "annual_revenue": 400000.0,
            "operating_costs": 180000.0,
            "tax_rate": 0.25,
            "working_capital": 50000.0,
            "terminal_value": 0.0,
            "wacc": 0.12,
            "financing_rate": 0.09,
            "reinvestment_rate": 0.06,
            "revenue_growth": 0.04,
            "cost_growth": 0.03,
            "terminal_growth": 0.00,
            "depreciation_rate": 0.10,
            "currency": "USD",
            "zig_revenue_share": 0.30,
            "zig_cost_share": 0.40,
            "zar_revenue_share": 0.10,
            "zar_cost_share": 0.10,
            "investment_fx_share": 0.70,
            "liquidity_buffer_months": 4,
        },
    },
    {
        "id": "technology_digitalisation",
        "name": "Technology & Digitalisation",
        "description": (
            "Investment in software, automation and digital systems to improve business operations."
        ),
        "inputs": {
            "project_name": "Technology & Digitalisation",
            "initial_investment": 250000.0,
            "project_life": 5,
            "annual_revenue": 130000.0,
            "operating_costs": 35000.0,
            "tax_rate": 0.25,
            "working_capital": 15000.0,
            "terminal_value": 0.0,
            "wacc": 0.14,
            "financing_rate": 0.10,
            "reinvestment_rate": 0.05,
            "revenue_growth": 0.05,
            "cost_growth": 0.04,
            "terminal_growth": 0.00,
            "depreciation_rate": 0.20,
            "currency": "USD",
            "zig_revenue_share": 0.50,
            "zig_cost_share": 0.80,
            "zar_revenue_share": 0.10,
            "zar_cost_share": 0.00,
            "investment_fx_share": 0.40,
            "liquidity_buffer_months": 6,
        },
    },
    {
        "id": "export_expansion",
        "name": "Export Expansion Project",
        "description": (
            "Investment aimed at increasing exports and generating foreign-currency revenue."
        ),
        "inputs": {
            "project_name": "Export Expansion Project",
            "initial_investment": 1200000.0,
            "project_life": 10,
            "annual_revenue": 450000.0,
            "operating_costs": 150000.0,
            "tax_rate": 0.25,
            "working_capital": 100000.0,
            "terminal_value": 0.0,
            "wacc": 0.12,
            "financing_rate": 0.09,
            "reinvestment_rate": 0.06,
            "revenue_growth": 0.05,
            "cost_growth": 0.04,
            "terminal_growth": 0.00,
            "depreciation_rate": 0.10,
            "currency": "USD",
            "zig_revenue_share": 0.10,
            "zig_cost_share": 0.60,
            "zar_revenue_share": 0.30,
            "zar_cost_share": 0.10,
            "investment_fx_share": 0.60,
            "liquidity_buffer_months": 6,
        },
    },
    {
        "id": "agricultural_investment",
        "name": "Agricultural Investment Project",
        "description": (
            "Investment in farming, irrigation, equipment and agricultural production."
        ),
        "inputs": {
            "project_name": "Agricultural Investment Project",
            "initial_investment": 350000.0,
            "project_life": 12,
            "annual_revenue": 150000.0,
            "operating_costs": 60000.0,
            "tax_rate": 0.25,
            "working_capital": 20000.0,
            "terminal_value": 0.0,
            "wacc": 0.13,
            "financing_rate": 0.09,
            "reinvestment_rate": 0.05,
            "revenue_growth": 0.03,
            "cost_growth": 0.03,
            "terminal_growth": 0.00,
            "depreciation_rate": 0.08,
            "currency": "USD",
            "zig_revenue_share": 0.70,
            "zig_cost_share": 0.70,
            "zar_revenue_share": 0.15,
            "zar_cost_share": 0.00,
            "investment_fx_share": 0.30,
            "liquidity_buffer_months": 12,
        },
    },
]


def get_project_type_list() -> List[Dict[str, str]]:
    return [{"id": t["id"], "name": t["name"], "description": t["description"]} for t in PROJECT_TYPES]


def get_project_template(template_id: str) -> Optional[Dict[str, Any]]:
    for t in PROJECT_TYPES:
        if t["id"] == template_id:
            return t
    return None


def get_template_inputs(template_id: str) -> Dict[str, Any]:
    t = get_project_template(template_id)
    if t is None:
        return {}
    return dict(t.get("inputs", {}))