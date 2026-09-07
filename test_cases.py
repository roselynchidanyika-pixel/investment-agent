import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from calculations import calculate_all_metrics
from data_validation import validate_project_inputs
from risk_analysis import assess_risks
from scenario_analysis import run_scenario_analysis
from project_templates import PROJECT_TYPES, get_project_template, get_template_inputs
from fx_analysis import (
    FX_SCENARIOS,
    STRATEGY_OPTIONS,
    run_fx_scenario_analysis,
    assess_currency_exposure,
    recommend_currency_strategy,
    get_fx_risk_summary,
)


def test_profitable_project():
    print("\n" + "=" * 70)
    print("TEST 1: Normal Profitable Project")
    print("=" * 70)

    inputs = {
        "project_name": "Profitable Manufacturing Plant",
        "project_description": "New factory for consumer goods",
        "initial_investment": 1000000,
        "project_life": 10,
        "annual_revenue": 500000,
        "operating_costs": 200000,
        "tax_rate": 0.25,
        "working_capital": 50000,
        "terminal_value": 200000,
        "wacc": 0.10,
        "financing_rate": 0.08,
        "reinvestment_rate": 0.06,
        "growth_rate": 0.03,
        "depreciation_rate": 0.10,
        "currency": "USD",
    }

    is_valid, errors, warnings = validate_project_inputs(inputs)
    print(f"Validation: {'PASS' if is_valid else 'FAIL'}")
    if errors:
        for e in errors:
            print(f"  Error: {e}")

    metrics = calculate_all_metrics(inputs)
    risk_data = assess_risks(inputs, metrics)

    print(f"\nNPV: ${metrics['npv']:,.0f}")
    print(f"IRR: {metrics['irr']:.1%}")
    print(f"MIRR: {metrics['mirr']:.1%}")
    print(f"PI: {metrics['pi']:.2f}")
    print(f"ROI: {metrics['roi']:.1%}")
    print(f"Payback: {metrics['payback']:.1f} years")
    print(f"Risk Level: {risk_data['overall_level']}")
    print(f"Decision: {metrics['npv_status']['decision']}")

    expected = "ACCEPT"
    actual = metrics["npv_status"]["decision"]
    passed = actual == expected
    print(f"\nExpected: {expected}")
    print(f"Actual: {actual}")
    print(f"RESULT: {'PASS' if passed else 'FAIL'}")
    assert passed, f"Test 1 failed: expected {expected}, got {actual}"
    return passed


def test_negative_npv_project():
    print("\n" + "=" * 70)
    print("TEST 2: Negative NPV Project")
    print("=" * 70)

    inputs = {
        "project_name": "Unprofitable Venture",
        "project_description": "High cost, low return project",
        "initial_investment": 5000000,
        "project_life": 5,
        "annual_revenue": 400000,
        "operating_costs": 350000,
        "tax_rate": 0.30,
        "working_capital": 200000,
        "terminal_value": 0,
        "wacc": 0.15,
        "financing_rate": 0.12,
        "reinvestment_rate": 0.08,
        "growth_rate": 0.02,
        "depreciation_rate": 0.10,
        "currency": "USD",
    }

    is_valid, errors, warnings = validate_project_inputs(inputs)
    print(f"Validation: {'PASS' if is_valid else 'FAIL'}")

    metrics = calculate_all_metrics(inputs)
    risk_data = assess_risks(inputs, metrics)

    print(f"\nNPV: ${metrics['npv']:,.0f}")
    print(f"IRR: {metrics['irr']:.1%}")
    print(f"MIRR: {metrics['mirr']:.1%}")
    print(f"PI: {metrics['pi']:.2f}")
    print(f"ROI: {metrics['roi']:.1%}")
    print(f"Payback: {metrics['payback']:.1f} years" if metrics['payback'] != float('inf') else "Payback: Never")
    print(f"Risk Level: {risk_data['overall_level']}")
    print(f"Decision: {metrics['npv_status']['decision']}")

    expected = "REJECT"
    actual = metrics["npv_status"]["decision"]
    passed = actual == expected
    print(f"\nExpected: {expected}")
    print(f"Actual: {actual}")
    print(f"RESULT: {'PASS' if passed else 'FAIL'}")
    assert passed, f"Test 2 failed: expected {expected}, got {actual}"
    return passed


def test_edge_cases():
    print("\n" + "=" * 70)
    print("TEST 3: Edge Cases")
    print("=" * 70)

    print("\n--- Edge Case 3a: Very Small Investment ---")
    inputs_small = {
        "project_name": "Micro Project",
        "project_description": "Very small investment test",
        "initial_investment": 100,
        "project_life": 3,
        "annual_revenue": 200,
        "operating_costs": 50,
        "tax_rate": 0.25,
        "working_capital": 0,
        "terminal_value": 0,
        "wacc": 0.10,
        "financing_rate": 0.08,
        "reinvestment_rate": 0.06,
        "growth_rate": 0.0,
        "depreciation_rate": 0.33,
        "currency": "USD",
    }
    try:
        metrics_small = calculate_all_metrics(inputs_small)
        print(f"  NPV: ${metrics_small['npv']:,.0f}")
        print(f"  Decision: {metrics_small['npv_status']['decision']}")
        print("  RESULT: PASS (no crash)")
    except Exception as e:
        print(f"  RESULT: FAIL - {e}")
        return False

    print("\n--- Edge Case 3b: Zero Revenue ---")
    inputs_zero = {
        "project_name": "Zero Revenue Test",
        "project_description": "Testing zero revenue handling",
        "initial_investment": 1000000,
        "project_life": 5,
        "annual_revenue": 0,
        "operating_costs": 50000,
        "tax_rate": 0.25,
        "working_capital": 0,
        "terminal_value": 0,
        "wacc": 0.10,
        "financing_rate": 0.08,
        "reinvestment_rate": 0.06,
        "growth_rate": 0.0,
        "depreciation_rate": 0.20,
        "currency": "USD",
    }
    try:
        metrics_zero = calculate_all_metrics(inputs_zero)
        print(f"  NPV: ${metrics_zero['npv']:,.0f}")
        print(f"  Decision: {metrics_zero['npv_status']['decision']}")
        print("  RESULT: PASS (no crash)")
    except Exception as e:
        print(f"  RESULT: FAIL - {e}")
        return False

    print("\n--- Edge Case 3c: Validation with Missing Fields ---")
    invalid_inputs = {"project_name": "Incomplete"}
    is_valid, errors, warnings = validate_project_inputs(invalid_inputs)
    passed_valid = not is_valid and len(errors) > 0
    print(f"  Valid: {is_valid}")
    print(f"  Errors caught: {len(errors)}")
    print(f"  RESULT: {'PASS' if passed_valid else 'FAIL'}")

    print("\n--- Edge Case 3d: Negative Investment ---")
    neg_inputs = {
        "project_name": "Neg Test",
        "project_description": "Test",
        "initial_investment": -100000,
        "project_life": 5,
        "annual_revenue": 50000,
        "operating_costs": 20000,
        "tax_rate": 0.25,
        "working_capital": 0,
        "terminal_value": 0,
        "wacc": 0.10,
        "financing_rate": 0.08,
        "reinvestment_rate": 0.06,
    }
    is_valid_neg, errors_neg, _ = validate_project_inputs(neg_inputs)
    passed_neg = not is_valid_neg
    print(f"  Valid: {is_valid_neg}")
    print(f"  Errors caught: {len(errors_neg)}")
    print(f"  RESULT: {'PASS' if passed_neg else 'FAIL'}")

    return True


def test_high_risk_project():
    print("\n" + "=" * 70)
    print("TEST 4: High-Risk / Worst-Case Project")
    print("=" * 70)

    inputs = {
        "project_name": "High Risk Speculative Venture",
        "project_description": "Speculative project with thin margins and high WACC",
        "initial_investment": 10000000,
        "project_life": 7,
        "annual_revenue": 2000000,
        "operating_costs": 1900000,
        "tax_rate": 0.35,
        "working_capital": 1000000,
        "terminal_value": 500000,
        "wacc": 0.20,
        "financing_rate": 0.18,
        "reinvestment_rate": 0.10,
        "growth_rate": 0.02,
        "depreciation_rate": 0.14,
        "currency": "ZAR",
    }

    is_valid, errors, warnings = validate_project_inputs(inputs)
    print(f"Validation: {'PASS' if is_valid else 'FAIL (expected)'}")
    if warnings:
        for w in warnings:
            print(f"  Warning: {w}")

    metrics = calculate_all_metrics(inputs)
    risk_data = assess_risks(inputs, metrics)

    print(f"\nNPV: ${metrics['npv']:,.0f}")
    print(f"IRR: {metrics['irr']:.1%}")
    print(f"MIRR: {metrics['mirr']:.1%}")
    print(f"PI: {metrics['pi']:.2f}")
    print(f"ROI: {metrics['roi']:.1%}")
    print(f"Payback: {metrics['payback']:.1f} years" if metrics['payback'] != float('inf') else "Payback: Never")
    print(f"Risk Level: {risk_data['overall_level']}")

    scenario_data = run_scenario_analysis(inputs)
    print(f"\nBest Case NPV: ${scenario_data['best_case']['npv']:,.0f}")
    print(f"Base Case NPV: ${scenario_data['base_case']['npv']:,.0f}")
    print(f"Worst Case NPV: ${scenario_data['worst_case']['npv']:,.0f}")

    overall_metrics_reject = (
        metrics["npv_status"]["decision"] == "REJECT" or
        risk_data["overall_level"] in ("HIGH", "VERY HIGH") or
        scenario_data["worst_case"]["npv_status"]["decision"] == "REJECT"
    )
    passed = overall_metrics_reject
    actual = "REJECT" if metrics["npv_status"]["decision"] == "REJECT" else "REVIEW"
    print(f"\nExpected: REJECT or REVIEW")
    print(f"Actual: {actual}")
    print(f"RESULT: {'PASS' if passed else 'FAIL'}")
    assert passed, f"Test 4 failed"
    return passed


def test_project_templates():
    print("\n" + "=" * 70)
    print("TEST 5: Project Type Templates")
    print("=" * 70)

    expected_names = {
        "Solar Energy Expansion",
        "Manufacturing Capacity Upgrade",
        "Technology & Digitalisation",
        "Export Expansion Project",
        "Agricultural Investment Project",
    }
    actual_names = {t["name"] for t in PROJECT_TYPES}
    for name in sorted(expected_names):
        ok = name in actual_names
        print(f"  Template '{name}': {'PASS' if ok else 'MISSING'}")
        assert ok, f"Test 5 failed: missing template '{name}'"

    for t in PROJECT_TYPES:
        for key in ("id", "name", "description", "inputs"):
            assert key in t, f"Test 5 failed: template {t.get('name', '?')} missing key '{key}'"
        assert get_project_template(t["id"]) is not None
        assert isinstance(get_template_inputs(t["id"]), dict)

    sample = get_template_inputs("solar_energy_expansion")
    for key in ("zig_revenue_share", "zig_cost_share", "zar_revenue_share",
                "zar_cost_share", "investment_fx_share", "liquidity_buffer_months"):
        assert key in sample, f"Test 5 failed: template missing FX field '{key}'"

    print(f"\nTotal templates: {len(PROJECT_TYPES)}")
    print("RESULT: PASS")
    return True


def test_fx_modules():
    print("\n" + "=" * 70)
    print("TEST 6: FX Market, Scenarios, Risk & Currency Strategy")
    print("=" * 70)

    inputs = {
        "project_name": "FX Integration Test",
        "project_description": "Verify FX pipeline",
        "initial_investment": 1000000,
        "project_life": 10,
        "annual_revenue": 400000,
        "operating_costs": 120000,
        "tax_rate": 0.25,
        "working_capital": 0,
        "terminal_value": 0,
        "wacc": 0.10,
        "financing_rate": 0.08,
        "reinvestment_rate": 0.06,
        "growth_rate": 0.0,
        "depreciation_rate": 0.10,
        "currency": "USD",
        "zig_revenue_share": 0.4,
        "zig_cost_share": 0.6,
        "zar_revenue_share": 0.2,
        "zar_cost_share": 0.1,
        "investment_fx_share": 0.5,
        "liquidity_buffer_months": 6,
    }

    fx_scenarios = run_fx_scenario_analysis(inputs)
    results = fx_scenarios.get("results", [])
    assert len(results) == len(FX_SCENARIOS), "Test 6 failed: scenario count mismatch"
    labels = {r["label"] for r in results}
    print(f"  Scenarios run: {len(results)}")
    for r in results:
        print(f"    {r['label']}: NPV {r['npv']:,.0f} ({r['npv_delta']:+,.0f})")
    expected_labels = {"ZiG +5%", "ZiG -5%", "USD +5%", "USD -5%", "ZAR +5%", "ZAR -5%"}
    assert expected_labels.issubset(labels), "Test 6 failed: missing scenario labels"
    assert isinstance(fx_scenarios.get("max_npv_swing_pct"), float)

    exposure = assess_currency_exposure(inputs)
    print(f"\n  Exposure: revenue {exposure['revenue_exposure']:.0%}, "
          f"cost {exposure['cost_exposure']:.0%}, level {exposure['level']}")

    fx_market = {
        "rates": {"USD_ZIG": 13.5, "ZIG_USD": 0.074, "USD_ZAR": 18.5, "ZAR_USD": 0.054},
        "pairs": [],
        "fx_risk_level": "MODERATE",
        "fx_risk_score": 5.0,
    }
    fx_risk = get_fx_risk_summary(inputs, fx_market, fx_scenarios)
    assert fx_risk["level"] in ("LOW", "MODERATE", "HIGH"), "Test 6 failed: bad FX risk level"

    strategy = recommend_currency_strategy(inputs, fx_market, fx_scenarios, exposure)
    assert strategy["strategy"] in STRATEGY_OPTIONS, f"Test 6 failed: unknown strategy '{strategy['strategy']}'"
    print(f"\n  FX Risk: {fx_risk['level']} (score {fx_risk['score']})")
    print(f"  Strategy: {strategy['strategy']} -> {strategy['recommendation_text']}")

    text = strategy["reason"] + " ".join(strategy["key_fx_factors"])
    for word in ("appreciate", "depreciate"):
        assert word not in text.lower(), "Test 6 failed: strategy must not predict currency direction"
    print("  Strategy uses probability/scenario language: PASS")

    print("\nRESULT: PASS")
    return True


def run_all_tests():
    print("\n" + "#" * 70)
    print("#  INTEGRATED INVESTMENT DECISION AGENT FOR CAPITAL PROJECTS - TEST SUITE")
    print("#" * 70)

    results = {}
    tests = [
        ("Test 1: Normal Profitable Project", test_profitable_project),
        ("Test 2: Negative NPV Project", test_negative_npv_project),
        ("Test 3: Edge Cases", test_edge_cases),
        ("Test 4: High-Risk Project", test_high_risk_project),
        ("Test 5: Project Type Templates", test_project_templates),
        ("Test 6: FX Market & Strategy", test_fx_modules),
    ]

    for name, test_func in tests:
        try:
            passed = test_func()
            results[name] = "PASS" if passed else "FAIL"
        except AssertionError as e:
            results[name] = f"FAIL: {e}"
        except Exception as e:
            results[name] = f"ERROR: {e}"

    print("\n" + "#" * 70)
    print("#  TEST RESULTS SUMMARY")
    print("#" * 70)
    all_passed = True
    for name, result in results.items():
        status = "PASS" if result == "PASS" else "FAIL"
        print(f"  {name}: {result}")
        if result != "PASS":
            all_passed = False

    print(f"\n{'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
    print("#" * 70)
    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
