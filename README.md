# Financial Engineering Investment Decision Agent

A professional, industry-independent Streamlit web application for evaluating investment proposals and capital projects.

## Features

- **Capital Budgeting Engine**: NPV, IRR, MIRR, PI, Payback Period, ROI
- **DCF Valuation**: Complete discounted cash flow analysis
- **Returns Analysis**: IRR, MIRR, ROI, Holding Period Return, Annualized Return
- **Risk Analysis**: 8-factor risk assessment with severity scoring
- **Scenario Analysis**: Best Case / Base Case / Worst Case
- **Sensitivity Analysis**: Tornado charts and variable impact ranking
- **FX Currency Analysis**: Live ZIG, USD, ZAR exchange rates with multi-currency comparison
- **Final Investment Decision**: Weighted scoring engine (ACCEPT / REJECT / REVIEW)
- **Management Report**: Professional Word document generation
- **Email Reports**: Send analysis via email with report attachment
- **Input Validation**: Comprehensive data validation with error handling
- **CSV/Excel Upload**: Import project data from files

## Installation

```bash
pip install -r requirements.txt
```

## Running

```bash
streamlit run app.py
```

## Project Structure

```
app.py                    # Main Streamlit application
calculations.py           # Core financial calculations
data_validation.py        # Input validation and formatting
risk_analysis.py          # Risk assessment engine
scenario_analysis.py      # Scenario and sensitivity analysis
report_generator.py       # Word document report generation
email_service.py          # Email functionality
test_cases.py             # Automated test suite
sample_data.csv           # Sample project data
requirements.txt          # Python dependencies
README.md                 # This file
```

## FX Exchange Rates (ZIG/USD/ZAR)

The application fetches live exchange rates from public APIs:
- **USD/ZAR**: Fetched from open.er-api.com
- **USD/ZIG**: Estimated rates with manual override option
- **Currency Comparison**: Compare investment returns across USD, ZIG, and ZAR

**Important**: ZIG rates are indicative estimates. Always verify with your bank before making decisions.

## Email Configuration

Set these environment variables before using the email feature:

```bash
set SMTP_HOST=smtp.gmail.com
set SMTP_PORT=587
set SMTP_USER=your_email@gmail.com
set SMTP_PASS=your_app_password
```

## Testing

Run the test suite:

```bash
python test_cases.py
```

Or use the Test Cases tab within the application.

## License

For internal use.
