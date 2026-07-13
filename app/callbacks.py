"""Cross-page state and page-specific Dash callbacks."""

from __future__ import annotations

import pandas as pd
from dash import Input, Output, State, ctx, html, no_update
from dash.exceptions import PreventUpdate

from app.components import kpi_cards
from app.constants import APP_PERIODS, APP_QUARTERS, COUNTRY_TO_REGION, DEFAULT_JOURNEY, METRIC_OPTIONS
from app.data_loader import filter_bridge, filter_layoffs, filter_workforce
from app.figures import (
    company_disruption_bars,
    company_recommendation_vs_disruption,
    country_disruption_lollipop,
    country_industry_heatmap,
    country_map,
    disruption_ranking,
    industry_layoffs_bar,
    opportunity_timeline,
    open_role_momentum,
    role_vs_industry,
    signal_cloud,
)
from app.scoring import disruption_scores, quarterly_market, recommendation_scores


def _countries_from_map(click_data):
    if not click_data or not click_data.get("points"):
        return None
    custom = click_data["points"][0].get("customdata")
    return custom[0] if isinstance(custom, (list, tuple)) else custom


def _point_value(click_data, axis):
    if not click_data or not click_data.get("points"):
        return None
    return click_data["points"][0].get(axis)


def _toggle(values, value, limit=None):
    values = list(values or [])
    if not value:
        return values
    if value in values:
        values.remove(value)
    else:
        values.append(value)
    return values[-limit:] if limit else values


def _role_momentum(df):
    market = quarterly_market(df)
    if market.empty or len(market) < 2:
        return None
    return float(market.iloc[-1]["open_role_change_pct"])


def register_callbacks(app, workforce_df, layoffs_df, bridge_df, profile):
    @app.callback(
        Output("nav-explore", "className"),
        Output("nav-decide", "className"),
        Input("url", "pathname"),
    )
    def highlight_active_page(pathname):
        return (
            "nav-link active" if pathname == "/explore" else "nav-link",
            "nav-link active" if pathname == "/decide" else "nav-link",
        )

    @app.callback(
        Output("ex-countries", "value"),
        Output("ex-industries", "value"),
        Output("ex-selected-role", "data"),
        Output("ex-role-label", "children"),
        Input("ex-reset", "n_clicks"),
        Input("ex-map", "clickData"),
        Input("ex-role-industry", "clickData"),
        Input("ex-industry-layoffs", "clickData"),
        State("ex-countries", "value"),
        State("ex-industries", "value"),
        State("ex-selected-role", "data"),
        prevent_initial_call=True,
    )
    def explore_clicks(_reset, map_click, role_industry_click, industry_layoffs_click, countries, industries, role):
        trigger = ctx.triggered_id
        if trigger == "ex-reset":
            return [], [], None, "None selected"
        if trigger == "ex-map":
            countries = _toggle(countries, _countries_from_map(map_click), limit=2)
        elif trigger in {"ex-role-industry", "ex-industry-layoffs"}:
            clicked_industry = _point_value(role_industry_click if trigger == "ex-role-industry" else industry_layoffs_click, "y")
            industries = _toggle(industries, clicked_industry)
        return countries or [], industries or [], role, role or "None selected"

    @app.callback(
        Output("ex-period", "value"),
        Output("ex-map-metric", "value"),
        Output("ex-benchmark-view", "value"),
        Input("ex-reset", "n_clicks"),
        prevent_initial_call=True,
    )
    def reset_explore_filters(_clicks):
        return [0, len(APP_PERIODS) - 2], "open_roles", "avg_salary"

    @app.callback(
        Output("ex-map", "figure"),
        Output("ex-map-title", "children"),
        Output("ex-timeline", "figure"),
        Output("ex-momentum", "figure"),
        Output("ex-role-industry", "figure"),
        Output("ex-industry-layoffs", "figure"),
        Output("ex-salary-benchmark", "figure"),
        Output("ex-benchmark-title", "children"),
        Output("ex-kpis", "children"),
        Input("ex-period", "value"),
        Input("ex-industries", "value"),
        Input("ex-countries", "value"),
        Input("ex-map-metric", "value"),
        Input("ex-benchmark-view", "value"),
        Input("ex-selected-role", "data"),
    )
    def update_explore(period_range, industries, countries, map_metric, benchmark_view, selected_role):
        map_metric = map_metric or "open_roles"
        timeline_range = [0, len(APP_PERIODS) - 2]
        market = filter_layoffs(layoffs_df, period_range=period_range)
        highlighted_market = filter_layoffs(layoffs_df, period_range=period_range, industries=industries, countries=countries, role=selected_role)
        highlight_active = bool((industries or []) or (countries or []) or selected_role)
        period_brush_active = (period_range or timeline_range) != timeline_range
        kpi_market = highlighted_market if highlight_active else market
        bridge = filter_bridge(bridge_df, period_range=period_range)
        timeline_market = filter_layoffs(layoffs_df, period_range=timeline_range)
        momentum = _role_momentum(kpi_market)
        leading_role = kpi_market.groupby("top_hiring_role", observed=True)["open_roles"].sum().idxmax() if not kpi_market.empty else "—"
        items = [
            ("Open roles", f"{kpi_market['open_roles'].sum():,.0f}", "opportunity"),
            ("Latest open-role change", "Baseline" if momentum is None or pd.isna(momentum) else f"{momentum:+.1f}%", "opportunity" if momentum is not None and momentum >= 0 else "disruption"),
            ("Layoffs", f"{kpi_market['layoffs_count'].sum():,.0f}", "disruption"),
            ("Leading role", leading_role, "context"),
        ]
        map_title = "The Global Open Roles" if map_metric == "open_roles" else f"Global {METRIC_OPTIONS.get(map_metric, map_metric)}"
        benchmark_labels = {
            "avg_salary": "Salary benchmark",
            "employee_satisfaction": "Employee satisfaction",
            "attrition_rate": "Attrition rate",
            "ai_adoption_score": "AI adoption",
            "layoff_risk_score": "Layoff risk",
        }
        benchmark_title = benchmark_labels.get(benchmark_view or "avg_salary", "Salary benchmark")
        selected_context = highlighted_market if highlight_active or period_brush_active else None
        return country_map(market, map_metric, countries), map_title, opportunity_timeline(timeline_market, selected_context), open_role_momentum(timeline_market, selected_context), role_vs_industry(market, selected_role, industries), industry_layoffs_bar(market, industries), country_industry_heatmap(bridge, benchmark_view or "avg_salary", countries, industries), benchmark_title, kpi_cards(items)

    @app.callback(
        Output("journey-state", "data"),
        Output("url", "pathname"),
        Input("ex-continue", "n_clicks"),
        State("ex-period", "value"),
        State("ex-countries", "value"),
        State("ex-industries", "value"),
        State("ex-selected-role", "data"),
        State("ex-map-metric", "value"),
        State("journey-state", "data"),
        prevent_initial_call=True,
    )
    def continue_to_decide(_clicks, period_range, countries, industries, role, map_metric, journey):
        if not _clicks:
            raise PreventUpdate
        countries = countries or []
        state = dict(journey or DEFAULT_JOURNEY)
        start, end = period_range or [0, len(APP_PERIODS) - 1]
        state.update({"period_range": [start, end], "years": [2024 + int(start) // 4, 2024 + int(end) // 4], "quarters": APP_QUARTERS, "countries": countries, "regions": sorted({COUNTRY_TO_REGION[c] for c in countries if c in COUNTRY_TO_REGION}), "industries": industries or [], "selected_role": role, "map_metric": map_metric})
        return state, "/decide"

    @app.callback(
        Output("de-period", "value"),
        Output("de-industries", "value"),
        Output("de-countries", "value"),
        Output("de-salary-range", "value"),
        Output("de-disruption-scope", "value"),
        Input("url", "pathname"),
        Input("de-reset", "n_clicks"),
        State("journey-state", "data"),
    )
    def initialize_decide(pathname, _reset, journey):
        if pathname != "/decide":
            raise PreventUpdate
        state = journey or DEFAULT_JOURNEY
        salary_min = int(profile.get("salary_min", 30000) // 5000 * 5000)
        salary_max = int((profile.get("salary_max", 220000) // 5000 + 1) * 5000)
        return state.get("period_range", [0, len(APP_PERIODS) - 1]), state.get("industries", []), state.get("countries", []), [salary_min, salary_max], "industry_norm"

    @app.callback(
        Output("de-selected-company", "data"),
        Input("de-reset", "n_clicks"),
        Input("de-clear-company", "n_clicks"),
        Input("de-company-scatter", "clickData"),
        Input("de-disruption-company", "clickData"),
        State("de-selected-company", "data"),
        prevent_initial_call=True,
    )
    def select_company(_reset, _clear_company, scatter_click, company_click, selected_company):
        trigger = ctx.triggered_id
        if trigger in {"de-reset", "de-clear-company"}:
            return None
        if trigger == "de-company-scatter":
            point = (scatter_click or {}).get("points", [{}])[0]
            custom = point.get("customdata")
            company = custom[0] if isinstance(custom, (list, tuple)) and custom else None
        elif trigger == "de-disruption-company":
            company = _point_value(company_click, "y")
        else:
            raise PreventUpdate
        if not company:
            raise PreventUpdate
        return None if company == selected_company else company

    @app.callback(
        Output("de-company-scatter", "figure"),
        Output("de-disruption-company", "figure"),
        Output("de-disruption-segment", "figure"),
        Output("de-company-table", "data"),
        Output("de-company-table", "columns"),
        Output("de-signal-cloud", "figure"),
        Output("de-kpis", "children"),
        Output("de-selection-chips", "children"),
        Output("de-clear-company", "children"),
        Output("de-clear-company", "style"),
        Input("de-period", "value"),
        Input("de-industries", "value"),
        Input("de-countries", "value"),
        Input("de-salary-range", "value"),
        Input("de-disruption-scope", "value"),
        Input("de-selected-company", "data"),
        Input("journey-state", "data"),
    )
    def update_decide(period_range, industries, countries, salary_range, disruption_scope, selected_company, journey):
        role = (journey or {}).get("selected_role")
        regions = sorted({COUNTRY_TO_REGION[c] for c in (countries or []) if c in COUNTRY_TO_REGION})
        market = filter_layoffs(layoffs_df, period_range=period_range, industries=industries, countries=countries, role=role)
        role_market = filter_layoffs(layoffs_df, period_range=period_range, industries=industries, countries=countries)
        country_context = filter_layoffs(layoffs_df, period_range=period_range, industries=industries, role=role)
        industry_context = filter_layoffs(layoffs_df, period_range=period_range, countries=countries, role=role)
        if selected_company and selected_company not in set(role_market["company_name"].unique()):
            selected_company = None
        workforce = filter_workforce(workforce_df, period_range=period_range, industries=industries, regions=regions, salary_range=salary_range)

        recommendations = recommendation_scores(market)
        table = recommendations[["company_name", "country", "industry_norm", "open_roles", "open_role_change_pct", "layoffs", "remote_share", "sentiment", "job_security", "ai_risk", "disruption_index", "recommendation_score"]].copy() if not recommendations.empty else pd.DataFrame()
        if not table.empty:
            table = table.rename(columns={"company_name": "Company", "country": "Country", "industry_norm": "Industry", "open_roles": "Open roles", "open_role_change_pct": "Open-role change %", "layoffs": "Layoffs", "remote_share": "Remote %", "sentiment": "Sentiment", "job_security": "Job security", "ai_risk": "AI risk", "disruption_index": "Disruption", "recommendation_score": "Recommendation"})
            for column in ["Open-role change %", "Remote %", "Sentiment", "Job security", "AI risk", "Disruption", "Recommendation"]:
                table[column] = table[column].round(1)
            if selected_company:
                table = table.assign(_selected=(table["Company"] == selected_company).astype(int)).sort_values(["_selected", "Recommendation"], ascending=[False, False]).drop(columns="_selected")
        columns = [{"name": column, "id": column} for column in table.columns]
        scores = disruption_scores(market, "industry_norm")
        best = recommendations.iloc[0]["company_name"] if not recommendations.empty else "—"
        avg_disruption = scores["disruption_index"].mean() if not scores.empty else 0
        salary_value = workforce["avg_salary"].mean() if not workforce.empty else float("nan")
        salary_n = int(workforce["avg_salary"].notna().sum()) if not workforce.empty else 0
        items = [
            ("Best current match", best, "opportunity"),
            ("Average disruption", f"{avg_disruption:.1f}/100", "disruption" if avg_disruption >= 50 else "transition"),
            ("Salary benchmark", "—" if pd.isna(salary_value) else f"${salary_value:,.0f}", "context"),
            ("Valid salary records", f"{salary_n:,}", "context"),
        ]
        chips = []
        for label, values in [("Countries", countries), ("Industries", industries)]:
            if values:
                text = ", ".join(map(str, values))
                chips.append(html.Span(f"{label}: {text}", className="selection-chip"))
        if role:
            chips.append(html.Span(f"Role: {role}", className="selection-chip role-chip"))
        cloud_market = market[market["company_name"] == selected_company] if selected_company else market
        company_chip_text = f"Highlighted company: {selected_company} ×" if selected_company else ""
        company_chip_style = {} if selected_company else {"display": "none"}
        segment_figure = disruption_ranking(country_context, "country", selected_values=countries) if disruption_scope == "country" else disruption_ranking(industry_context, "industry_norm", selected_values=industries)
        return company_recommendation_vs_disruption(role_market, selected_company), company_disruption_bars(role_market, selected_company), segment_figure, table.to_dict("records"), columns, signal_cloud(cloud_market), kpi_cards(items), chips, company_chip_text, company_chip_style
