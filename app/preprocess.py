"""Clean the two source CSVs and build safe, aggregated Parquet assets."""

from __future__ import annotations

import json

import pandas as pd

from app.constants import (
    APP_YEARS,
    BRIDGE_PARQUET,
    COUNTRY_TO_ISO3,
    COUNTRY_TO_REGION,
    INDUSTRY_NORMALIZATION,
    LAYOFFS_FILE,
    LAYOFFS_PARQUET,
    MONTH_ORDER,
    NUMERIC_LAYOFF_COLUMNS,
    NUMERIC_WORKFORCE_COLUMNS,
    PROFILE_FILE,
    PROCESSED_DIR,
    WORKFORCE_FILE,
    WORKFORCE_PARQUET,
)


def _clean_workforce() -> pd.DataFrame:
    if not WORKFORCE_FILE.exists():
        raise FileNotFoundError(f"Missing workforce dataset: {WORKFORCE_FILE}")

    df = pd.read_csv(WORKFORCE_FILE)
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df = df[df["year"].isin(APP_YEARS)].copy()
    df["quarter_num"] = pd.to_numeric(
        df["quarter"].astype(str).str.extract(r"Q(\d)", expand=False), errors="coerce"
    ).astype("Int64")
    df["industry_norm"] = df["industry"].map(INDUSTRY_NORMALIZATION).fillna(df["industry"])
    df["period"] = df["year"].astype(str) + " " + df["quarter"]
    df["period_order"] = df["year"] * 10 + df["quarter_num"]
    df["net_workforce_change"] = df["employees_hired"] - df["layoffs"]

    for column in NUMERIC_WORKFORCE_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    return df


def _clean_layoffs() -> pd.DataFrame:
    if not LAYOFFS_FILE.exists():
        raise FileNotFoundError(f"Missing layoffs dataset: {LAYOFFS_FILE}")

    df = pd.read_csv(LAYOFFS_FILE)
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df = df[df["year"].isin(APP_YEARS)].copy()
    df["month_num"] = df["month"].map(MONTH_ORDER).astype("Int64")
    df["quarter_num"] = ((df["month_num"] - 1) // 3 + 1).astype("Int64")
    df["quarter"] = "Q" + df["quarter_num"].astype(str)
    df["region"] = df["country"].map(COUNTRY_TO_REGION).fillna("Other")
    df["iso_alpha"] = df["country"].map(COUNTRY_TO_ISO3)
    df["industry_norm"] = df["industry"].map(INDUSTRY_NORMALIZATION).fillna(df["industry"])
    df["period"] = df["year"].astype(str) + " " + df["quarter"]
    df["period_order"] = df["year"] * 10 + df["quarter_num"]

    for column in NUMERIC_LAYOFF_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    return df


def _build_bridge(workforce: pd.DataFrame, layoffs: pd.DataFrame) -> pd.DataFrame:
    """Join aggregates only; never connect the disjoint company dimensions."""
    keys = ["year", "quarter", "quarter_num", "period", "period_order", "industry_norm", "region"]
    wf = (
        workforce.groupby(keys, observed=True)
        .agg(
            employees_hired=("employees_hired", "sum"),
            workforce_layoffs=("layoffs", "sum"),
            employee_satisfaction=("employee_satisfaction", "mean"),
            satisfaction_n=("employee_satisfaction", "count"),
            avg_salary=("avg_salary", "mean"),
            salary_n=("avg_salary", "count"),
            ai_adoption_score=("ai_adoption_score", "mean"),
            automation_level=("automation_level", "mean"),
            attrition_rate=("attrition_rate", "mean"),
            layoff_risk_score=("layoff_risk_score", "mean"),
        )
        .reset_index()
    )
    lf = (
        layoffs.groupby(keys, observed=True)
        .agg(
            layoffs_count=("layoffs_count", "sum"),
            layoff_percentage=("layoff_percentage", "mean"),
            open_roles=("open_roles", "sum"),
            remote_jobs_percentage=("remote_jobs_percentage", "mean"),
            employee_sentiment=("employee_sentiment", "mean"),
            job_security_score=("job_security_score", "mean"),
            ai_replacement_risk=("ai_replacement_risk", "mean"),
            ai_automation_impact=("ai_automation_impact", "mean"),
        )
        .reset_index()
    )
    return wf.merge(lf, on=keys, how="inner", validate="one_to_one")


def build_processed_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    workforce = _clean_workforce()
    layoffs = _clean_layoffs()
    bridge = _build_bridge(workforce, layoffs)

    workforce.to_parquet(WORKFORCE_PARQUET, index=False)
    layoffs.to_parquet(LAYOFFS_PARQUET, index=False)
    bridge.to_parquet(BRIDGE_PARQUET, index=False)

    profile = {
        "workforce_rows": int(len(workforce)),
        "layoffs_rows": int(len(layoffs)),
        "bridge_rows": int(len(bridge)),
        "years": APP_YEARS,
        "quarters": ["Q1", "Q2", "Q3", "Q4"],
        "industries": sorted(set(workforce["industry_norm"].dropna()) | set(layoffs["industry_norm"].dropna())),
        "regions": sorted(workforce["region"].dropna().unique().tolist()),
        "countries": sorted(layoffs["country"].dropna().unique().tolist()),
        "roles": sorted(layoffs["top_hiring_role"].dropna().unique().tolist()),
        "companies": sorted(layoffs["company_name"].dropna().unique().tolist()),
        "company_sizes": sorted(layoffs["company_size"].dropna().unique().tolist()),
        "hiring_trends": sorted(layoffs["hiring_trend"].dropna().unique().tolist()),
        "salary_min": float(workforce["avg_salary"].min()),
        "salary_max": float(workforce["avg_salary"].max()),
        "missing": {
            "avg_salary": int(workforce["avg_salary"].isna().sum()),
            "employee_satisfaction": int(workforce["employee_satisfaction"].isna().sum()),
            "revenue_growth": int(workforce["revenue_growth"].isna().sum()),
        },
    }
    PROFILE_FILE.write_text(json.dumps(profile, indent=2), encoding="utf-8")
    return workforce, layoffs, bridge


if __name__ == "__main__":
    wf, lf, bridge_df = build_processed_data()
    print(f"Wrote {len(wf):,} workforce rows, {len(lf):,} market rows, and {len(bridge_df):,} bridge rows.")
