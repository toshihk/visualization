import numpy as np
import pandas as pd


def pearson_r(df: pd.DataFrame, x: str, y: str) -> tuple[float | None, int]:
    clean = df[[x, y]].replace([np.inf, -np.inf], np.nan).dropna()
    if len(clean) < 3 or clean[x].nunique() < 2 or clean[y].nunique() < 2:
        return None, int(len(clean))
    return float(clean[x].corr(clean[y])), int(len(clean))


def anova_summary(df: pd.DataFrame, category: str, value: str) -> dict:
    clean = df[[category, value]].dropna()
    groups = [group[value].to_numpy() for _, group in clean.groupby(category) if len(group) > 1]
    if len(groups) < 2:
        return {"f": None, "eta_squared": None, "groups": []}

    grand_mean = clean[value].mean()
    ss_between = sum(len(group) * (group.mean() - grand_mean) ** 2 for group in groups)
    ss_total = ((clean[value] - grand_mean) ** 2).sum()
    df_between = len(groups) - 1
    df_within = len(clean) - len(groups)
    ss_within = ss_total - ss_between
    f_value = (ss_between / df_between) / (ss_within / df_within) if df_within and ss_within else None
    eta_squared = ss_between / ss_total if ss_total else None

    grouped = (
        clean.groupby(category)[value]
        .agg(["mean", "count"])
        .reset_index()
        .sort_values("mean", ascending=False)
    )
    return {
        "f": float(f_value) if f_value is not None else None,
        "eta_squared": float(eta_squared) if eta_squared is not None else None,
        "groups": grouped.to_dict("records"),
    }

