"""Plotly figures for the two-page job-seeker journey."""

from __future__ import annotations

from collections import Counter

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from app.constants import COLORS, COUNTRY_TO_REGION, METRIC_OPTIONS
from app.scoring import disruption_scores, quarterly_market, recommendation_scores


PLOT_LAYOUT = {
    "template": "plotly_white",
    "font": {"family": "Inter, system-ui, sans-serif", "color": COLORS["ink"]},
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "margin": {"l": 48, "r": 24, "t": 68, "b": 48},
    "hoverlabel": {"bgcolor": "white", "font_size": 13},
}


def _style(fig: go.Figure, title: str) -> go.Figure:
    fig.update_layout(**PLOT_LAYOUT, title={"text": title, "x": 0.02, "xanchor": "left"}, legend_title_text="")
    fig.update_xaxes(gridcolor=COLORS["grid"], zeroline=False)
    fig.update_yaxes(gridcolor=COLORS["grid"], zeroline=False)
    return fig


def empty_figure(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False, font={"size": 16, "color": COLORS["muted"]})
    fig.update_layout(**PLOT_LAYOUT, xaxis={"visible": False}, yaxis={"visible": False})
    return fig


def country_map(df: pd.DataFrame, metric: str, selected_countries: list[str] | None = None) -> go.Figure:
    if df.empty:
        return empty_figure("No covered-market data matches these filters")
    aggregation = "sum" if metric in {"layoffs_count", "open_roles"} else "mean"
    grouped = df.groupby(["country", "region", "iso_alpha"], observed=True)[metric].agg(aggregation).reset_index(name="value")
    selected = set(selected_countries or [])
    zmin, zmax = float(grouped["value"].min()), float(grouped["value"].max())
    colorscale = [[0, "#dbeafe"], [0.45, "#60a5fa"], [1, COLORS["context"]]]
    hovertemplate = (
        "<b>%{customdata[0]}</b><br>Region: %{customdata[1]}<br>"
        + METRIC_OPTIONS.get(metric, metric)
        + ": %{z:,.1f}<extra></extra>"
    )
    fig = go.Figure()
    selectedpoints = [index for index, country in enumerate(grouped["country"]) if country in selected] if selected else None
    fig.add_trace(go.Choropleth(
        locations=grouped["iso_alpha"],
        z=grouped["value"],
        zmin=zmin,
        zmax=zmax,
        customdata=np.column_stack([grouped["country"], grouped["region"]]),
        colorscale=colorscale,
        marker_line_color="white",
        marker_line_width=0.8,
        colorbar_title=METRIC_OPTIONS.get(metric, metric),
        selectedpoints=selectedpoints,
        selected={"marker": {"opacity": 1.0}},
        unselected={"marker": {"opacity": 0.18}},
        hovertemplate=hovertemplate,
    ))
    fig.update_geos(showframe=False, showcoastlines=True, coastlinecolor="#cbd5e1", projection_type="natural earth", bgcolor="rgba(0,0,0,0)", fitbounds="locations", lataxis_range=[-5, 75])
    fig.update_layout(dragmode=False, uirevision="locked-covered-markets")
    fig.add_annotation(text="Click a country to select it", x=0.01, y=0.01, xref="paper", yref="paper", showarrow=False, font={"size": 11, "color": COLORS["muted"]}, bgcolor="rgba(255,255,255,.85)")
    fig = _style(fig, "")
    fig.update_layout(height=370, margin={"l": 15, "r": 25, "t": 12, "b": 20})
    return fig


def opportunity_timeline(df: pd.DataFrame, selected_df: pd.DataFrame | None = None) -> go.Figure:
    market = quarterly_market(df)
    if market.empty:
        return empty_figure("No quarterly market data matches these filters")
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    use_brush = selected_df is not None and not selected_df.empty
    if use_brush:
        selected_market = quarterly_market(selected_df).set_index("period").reindex(market["period"]).reset_index()
        selected_open_roles = selected_market["open_roles"]
        selected_layoffs = selected_market["layoffs_count"]
        selected_open_roles_for_math = selected_open_roles.fillna(0)
        selected_layoffs_for_math = selected_layoffs.fillna(0)
        other_open_roles = np.clip(market["open_roles"].to_numpy() - selected_open_roles_for_math.to_numpy(), 0, None)
        other_layoffs = np.clip(market["layoffs_count"].to_numpy() - selected_layoffs_for_math.to_numpy(), 0, None)
        fig.add_trace(go.Bar(
            x=selected_market["period"],
            y=selected_open_roles,
            name="Open roles",
            marker={"color": "#a7f3d0", "line": {"color": COLORS["opportunity_dark"], "width": 2}},
            hovertemplate="%{x}<br>Open roles: %{y:,.0f}<extra></extra>",
        ), secondary_y=False)
        fig.add_trace(go.Bar(
            x=market["period"],
            y=other_open_roles,
            name="Open roles",
            marker={"color": "rgba(151, 163, 185, .28)", "line": {"color": "rgba(151, 163, 185, .38)", "width": 1}},
            hovertemplate="%{x}<br>Open roles: %{y:,.0f}<extra></extra>",
        ), secondary_y=False)
        fig.add_trace(go.Scatter(
            x=market["period"],
            y=other_layoffs,
            name="Layoffs",
            mode="lines+markers",
            line={"color": "rgba(151, 163, 185, .45)", "width": 3, "dash": "dot"},
            marker={"size": 7, "color": "rgba(151, 163, 185, .45)", "line": {"color": "white", "width": 1}},
            hovertemplate="%{x}<br>Layoffs: %{y:,.0f}<extra></extra>",
        ), secondary_y=True)
        fig.add_trace(go.Scatter(
            x=selected_market["period"],
            y=selected_layoffs,
            name="Layoffs",
            mode="lines+markers",
            line={"color": COLORS["context_dark"], "width": 4},
            marker={"size": 9, "color": COLORS["context_dark"], "line": {"color": "white", "width": 1.5}},
            hovertemplate="%{x}<br>Layoffs: %{y:,.0f}<extra></extra>",
        ), secondary_y=True)
    else:
        fig.add_trace(go.Bar(x=market["period"], y=market["open_roles"], name="Open roles", marker={"color": "#d9f2e6", "line": {"color": COLORS["opportunity_dark"], "width": 2}}, opacity=0.95, customdata=market["dominant_hiring_trend"], hovertemplate="%{x}<br>Open roles: %{y:,.0f}<br>Dominant hiring trend: %{customdata}<extra></extra>"), secondary_y=False)
        fig.add_trace(go.Scatter(x=market["period"], y=market["layoffs_count"], name="Layoffs", mode="lines+markers", line={"color": COLORS["context_dark"], "width": 4}, marker={"size": 9, "color": COLORS["context_dark"], "line": {"color": "white", "width": 1.5}}, hovertemplate="%{x}<br>People laid off: %{y:,.0f}<extra></extra>"), secondary_y=True)
    fig.update_yaxes(title_text="Open roles", secondary_y=False)
    fig.update_yaxes(title_text="People laid off", secondary_y=True, showgrid=False)
    fig = _style(fig, "Hiring demand and layoffs over time")
    fig.update_layout(barmode="stack", height=350, showlegend=not use_brush, legend={"orientation": "h", "yanchor": "bottom", "y": 1.01, "xanchor": "right", "x": 1, "font": {"size": 10}}, hovermode="x unified", margin={"l": 58, "r": 58, "t": 65, "b": 55})
    return fig


def open_role_momentum(df: pd.DataFrame, selected_df: pd.DataFrame | None = None) -> go.Figure:
    market = quarterly_market(df)
    if market.empty:
        return empty_figure("No open-role change data matches these filters")
    momentum_colors = [COLORS["muted"] if pd.isna(value) else COLORS["opportunity"] if value >= 0 else COLORS["disruption"] for value in market["open_role_change_pct"]]
    fig = go.Figure()
    use_brush = selected_df is not None and not selected_df.empty
    if use_brush:
        fig.add_trace(go.Bar(
            x=market["period"],
            y=market["open_role_change_pct"].fillna(0),
            name="Open-role change",
            marker={"color": "rgba(151, 163, 185, .35)", "line": {"color": "rgba(151, 163, 185, .45)", "width": 1}},
            hovertemplate="%{x}<br>Open-role change: %{y:+.1f}%<extra></extra>",
        ))
        selected_market = quarterly_market(selected_df).set_index("period").reindex(market["period"]).reset_index()
        selected_colors = [COLORS["muted"] if pd.isna(value) else COLORS["opportunity"] if value >= 0 else COLORS["disruption"] for value in selected_market["open_role_change_pct"]]
        fig.add_trace(go.Bar(
            x=selected_market["period"],
            y=selected_market["open_role_change_pct"],
            name="Open-role change",
            marker={"color": selected_colors, "line": {"color": "rgba(31,41,55,.24)", "width": 0.8}},
            text=selected_market["open_role_change_pct"].map(lambda value: "" if pd.isna(value) else f"{value:+.1f}%"),
            textposition="outside",
            textfont={"size": 15, "color": COLORS["ink"]},
            hovertemplate="%{x}<br>Open-role change: %{y:+.1f}%<extra></extra>",
        ))
    else:
        fig.add_trace(go.Bar(
            x=market["period"],
            y=market["open_role_change_pct"].fillna(0),
            name="Open-role change",
            marker_color=momentum_colors,
            text=market["change_label"],
            textposition="outside",
            textfont={"size": 15, "color": COLORS["ink"]},
            customdata=np.column_stack([market["open_role_change"], market["dominant_hiring_trend"]]),
            hovertemplate="%{x}<br>Open-role change: %{customdata[0]:+,.0f} (%{y:+.1f}%)<br>Dominant hiring trend: %{customdata[1]}<extra></extra>",
        ))
    fig.add_hline(y=0, line_color="#98a2b3", line_width=1)
    fig.update_xaxes(tickfont={"size": 12})
    fig.update_yaxes(title_text="Change in open roles (%)", ticksuffix="%", tickfont={"size": 12})
    fig = _style(fig, "Quarterly change in open roles")
    fig.update_layout(barmode="overlay" if use_brush else "relative", height=350, showlegend=False, legend={"orientation": "h", "yanchor": "bottom", "y": 1.01, "xanchor": "right", "x": 1, "font": {"size": 9}}, margin={"l": 58, "r": 20, "t": 65, "b": 55})
    return fig


def top_roles(df: pd.DataFrame, selected_role: str | None = None) -> go.Figure:
    if df.empty:
        return empty_figure("No role demand matches these filters")
    grouped = df.groupby(["top_hiring_role", "country"], observed=True)["open_roles"].sum().reset_index()
    order = grouped.groupby("top_hiring_role")["open_roles"].sum().sort_values(ascending=False).index.tolist()
    fig = px.bar(grouped, x="open_roles", y="top_hiring_role", color="country", orientation="h", category_orders={"top_hiring_role": order}, labels={"open_roles": "Open roles", "top_hiring_role": "", "country": "Country"}, color_discrete_sequence=px.colors.qualitative.Safe)
    for trace in fig.data:
        trace.marker.opacity = [1.0 if not selected_role or role == selected_role else 0.18 for role in trace.y]
        trace.hovertemplate = "<b>%{y}</b><br>Open roles: %{x:,.0f}<br>Country: %{fullData.name}<extra></extra>"
    fig.update_layout(barmode="stack")
    fig.update_yaxes(categoryorder="array", categoryarray=order, autorange="reversed")
    fig = _style(fig, "Top roles in demand")
    fig.update_layout(height=230, legend={"orientation": "h", "yanchor": "top", "y": -0.22, "font": {"size": 8}}, margin={"l": 115, "r": 15, "t": 45, "b": 58})
    return fig


def role_vs_industry(
    df: pd.DataFrame,
    selected_role: str | None = None,
    selected_industries: list[str] | None = None,
) -> go.Figure:
    """Compare open-role demand by industry using shared role colors."""
    if df.empty:
        return empty_figure("No industry hiring data matches these filters")

    hiring = df.groupby(["industry_norm", "top_hiring_role"], observed=True)["open_roles"].sum().reset_index()
    industry_order = (
        hiring.groupby("industry_norm", observed=True)["open_roles"]
        .sum()
        .sort_values(ascending=False)
        .index.tolist()
    )
    role_order = hiring.groupby("top_hiring_role", observed=True)["open_roles"].sum().sort_values(ascending=False).index.tolist()
    selected = set(selected_industries or [])
    palette = px.colors.qualitative.Safe
    fig = go.Figure()
    for index, role in enumerate(role_order):
        subset = hiring[hiring["top_hiring_role"] == role].set_index("industry_norm").reindex(industry_order).reset_index()
        fig.add_trace(go.Bar(
            x=subset["open_roles"].fillna(0), y=subset["industry_norm"], name=role,
            legendgroup=role, showlegend=False, orientation="h",
            marker={"color": palette[index % len(palette)], "line": {"color": "rgba(31,41,55,.35)", "width": 0.5}, "opacity": [1.0 if not selected or industry in selected else 0.16 for industry in subset["industry_norm"]]},
            hovertemplate="<b>%{y}</b><br>Job role: " + role + "<br>Open roles: %{x:,.0f}<extra></extra>",
        ))

    hiring_totals = hiring.groupby("industry_norm", observed=True)["open_roles"].sum()
    max_total = float(hiring_totals.max()) if not hiring_totals.empty else 1_000_000
    max_tick = max(1_000_000, np.ceil(max_total / 1_000_000) * 1_000_000)
    tickvals = np.arange(0, max_tick + 1, 1_000_000)
    ticktext = ["0" if value == 0 else f"{int(value / 1_000_000)}M" for value in tickvals]
    fig.update_yaxes(categoryorder="array", categoryarray=industry_order, autorange="reversed", tickfont={"size": 9}, gridcolor="#eef2f6")
    fig.update_xaxes(range=[0, max_tick * 1.04], tickmode="array", tickvals=tickvals, ticktext=ticktext, title_text="Open roles")
    fig = _style(fig, "<b>Top industries in demand</b><br><sup>Open roles by job role</sup>")
    fig.update_layout(
        barmode="stack",
        bargap=0.46,
        legend={
            "orientation": "h",
            "yanchor": "top",
            "y": -0.22,
            "xanchor": "left",
            "x": 0,
            "font": {"size": 8},
            "entrywidth": 86,
            "entrywidthmode": "pixels",
            "tracegroupgap": 2,
        },
        height=210,
        showlegend=False,
        margin={"l": 82, "r": 22, "t": 58, "b": 72},
    )
    return fig


def industry_layoffs_bar(df: pd.DataFrame, selected_industries: list[str] | None = None) -> go.Figure:
    if df.empty:
        return empty_figure("No industry layoff data matches these filters")
    open_order = df.groupby("industry_norm", observed=True)["open_roles"].sum().sort_values(ascending=False).index.tolist()
    open_totals = df.groupby("industry_norm", observed=True)["open_roles"].sum().reindex(open_order).fillna(0)
    layoffs = df.groupby(["industry_norm", "top_hiring_role"], observed=True)["layoffs_count"].sum().reset_index()
    role_order = df.groupby("top_hiring_role", observed=True)["open_roles"].sum().sort_values(ascending=False).index.tolist()
    selected = set(selected_industries or [])
    layoff_totals = layoffs.groupby("industry_norm", observed=True)["layoffs_count"].sum().reindex(open_order).fillna(0)
    max_total = float(max(open_totals.max(), layoff_totals.max())) if not layoff_totals.empty else 1_000_000
    max_tick = max(1_000_000, np.ceil(max_total / 1_000_000) * 1_000_000)
    tickvals = np.arange(0, max_tick + 1, 1_000_000)
    ticktext = ["0" if value == 0 else f"{int(value / 1_000_000)}M" for value in tickvals]
    palette = px.colors.qualitative.Safe
    fig = go.Figure()
    for index, role in enumerate(role_order):
        subset = layoffs[layoffs["top_hiring_role"] == role].set_index("industry_norm").reindex(open_order).reset_index()
        fig.add_trace(go.Bar(
            x=subset["layoffs_count"].fillna(0),
            y=subset["industry_norm"],
            name=role,
            legendgroup=role,
            showlegend=True,
            orientation="h",
            marker={
                "color": palette[index % len(palette)],
                "opacity": [1.0 if not selected or industry in selected else 0.16 for industry in subset["industry_norm"]],
                "line": {"color": "rgba(31,41,55,.25)", "width": 0.5},
            },
            hovertemplate="<b>%{y}</b><br>Job role: " + role + "<br>Layoffs: %{x:,.0f}<extra></extra>",
        ))
    fig.update_yaxes(categoryorder="array", categoryarray=open_order, autorange="reversed", tickfont={"size": 9}, gridcolor="#eef2f6")
    fig.update_xaxes(range=[0, max_tick * 1.04], tickmode="array", tickvals=tickvals, ticktext=ticktext, title_text="Layoffs")
    fig = _style(fig, "Industry layoffs")
    fig.update_layout(
        barmode="stack",
        bargap=0.46,
        height=238,
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": -1.33,
            "xanchor": "left",
            "x": 0,
            "font": {"size": 8},
            "entrywidth": 86,
            "entrywidthmode": "pixels",
            "tracegroupgap": 2,
        },
        margin={"l": 82, "r": 22, "t": 42, "b": 116},
    )
    return fig


def company_opportunity_vs_layoffs(df: pd.DataFrame, selected_company: str | None = None) -> go.Figure:
    if df.empty:
        return empty_figure("No company opportunity and layoff data matches these filters")
    roles = df.groupby(["company_name", "top_hiring_role"], observed=True)["open_roles"].sum().reset_index()
    roles["company_total"] = roles.groupby("company_name", observed=True)["open_roles"].transform("sum")
    roles["company_share"] = 100 * roles["open_roles"] / roles["company_total"]
    layoffs_by_role = df.groupby(["company_name", "top_hiring_role"], observed=True)["layoffs_count"].sum().reset_index()
    layoffs_by_role["company_total"] = layoffs_by_role.groupby("company_name", observed=True)["layoffs_count"].transform("sum")
    layoffs_by_role["company_share"] = np.where(
        layoffs_by_role["company_total"] > 0,
        100 * layoffs_by_role["layoffs_count"] / layoffs_by_role["company_total"],
        0,
    )
    layoffs = layoffs_by_role.groupby("company_name", observed=True)["layoffs_count"].sum().reset_index()
    company_order = roles.groupby("company_name", observed=True)["open_roles"].sum().sort_values(ascending=False).index.tolist()
    role_order = roles.groupby("top_hiring_role", observed=True)["open_roles"].sum().sort_values(ascending=False).index.tolist()
    layoffs = layoffs.set_index("company_name").reindex(company_order).reset_index()
    fig = go.Figure()
    palette = px.colors.qualitative.Safe

    # The source identifies the top hiring role on each record, not the role laid
    # off. The left side therefore shows layoff counts grouped by hiring-role
    # context and is labelled accordingly in the title and hover text.
    for index, role in enumerate(role_order):
        subset = layoffs_by_role[layoffs_by_role["top_hiring_role"] == role].set_index("company_name").reindex(company_order).reset_index()
        fig.add_trace(go.Bar(
            x=-subset["layoffs_count"].fillna(0),
            y=subset["company_name"],
            name=role,
            legendgroup=role,
            showlegend=False,
            orientation="h",
            marker={
                "color": palette[index % len(palette)],
                "line": {"color": "rgba(31, 41, 55, 0.35)", "width": 0.5},
                "pattern": {"shape": "/", "solidity": 0.35},
                "opacity": [1.0 if not selected_company or company == selected_company else 0.18 for company in subset["company_name"]],
            },
            customdata=np.column_stack([subset["layoffs_count"].fillna(0), subset["company_share"].fillna(0), subset["company_total"].fillna(0)]),
            hovertemplate=(
                "<b>%{y}</b><br>Recorded top hiring role: " + role
                + "<br>Layoffs in these records: %{customdata[0]:,.0f}"
                "<br>Share of company layoffs: %{customdata[1]:.1f}%"
                "<br>Company total layoffs: %{customdata[2]:,.0f}"
                "<br><i>This is hiring-role context, not the role laid off.</i><extra></extra>"
            ),
        ))

    for index, role in enumerate(role_order):
        subset = roles[roles["top_hiring_role"] == role].set_index("company_name").reindex(company_order).reset_index()
        fig.add_trace(go.Bar(
            x=subset["open_roles"].fillna(0),
            y=subset["company_name"],
            name=role,
            legendgroup=role,
            showlegend=True,
            orientation="h",
            marker={
                "color": palette[index % len(palette)],
                "line": {"color": "rgba(31, 41, 55, 0.35)", "width": 0.5},
                "opacity": [1.0 if not selected_company or company == selected_company else 0.18 for company in subset["company_name"]],
            },
            customdata=np.column_stack([subset["company_share"].fillna(0), subset["company_total"].fillna(0)]),
            hovertemplate="<b>%{y}</b><br>Role: " + role + "<br>Open roles: %{x:,.0f}<br>Share of company demand: %{customdata[0]:.1f}%<br>Company total: %{customdata[1]:,.0f}<extra></extra>",
        ))
    max_extent = float(max(layoffs["layoffs_count"].max(), roles.groupby("company_name")["open_roles"].sum().max())) * 1.08
    tickvals = np.linspace(-max_extent, max_extent, 9)
    ticktext = [f"{abs(value) / 1_000_000:.1f}M" for value in tickvals]
    fig.add_vline(x=0, line_color="#667085", line_width=1)
    for trace in fig.data:
        trace.cliponaxis = False
    fig.update_yaxes(categoryorder="array", categoryarray=company_order, autorange="reversed")
    fig.update_xaxes(range=[-max_extent, max_extent], tickmode="array", tickvals=tickvals, ticktext=ticktext, title_text="← Layoffs | Open roles →")
    fig = _style(fig, "<b>Company hiring versus layoffs by role context</b><br><sup>Left hatched: layoffs · right solid: open roles · color: recorded top hiring role</sup>")
    fig.update_layout(
        barmode="relative",
        height=460,
        legend={"orientation": "h", "yanchor": "top", "y": -0.13, "xanchor": "center", "x": 0.5, "font": {"size": 9}},
        margin={"l": 105, "r": 30, "t": 65, "b": 105},
    )
    return fig


def top_industries(df: pd.DataFrame, selected_industries: list[str] | None = None) -> go.Figure:
    scores = disruption_scores(df, "industry_norm")
    if scores.empty:
        return empty_figure("No industry demand matches these filters")
    scores = scores.sort_values("open_roles", ascending=False)
    color_min = float(scores["disruption_index"].min())
    color_max = float(scores["disruption_index"].max())
    if color_min == color_max:
        color_min, color_max = max(0, color_min - 1), min(100, color_max + 1)
    fig = px.bar(scores, x="open_roles", y="industry_norm", orientation="h", color="disruption_index", color_continuous_scale=[[0, COLORS["opportunity"]], [0.55, COLORS["transition"]], [1, COLORS["disruption"]]], range_color=[color_min, color_max], labels={"open_roles": "Open roles", "industry_norm": "", "disruption_index": "Disruption"}, custom_data=["open_role_change_pct", "layoffs_count"])
    selected = set(selected_industries or [])
    fig.update_traces(
        marker_opacity=[1.0 if not selected or industry in selected else 0.18 for industry in scores["industry_norm"]],
        hovertemplate="<b>%{y}</b><br>Open roles: %{x:,.0f}<br>Momentum: %{customdata[0]:+.1f}%<br>Layoffs: %{customdata[1]:,.0f}<extra></extra>",
    )
    fig.update_yaxes(categoryorder="array", categoryarray=scores["industry_norm"].tolist(), autorange="reversed")
    fig = _style(fig, "Industries: demand colored by disruption")
    fig.update_layout(height=230, coloraxis_colorbar={"title": {"text": f"Disruption<br>{color_min:.1f}–{color_max:.1f}"}, "thickness": 10, "len": 0.75}, margin={"l": 90, "r": 75, "t": 45, "b": 40})
    return fig


def opportunity_quadrant(df: pd.DataFrame, selected_industries: list[str] | None = None) -> go.Figure:
    scores = disruption_scores(df, "industry_norm")
    if scores.empty:
        return empty_figure("No opportunity-disruption comparison is available")
    scores["open_role_change_pct"] = scores["open_role_change_pct"].fillna(0)
    fig = px.scatter(scores, x="open_role_change_pct", y="disruption_index", size="open_roles", color="disruption_index", text="industry_norm", color_continuous_scale=[[0, COLORS["opportunity"]], [0.55, COLORS["transition"]], [1, COLORS["disruption"]]], range_color=[0, 100], size_max=56, labels={"open_role_change_pct": "Latest open-role momentum (%)", "disruption_index": "AI Disruption Index", "open_roles": "Open roles"}, hover_data={"layoffs_count": ":,.0f"}, custom_data=["industry_norm"])
    fig.add_vline(x=0, line_dash="dash", line_color="#98a2b3")
    fig.add_hline(y=50, line_dash="dash", line_color="#98a2b3")
    selected = set(selected_industries or [])
    fig.update_traces(
        textposition="top center",
        marker_opacity=[1.0 if not selected or industry in selected else 0.18 for industry in scores["industry_norm"]],
        hovertemplate="<b>%{customdata[0]}</b><br>Open-role momentum: %{x:+.1f}%<br>Disruption index: %{y:.1f}<br>Open roles: %{marker.size:,.0f}<extra></extra>",
    )
    fig.add_annotation(text="Click a bubble to filter by industry", x=0.01, y=1.02, xref="paper", yref="paper", showarrow=False, font={"size": 11, "color": COLORS["muted"]})
    return _style(fig, "Opportunity versus disruption")


def disruption_ranking(df: pd.DataFrame, dimension: str, selected_company: str | None = None, selected_values: list[str] | None = None) -> go.Figure:
    scores = disruption_scores(df, dimension)
    if scores.empty:
        return empty_figure("No AI disruption landscape matches these filters")
    scores = scores.nlargest(20, "disruption_index").copy()
    color_min = float(scores["disruption_index"].min())
    color_max = float(scores["disruption_index"].max())
    if color_min == color_max:
        color_min, color_max = max(0, color_min - 1), min(100, color_max + 1)
    scores["point_label"] = scores[dimension].astype(str)
    fig = px.scatter(
        scores,
        x="ai_replacement_risk",
        y="ai_automation_impact",
        size="open_roles",
        color="disruption_index",
        text="point_label",
        size_max=44,
        range_color=[color_min, color_max],
        color_continuous_scale=[[0, COLORS["opportunity"]], [0.55, COLORS["transition"]], [1, COLORS["disruption"]]],
        labels={"ai_replacement_risk": "AI replacement risk (1–10)", "ai_automation_impact": "AI automation impact", "open_roles": "Open roles", "disruption_index": "Disruption index", "point_label": ""},
        custom_data=[dimension, "disruption_index", "ai_replacement_risk", "ai_automation_impact", "ai_adoption_level", "open_roles"],
    )
    label_positions = ["top center", "bottom center", "middle left", "middle right", "top left", "top right", "bottom left", "bottom right"]
    selected = set(selected_values or [])
    if selected:
        point_opacity = [1.0 if value in selected else 0.18 for value in scores[dimension]]
    elif selected_company and dimension == "company_name":
        point_opacity = [1.0 if company == selected_company else 0.18 for company in scores[dimension]]
    else:
        point_opacity = 0.78
    fig.update_traces(
        textposition=[label_positions[index % len(label_positions)] for index in range(len(scores))],
        textfont={"size": 10, "color": COLORS["ink"]},
        cliponaxis=False,
        marker={"opacity": point_opacity, "line": {"color": "white", "width": 1.2}},
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>Disruption index: %{customdata[1]:.1f} / 100"
            "<br>AI replacement risk: %{customdata[2]:.1f} / 10<br>Automation impact: %{customdata[3]:.1f}"
            "<br>AI adoption level: %{customdata[4]:.1f} / 10<br>Open roles: %{customdata[5]:,.0f}<extra></extra>"
        ),
    )
    x_min, x_max = float(scores["ai_replacement_risk"].min()), float(scores["ai_replacement_risk"].max())
    y_min, y_max = float(scores["ai_automation_impact"].min()), float(scores["ai_automation_impact"].max())
    x_spread = x_max - x_min
    y_spread = y_max - y_min
    x_pad = max(x_spread * 0.35, 0.04)
    y_pad = max(y_spread * 0.35, 0.08)
    dimension_label = {"country": "Country", "industry_norm": "Industry", "company_name": "Company"}.get(dimension, dimension.replace("_", " ").title())
    fig = _style(fig, f"<b>AI disruption landscape · {dimension_label}</b><br><sup>Size: open roles · color: displayed disruption index</sup>")
    fig.update_xaxes(range=[max(1, x_min - x_pad), min(10, x_max + x_pad)], title_standoff=18)
    fig.update_yaxes(range=[max(0, y_min - y_pad), y_max + y_pad], title_standoff=14)
    fig.update_layout(
        coloraxis_colorbar={
            "title": {"text": f"Displayed index<br>{color_min:.1f}–{color_max:.1f}"},
            "orientation": "h",
            "x": 0.5,
            "xanchor": "center",
            "y": -0.22,
            "yanchor": "top",
            "len": 0.72,
            "thickness": 9,
        },
        height=450,
        margin={"l": 58, "r": 24, "t": 72, "b": 88},
    )
    return fig


def company_recommendation_vs_disruption(df: pd.DataFrame, selected_company: str | None = None) -> go.Figure:
    recommendation_rows = recommendation_scores(df)
    if recommendation_rows.empty:
        return empty_figure("No company recommendation comparison matches these filters")
    company_rows = []
    for company, group in recommendation_rows.groupby("company_name", observed=True):
        sample_weights = group["open_roles"].clip(lower=0)
        total_weight = float(sample_weights.sum())
        weighted_mean = lambda column: float(np.average(group[column], weights=sample_weights)) if total_weight > 0 else float(group[column].mean())
        company_rows.append({
            "company_name": company,
            "open_roles": total_weight,
            "disruption_index": weighted_mean("disruption_index"),
            "recommendation_score": weighted_mean("recommendation_score"),
            "layoff_percentage": weighted_mean("layoff_percentage"),
        })
    scores = pd.DataFrame(company_rows).sort_values("recommendation_score", ascending=False)
    selected_opacity = [1.0 if not selected_company or company == selected_company else 0.18 for company in scores["company_name"]]
    fig = go.Figure()
    for row in scores.itertuples(index=False):
        alpha = 1.0 if not selected_company or row.company_name == selected_company else 0.18
        fig.add_trace(go.Scatter(
            x=[row.disruption_index, row.recommendation_score], y=[row.company_name, row.company_name],
            mode="lines", line={"color": f"rgba(152,162,179,{alpha})", "width": 4}, hoverinfo="skip", showlegend=False,
        ))
    customdata = np.column_stack([scores["company_name"], scores["recommendation_score"], scores["disruption_index"], scores["open_roles"], scores["layoff_percentage"]])
    hovertemplate = "<b>%{customdata[0]}</b><br>Recommendation: %{customdata[1]:.1f} / 100<br>Disruption: %{customdata[2]:.1f} / 100<br>Open roles: %{customdata[3]:,.0f}<br>Average layoff percentage: %{customdata[4]:.1f}%<extra></extra>"
    fig.add_trace(go.Scatter(
        x=scores["disruption_index"], y=scores["company_name"], mode="markers", name="AI disruption",
        marker={"size": 11, "color": COLORS["disruption"], "opacity": selected_opacity, "line": {"color": "white", "width": 1}},
        customdata=customdata, hovertemplate=hovertemplate,
    ))
    fig.add_trace(go.Scatter(
        x=scores["recommendation_score"], y=scores["company_name"], mode="markers", name="Recommendation",
        marker={"size": 11, "color": COLORS["opportunity"], "opacity": selected_opacity, "line": {"color": "white", "width": 1}},
        customdata=customdata, hovertemplate=hovertemplate,
    ))
    combined_min = min(float(scores["disruption_index"].min()), float(scores["recommendation_score"].min()))
    combined_max = max(float(scores["disruption_index"].max()), float(scores["recommendation_score"].max()))
    padding = max((combined_max - combined_min) * 0.12, 3)
    company_labels = scores["company_name"].tolist()
    fig.update_yaxes(categoryorder="array", categoryarray=company_labels, tickmode="array", tickvals=company_labels, ticktext=company_labels, autorange="reversed", tickfont={"size": 8}, automargin=True)
    fig.update_xaxes(title_text="Score (0–100)", range=[max(0, combined_min - padding), min(100, combined_max + padding)])
    fig = _style(fig, "Company recommendation vs AI disruption")
    fig.update_layout(height=520, legend={"orientation": "h", "yanchor": "bottom", "y": 1.01, "xanchor": "right", "x": 1, "font": {"size": 9}}, margin={"l": 92, "r": 25, "t": 72, "b": 62})
    return fig


def company_disruption_bars(df: pd.DataFrame, selected_company: str | None = None) -> go.Figure:
    scores = disruption_scores(df, "company_name")
    if scores.empty:
        return empty_figure("No company disruption comparison matches these filters")
    scores = scores.nlargest(20, "disruption_index").sort_values("disruption_index", ascending=False)
    score_min = float(scores["disruption_index"].min())
    score_max = float(scores["disruption_index"].max())
    score_padding = max((score_max - score_min) * 0.22, 3)
    axis_min = max(0, score_min - score_padding)
    axis_max = min(100, score_max + score_padding)
    fig = go.Figure(go.Bar(
        x=scores["disruption_index"], y=scores["company_name"], orientation="h",
        text=scores["disruption_index"].map(lambda value: f"{value:.1f}"), textposition="outside",
        marker={
            "color": scores["disruption_index"],
            "colorscale": [[0, COLORS["opportunity"]], [0.55, COLORS["transition"]], [1, COLORS["disruption"]]],
            "cmin": axis_min, "cmax": axis_max, "showscale": False,
            "opacity": [1.0 if not selected_company or company == selected_company else 0.18 for company in scores["company_name"]],
            "line": {"color": "white", "width": 0.8},
        },
        customdata=np.column_stack([scores["ai_replacement_risk"], scores["ai_automation_impact"], scores["ai_adoption_level"], scores["open_roles"]]),
        hovertemplate="<b>%{y}</b><br>Disruption index: %{x:.1f} / 100<br>AI replacement risk: %{customdata[0]:.1f} / 10<br>AI automation impact: %{customdata[1]:.1f}<br>AI adoption level: %{customdata[2]:.1f} / 10<br>Open roles: %{customdata[3]:,.0f}<extra></extra>",
    ))
    company_labels = scores["company_name"].tolist()
    fig.update_yaxes(categoryorder="array", categoryarray=company_labels, tickmode="array", tickvals=company_labels, ticktext=company_labels, autorange="reversed", tickfont={"size": 8}, automargin=True)
    fig.update_xaxes(title_text=f"AI Disruption Index · zoomed range {axis_min:.0f}–{axis_max:.0f}", range=[axis_min, axis_max])
    fig = _style(fig, "AI disruption ranking · Company")
    fig.update_layout(height=520, showlegend=False, margin={"l": 92, "r": 35, "t": 62, "b": 62})
    return fig


def country_disruption_lollipop(df: pd.DataFrame, selected_countries: list[str] | None = None) -> go.Figure:
    scores = disruption_scores(df, "country")
    if scores.empty:
        return empty_figure("No country disruption comparison matches these filters")
    scores = scores.sort_values("disruption_index", ascending=False)
    selected = set(selected_countries or [])
    def rgba(hex_color: str, alpha: float) -> str:
        value = hex_color.lstrip("#")
        red, green, blue = (int(value[index:index + 2], 16) for index in (0, 2, 4))
        return f"rgba({red},{green},{blue},{alpha})"

    point_colors = []
    for country, score in zip(scores["country"], scores["disruption_index"]):
        base = COLORS["opportunity"] if score < 40 else COLORS["transition"] if score < 60 else COLORS["disruption"]
        point_colors.append(rgba(base, 1.0 if not selected or country in selected else 0.18))

    fig = go.Figure()
    for country, score, color in zip(scores["country"], scores["disruption_index"], point_colors):
        fig.add_trace(go.Scatter(
            x=[0, score], y=[country, country], mode="lines", line={"color": color, "width": 7},
            hoverinfo="skip", showlegend=False,
        ))
    fig.add_trace(go.Scatter(
        x=scores["disruption_index"],
        y=scores["country"],
        mode="markers+text",
        text=scores["disruption_index"].map(lambda value: f"{value:.1f}"),
        textposition="middle right",
        marker={
            "size": 18,
            "color": point_colors,
            "line": {"color": "white", "width": 2},
        },
        customdata=np.column_stack([scores["layoff_percentage"], scores["open_roles"], scores["ai_replacement_risk"]]),
        hovertemplate=(
            "<b>%{y}</b><br>Disruption index: %{x:.1f} / 100"
            "<br>Average layoff percentage: %{customdata[0]:.1f}%"
            "<br>Open roles: %{customdata[1]:,.0f}"
            "<br>AI replacement risk: %{customdata[2]:.1f} / 10<extra></extra>"
        ),
    ))
    fig = _style(fig, "AI disruption by country")
    fig.update_yaxes(categoryorder="array", categoryarray=scores["country"].tolist(), autorange="reversed")
    fig.update_xaxes(title_text="AI Disruption Index (0–100)", range=[0, 106], dtick=20)
    fig.update_layout(
        height=450,
        showlegend=False,
        margin={"l": 85, "r": 42, "t": 62, "b": 62},
    )
    return fig


def country_industry_heatmap(
    bridge: pd.DataFrame,
    metric: str,
    selected_countries: list[str] | None = None,
    selected_industries: list[str] | None = None,
) -> go.Figure:
    if bridge.empty:
        return empty_figure("No connected benchmark data matches these filters")
    metric_labels = {
        "avg_salary": "Salary benchmark",
        "employee_satisfaction": "Employee satisfaction",
        "attrition_rate": "Attrition rate",
        "ai_adoption_score": "AI adoption",
        "layoff_risk_score": "Layoff risk",
    }
    metric = metric if metric in metric_labels else "avg_salary"
    grouped = bridge.groupby(["industry_norm", "region"], observed=True)[metric].mean().reset_index()
    grouped = grouped.dropna(subset=[metric]).copy()
    if grouped.empty:
        return empty_figure("No valid benchmark observations match these filters")
    selected_country_set = set(selected_countries or [])
    selected_industry_set = set(selected_industries or [])
    all_countries = sorted(COUNTRY_TO_REGION)
    country_lookup = pd.DataFrame(
        [{"country": country, "region": COUNTRY_TO_REGION[country]} for country in all_countries if country in COUNTRY_TO_REGION]
    )
    grouped = grouped.merge(country_lookup, on="region", how="inner")
    if grouped.empty:
        return empty_figure("No country-linked regional benchmarks match these filters")
    order = grouped.groupby("industry_norm", observed=True)[metric].mean().sort_values(ascending=False).index.tolist()
    if selected_industry_set:
        order = [industry for industry in order if industry in selected_industry_set] + [industry for industry in order if industry not in selected_industry_set]
    countries = sorted(grouped["country"].dropna().unique())
    if selected_country_set:
        countries = [country for country in countries if country in selected_country_set] + [country for country in countries if country not in selected_country_set]
    value_matrix = grouped.pivot_table(index="industry_norm", columns="country", values=metric, aggfunc="mean").reindex(index=order, columns=countries)
    region_matrix = grouped.pivot_table(index="industry_norm", columns="country", values="region", aggfunc="first").reindex(index=order, columns=countries)
    value_labels = value_matrix.apply(
        lambda column: column.map(
            lambda value: "" if pd.isna(value) else f"${value / 1000:.0f}k" if metric == "avg_salary" else f"{value:.1f}"
        )
    )
    metric_label = metric_labels[metric]
    fig = go.Figure(go.Heatmap(
        z=value_matrix.to_numpy(),
        x=countries,
        y=order,
        text=value_labels.to_numpy(),
        texttemplate="%{text}",
        customdata=region_matrix.to_numpy(),
        colorscale=[[0, "#dbeafe"], [0.5, "#60a5fa"], [1, "#1d4ed8"]],
        xgap=2,
        ygap=2,
        colorbar={"title": metric_label},
        hovertemplate="<b>%{y} · %{x}</b><br>" + metric_label + ": %{text}<br>Source region: %{customdata}<extra></extra>",
    ))
    if selected_country_set or selected_industry_set:
        highlight_cells = [
            (country, industry)
            for country in countries
            for industry in order
            if (not selected_country_set or country in selected_country_set)
            and (not selected_industry_set or industry in selected_industry_set)
            and pd.notna(value_matrix.loc[industry, country])
        ]
        for country, industry in highlight_cells:
            fig.add_shape(
                type="rect",
                xref="x",
                yref="y",
                x0=country,
                x1=country,
                y0=industry,
                y1=industry,
                x0shift=-0.5,
                x1shift=0.5,
                y0shift=-0.5,
                y1shift=0.5,
                line={"color": COLORS["ink"], "width": 2},
                fillcolor="rgba(0,0,0,0)",
                layer="above",
            )
    fig.update_yaxes(autorange="reversed", title_text="")
    fig.update_xaxes(title_text="Country", side="bottom")
    fig = _style(fig, "")
    fig.update_layout(
        height=350,
        margin={"l": 72, "r": 48, "t": 32, "b": 55},
    )
    return fig


def signal_cloud(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return empty_figure("No layoff reasons match these filters")
    tokens = df["reason_for_layoffs"].dropna().astype(str).tolist()
    counts = Counter(tokens).most_common(28)
    if not counts:
        return empty_figure("No layoff reasons are available")
    words, values = zip(*counts)
    theta = np.arange(len(words)) * 2.39996
    radius = 0.42 * np.sqrt(np.arange(len(words)) + 1)
    sizes = 15 + 31 * (np.array(values) / max(values))
    palette = [COLORS["disruption"], COLORS["transition"], COLORS["context"], COLORS["disruption_dark"]]
    colors = [palette[index % len(palette)] for index, _word in enumerate(words)]
    x_values = radius * np.cos(theta)
    y_values = radius * np.sin(theta)
    fig = go.Figure(go.Scatter(x=x_values, y=y_values, mode="text", text=words, textfont={"size": sizes, "color": colors}, customdata=values, cliponaxis=False, hovertemplate="%{text}<br>Occurrences: %{customdata:,}<extra></extra>"))
    extent = max(float(np.max(np.abs(x_values))), float(np.max(np.abs(y_values))), 1.0) + 0.9
    fig.update_xaxes(visible=False, range=[-extent, extent])
    fig.update_yaxes(visible=False, range=[-extent, extent], scaleanchor="x", scaleratio=1)
    fig = _style(fig, "Reasons for layoffs · frequency cloud")
    fig.update_layout(height=300, margin={"l": 60, "r": 60, "t": 58, "b": 38})
    return fig
