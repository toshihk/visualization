from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
PROCESSED_DIR = ROOT_DIR / "processed"

WORKFORCE_FILE = DATA_DIR / "ai_workforce_transformation.csv"
LAYOFFS_FILE = DATA_DIR / "tech_layoffs_hiring_trends_elite_v2.csv"

WORKFORCE_CSV = PROCESSED_DIR / "workforce_clean.csv"
LAYOFFS_CSV = PROCESSED_DIR / "layoffs_clean.csv"
BRIDGE_CSV = PROCESSED_DIR / "workforce_layoffs_bridge.csv"
PROFILE_FILE = PROCESSED_DIR / "data_profile.json"

APP_YEARS = [2024, 2025, 2026]
APP_QUARTERS = ["Q1", "Q2", "Q3", "Q4"]
APP_PERIODS = [f"{year} {quarter}" for year in APP_YEARS for quarter in APP_QUARTERS]
PERIOD_MARKS = {index: label.replace("20", "", 1) for index, label in enumerate(APP_PERIODS)}

COLORS = {
    "opportunity": "#16a36a",
    "opportunity_dark": "#087a50",
    "transition": "#f1a72f",
    "disruption": "#e05252",
    "disruption_dark": "#b8323c",
    "context": "#2f6fed",
    "context_dark": "#1f4fa6",
    "ink": "#172033",
    "muted": "#667085",
    "grid": "#e8edf4",
}


COUNTRY_TO_REGION = {
    "USA": "North America",
    "Canada": "North America",
    "UK": "Europe",
    "Germany": "Europe",
    "India": "Asia-Pacific",
    "Singapore": "Asia-Pacific",
}

COUNTRY_TO_ISO3 = {
    "USA": "USA",
    "Canada": "CAN",
    "UK": "GBR",
    "Germany": "DEU",
    "India": "IND",
    "Singapore": "SGP",
}

INDUSTRY_NORMALIZATION = {
    "Cloud Computing": "Cloud",
    "Cloud": "Cloud",
    "AI": "AI",
    "Cybersecurity": "Cybersecurity",
    "E-Commerce": "E-Commerce",
    "FinTech": "FinTech",
    "Gaming": "Gaming",
    "Software": "Software",
    "Data Analytics": "Data Analytics",
    "Social Media": "Social Media",
}

MONTH_ORDER = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}

NUMERIC_WORKFORCE_COLUMNS = [
    "inflation_rate",
    "interest_rate",
    "gdp_growth",
    "ai_adoption_score",
    "automation_level",
    "employees_hired",
    "layoffs",
    "attrition_rate",
    "employee_satisfaction",
    "avg_salary",
    "revenue_growth",
    "stock_growth",
    "productivity_index",
    "innovation_score",
    "layoff_risk_score",
]

NUMERIC_LAYOFF_COLUMNS = [
    "layoffs_count",
    "layoff_percentage",
    "ai_automation_impact",
    "ai_replacement_risk",
    "open_roles",
    "remote_jobs_percentage",
    "stock_growth_percent",
    "revenue_growth_percent",
    "salary_budget_change",
    "ai_adoption_level",
    "employee_sentiment",
    "job_security_score",
]

METRIC_OPTIONS = {
    "layoffs_count": "Layoffs",
    "open_roles": "Open roles",
    "layoff_percentage": "Layoff %",
    "ai_replacement_risk": "AI replacement risk",
    "remote_jobs_percentage": "Remote jobs %",
    "employee_sentiment": "Employee sentiment",
    "job_security_score": "Job security score",
}

HIRING_TREND_RISK = {
    "Aggressive Hiring": 0.0,
    "Moderate Hiring": 0.25,
    "Hiring Freeze": 0.75,
    "Downsizing": 1.0,
}

DEFAULT_JOURNEY = {
    "period_range": [0, len(APP_PERIODS) - 1],
    "years": [2024, 2026],
    "quarters": APP_QUARTERS,
    "countries": [],
    "regions": [],
    "industries": [],
    "selected_role": None,
    "map_metric": "open_roles",
}

CORRELATION_PAIRS = [
    {
        "theme": "Macroeconomics vs Corporate Strategy",
        "dataset": "bridge",
        "x": "interest_rate",
        "y": "layoffs_count",
        "title": "Interest rate vs layoffs",
        "note": "Tests whether tighter capital markets align with workforce reductions.",
    },
    {
        "theme": "Macroeconomics vs Corporate Strategy",
        "dataset": "bridge",
        "x": "gdp_growth",
        "y": "revenue_growth_percent",
        "title": "GDP growth vs revenue growth",
        "note": "Checks whether industry revenue tracks broader economic health.",
    },
    {
        "theme": "Technology vs Workforce Size",
        "dataset": "bridge",
        "x": "ai_adoption_score",
        "y": "layoffs_count",
        "title": "AI adoption vs layoffs",
        "note": "Looks for evidence of automation pressure on workforce size.",
    },
    {
        "theme": "Technology vs Workforce Size",
        "dataset": "bridge",
        "x": "automation_level",
        "y": "open_roles",
        "title": "Automation level vs open roles",
        "note": "Tests whether automation coincides with hiring demand.",
    },
    {
        "theme": "Technology vs Workforce Size",
        "dataset": "workforce",
        "x": "automation_level",
        "y": "productivity_index",
        "title": "Automation level vs productivity",
        "note": "Validates whether modernization translates into output efficiency.",
    },
    {
        "theme": "Workplace Environment vs Retention",
        "dataset": "workforce",
        "x": "avg_salary",
        "y": "attrition_rate",
        "title": "Average salary vs attrition",
        "note": "Tests whether pay alone appears to reduce employee departures.",
    },
    {
        "theme": "Human Capital vs Business Success",
        "dataset": "workforce",
        "x": "employee_satisfaction",
        "y": "productivity_index",
        "title": "Employee satisfaction vs productivity",
        "note": "Tests the happy-worker productivity hypothesis.",
    },
    {
        "theme": "Human Capital vs Business Success",
        "dataset": "workforce",
        "x": "employee_satisfaction",
        "y": "innovation_score",
        "title": "Employee satisfaction vs innovation",
        "note": "Checks whether morale aligns with stronger innovation scores.",
    },
    {
        "theme": "Human Capital vs Business Success",
        "dataset": "bridge",
        "x": "layoffs_count",
        "y": "stock_growth_percent",
        "title": "Layoffs vs stock growth",
        "note": "Explores whether markets reward or punish downsizing.",
    },
    {
        "theme": "Risk Modeling",
        "dataset": "workforce",
        "x": "revenue_growth",
        "y": "layoff_risk_score",
        "title": "Revenue growth vs layoff risk",
        "note": "Shows whether weak growth coincides with higher layoff risk.",
    },
    {
        "theme": "Risk Modeling",
        "dataset": "workforce",
        "x": "inflation_rate",
        "y": "layoff_risk_score",
        "title": "Inflation vs layoff risk",
        "note": "Shows whether external cost pressure appears in risk scores.",
    },
]

WORK_MODEL_TESTS = [
    ("work_model", "employee_satisfaction", "Work model vs employee satisfaction"),
    ("work_model", "attrition_rate", "Work model vs attrition rate"),
]
