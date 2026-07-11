"""Transparent market scoring used by both pages."""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.constants import HIRING_TREND_RISK


def _latest_momentum(df: pd.DataFrame, group_col: str | None = None) -> pd.DataFrame:
    groups = ([group_col] if group_col else []) + ["period_order"]
    quarterly = df.groupby(groups, observed=True)["open_roles"].sum().reset_index().sort_values(groups)
    if group_col:
        quarterly["open_role_change_pct"] = quarterly.groupby(group_col, observed=True)["open_roles"].pct_change() * 100
        return quarterly.groupby(group_col, observed=True).tail(1)[[group_col, "open_role_change_pct"]]
    quarterly["open_role_change_pct"] = quarterly["open_roles"].pct_change() * 100
    return quarterly.tail(1)[["open_role_change_pct"]]


def quarterly_market(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    trend_order = ["Downsizing", "Hiring Freeze", "Moderate Hiring", "Aggressive Hiring"]

    def dominant(series):
        counts = series.value_counts()
        return next((name for name in trend_order if name in counts.index and counts[name] == counts.max()), counts.index[0])

    result = (
        df.groupby(["period_order", "period"], observed=True)
        .agg(
            layoffs_count=("layoffs_count", "sum"),
            open_roles=("open_roles", "sum"),
            dominant_hiring_trend=("hiring_trend", dominant),
        )
        .reset_index()
        .sort_values("period_order")
    )
    result["open_role_change"] = result["open_roles"].diff()
    result["open_role_change_pct"] = result["open_roles"].pct_change() * 100
    result["change_label"] = result["open_role_change_pct"].map(
        lambda value: "Baseline" if pd.isna(value) else f"{value:+.1f}%"
    )
    return result


def disruption_scores(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    columns = [
        group_col,
        "layoffs_count",
        "layoff_percentage",
        "open_roles",
        "ai_replacement_risk",
        "ai_automation_impact",
        "ai_adoption_level",
        "hiring_trend_risk",
        "open_role_change_pct",
        "disruption_index",
    ]
    if df.empty:
        return pd.DataFrame(columns=columns)
    working = df.assign(hiring_trend_risk=df["hiring_trend"].map(HIRING_TREND_RISK).fillna(0.5))
    result = (
        working.groupby(group_col, observed=True)
        .agg(
            layoffs_count=("layoffs_count", "sum"),
            layoff_percentage=("layoff_percentage", "mean"),
            open_roles=("open_roles", "sum"),
            ai_replacement_risk=("ai_replacement_risk", "mean"),
            ai_automation_impact=("ai_automation_impact", "mean"),
            ai_adoption_level=("ai_adoption_level", "mean"),
            hiring_trend_risk=("hiring_trend_risk", "mean"),
        )
        .reset_index()
    )
    result = result.merge(_latest_momentum(working, group_col), on=group_col, how="left")
    result["momentum_risk"] = (-result["open_role_change_pct"].fillna(0) / 50).clip(0, 1)
    result["replacement_component"] = ((result["ai_replacement_risk"] - 1) / 9).clip(0, 1)
    result["automation_component"] = (result["ai_automation_impact"] / 20).clip(0, 1)
    result["adoption_component"] = ((result["ai_adoption_level"] - 1) / 9).clip(0, 1)
    result["disruption_index"] = 100 * (
        0.40 * result["replacement_component"]
        + 0.30 * result["automation_component"]
        + 0.30 * result["adoption_component"]
    )
    result["disruption_index"] = result["disruption_index"].clip(0, 100).round(1)
    return result


def recommendation_scores(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    result = (
        df.groupby(["company_name", "country", "industry_norm"], observed=True)
        .agg(
            open_roles=("open_roles", "sum"),
            layoffs=("layoffs_count", "sum"),
            layoff_percentage=("layoff_percentage", "mean"),
            remote_share=("remote_jobs_percentage", "mean"),
            sentiment=("employee_sentiment", "mean"),
            job_security=("job_security_score", "mean"),
            ai_risk=("ai_replacement_risk", "mean"),
            salary_budget_change=("salary_budget_change", "mean"),
        )
        .reset_index()
    )
    company_momentum = _latest_momentum(df, "company_name")
    result = result.merge(company_momentum, on="company_name", how="left")
    disruption = disruption_scores(df, "company_name")[["company_name", "disruption_index"]]
    result = result.merge(disruption, on="company_name", how="left")

    demand_span = result["open_roles"].max() - result["open_roles"].min()
    result["demand_score"] = 1.0 if demand_span == 0 else (result["open_roles"] - result["open_roles"].min()) / demand_span
    result["recommendation_score"] = 100 * (
        0.30 * result["demand_score"]
        + 0.20 * (result["job_security"] / 10).clip(0, 1)
        + 0.15 * (result["sentiment"] / 10).clip(0, 1)
        + 0.10 * (result["remote_share"] / 100).clip(0, 1)
        + 0.10 * (result["salary_budget_change"].clip(lower=0) / 40).clip(0, 1)
        + 0.10 * (1 - ((result["ai_risk"] - 1) / 9).clip(0, 1))
        + 0.05 * (1 - (result["layoff_percentage"] / 40).clip(0, 1))
    )
    result["recommendation_score"] = result["recommendation_score"].clip(0, 100).round(1)
    result["open_role_change_pct"] = result["open_role_change_pct"].replace([np.inf, -np.inf], np.nan).round(1)
    return result.sort_values(["recommendation_score", "open_roles"], ascending=False)
