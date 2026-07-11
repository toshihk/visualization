"""Cached data access and shared filter helpers."""

from __future__ import annotations

import json
from functools import lru_cache

import pandas as pd

from app.constants import BRIDGE_CSV, LAYOFFS_CSV, PROFILE_FILE, WORKFORCE_CSV


class ProcessedDataMissingError(FileNotFoundError):
    pass


def _read(path):
    paths = [path] if path.exists() else sorted(path.parent.glob(f"{path.stem}_part*.csv"))
    if not paths:
        raise ProcessedDataMissingError("Run `python -m app.preprocess` first.")
    return pd.concat((pd.read_csv(part) for part in paths), ignore_index=True) if len(paths) > 1 else pd.read_csv(paths[0])


@lru_cache(maxsize=1)
def load_workforce() -> pd.DataFrame:
    return _read(WORKFORCE_CSV)


@lru_cache(maxsize=1)
def load_layoffs() -> pd.DataFrame:
    return _read(LAYOFFS_CSV)


@lru_cache(maxsize=1)
def load_bridge() -> pd.DataFrame:
    return _read(BRIDGE_CSV)


@lru_cache(maxsize=1)
def load_profile() -> dict:
    return json.loads(PROFILE_FILE.read_text(encoding="utf-8")) if PROFILE_FILE.exists() else {}


def dropdown_options(values) -> list[dict]:
    return [{"label": str(value), "value": value} for value in sorted(v for v in values if pd.notna(v))]


def _years(df: pd.DataFrame, years) -> pd.DataFrame:
    if years and len(years) == 2:
        return df[df["year"].between(min(years), max(years))]
    return df


def _periods(df: pd.DataFrame, period_range) -> pd.DataFrame:
    if period_range and len(period_range) == 2:
        period_index = (df["year"] - 2024) * 4 + df["quarter_num"] - 1
        return df[period_index.between(min(period_range), max(period_range))]
    return df


def filter_workforce(df, years=None, quarters=None, period_range=None, industries=None, regions=None, salary_range=None):
    out = _periods(_years(df, years), period_range)
    for column, values in [("quarter", quarters), ("industry_norm", industries), ("region", regions)]:
        if values:
            out = out[out[column].isin(values)]
    if salary_range and len(salary_range) == 2:
        out = out[out["avg_salary"].between(*salary_range) | out["avg_salary"].isna()]
    return out


def filter_layoffs(
    df,
    years=None,
    quarters=None,
    period_range=None,
    industries=None,
    countries=None,
    role=None,
    company_sizes=None,
    hiring_trends=None,
    min_sentiment=0,
    min_security=0,
    min_remote=0,
    max_layoff=40,
    max_ai_risk=10,
):
    out = _periods(_years(df, years), period_range)
    for column, values in [
        ("quarter", quarters),
        ("industry_norm", industries),
        ("country", countries),
        ("company_size", company_sizes),
        ("hiring_trend", hiring_trends),
    ]:
        if values:
            out = out[out[column].isin(values)]
    if role:
        out = out[out["top_hiring_role"] == role]
    return out[
        (out["employee_sentiment"] >= (min_sentiment or 0))
        & (out["job_security_score"] >= (min_security or 0))
        & (out["remote_jobs_percentage"] >= (min_remote or 0))
        & (out["layoff_percentage"] <= (40 if max_layoff is None else max_layoff))
        & (out["ai_replacement_risk"] <= (10 if max_ai_risk is None else max_ai_risk))
    ]


def filter_bridge(df, years=None, quarters=None, period_range=None, industries=None, regions=None):
    out = _periods(_years(df, years), period_range)
    for column, values in [("quarter", quarters), ("industry_norm", industries), ("region", regions)]:
        if values:
            out = out[out[column].isin(values)]
    return out
