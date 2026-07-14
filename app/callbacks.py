"""Cross-page state and page-specific Dash callbacks."""

from __future__ import annotations

from urllib.parse import parse_qs, urlencode

import pandas as pd
from dash import Input, Output, State, ctx, html, no_update
from dash.exceptions import PreventUpdate

from app.constants import APP_PERIODS, APP_QUARTERS, COUNTRY_TO_ISO3, COUNTRY_TO_REGION, DEFAULT_JOURNEY, METRIC_OPTIONS
from app.data_loader import filter_bridge, filter_layoffs
from app.figures import (
    company_disruption_bars,
    company_recommendation_scatter,
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
from app.scoring import recommendation_scores


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


def _salary_bounds(profile):
    salary_min = int(profile.get("salary_min", 30000) // 5000 * 5000)
    salary_max = int((profile.get("salary_max", 220000) // 5000 + 1) * 5000)
    return salary_min, salary_max


def _salary_active(salary_range, profile):
    salary_min, salary_max = _salary_bounds(profile)
    return bool(salary_range and len(salary_range) == 2 and [int(salary_range[0]), int(salary_range[1])] != [salary_min, salary_max])


def _salary_matched_layoffs(df: pd.DataFrame, bridge_df: pd.DataFrame, period_range, salary_range) -> pd.DataFrame:
    if not salary_range or len(salary_range) != 2:
        return df
    salary_bridge = filter_bridge(bridge_df, period_range=period_range, salary_range=salary_range)
    if salary_bridge.empty:
        return df.iloc[0:0].copy()
    combos = salary_bridge[["industry_norm", "region"]].drop_duplicates()
    return df.merge(combos.assign(_salary_match=1), on=["industry_norm", "region"], how="inner").drop(columns="_salary_match")


def _salary_country_source(bridge_df: pd.DataFrame) -> pd.DataFrame:
    if bridge_df.empty or "avg_salary" not in bridge_df.columns:
        return bridge_df.iloc[0:0].copy()
    countries = pd.DataFrame(
        [
            {"country": country, "region": region, "iso_alpha": COUNTRY_TO_ISO3.get(country)}
            for country, region in COUNTRY_TO_REGION.items()
        ]
    ).dropna(subset=["iso_alpha"])
    salary_by_region = bridge_df.dropna(subset=["avg_salary"]).groupby("region", observed=True)["avg_salary"].mean().reset_index()
    return countries.merge(salary_by_region, on="region", how="inner")


def _map_metric_value(value) -> str:
    """Keep the map on a selectable non-salary metric, defaulting to layoffs."""
    if value in METRIC_OPTIONS and value not in {"avg_salary", "open_roles"}:
        return value
    return "layoffs_count"


def _latest_period_index() -> int:
    return len(APP_PERIODS) - 2


def _clamp_period_range(period_range, max_index: int | None = None) -> list[int]:
    max_index = _latest_period_index() if max_index is None else max_index
    if not period_range or len(period_range) != 2:
        return [0, max_index]
    start, end = int(period_range[0]), int(period_range[1])
    start = max(0, min(start, max_index))
    end = max(0, min(end, max_index))
    return [min(start, end), max(start, end)]


def _csv_values(values) -> str:
    return ",".join(str(value) for value in (values or []) if value)


def _split_values(value: str | None) -> list[str]:
    if not value:
        return []
    return [item for item in value.split(",") if item]


def _range_from_text(value: str | None, fallback, max_index: int | None = None) -> list[int]:
    if not value:
        return fallback
    try:
        start, end = [int(float(part)) for part in value.split(",", 1)]
    except (TypeError, ValueError):
        return fallback
    if max_index is None:
        return [min(start, end), max(start, end)]
    return _clamp_period_range([start, end], max_index)


def _explore_query(period_range, salary_range, countries, industries) -> str:
    query = {
        "period": ",".join(map(str, _clamp_period_range(period_range, _latest_period_index()))),
        "salary": ",".join(map(str, salary_range or [])),
    }
    if countries:
        query["countries"] = _csv_values(countries)
    if industries:
        query["industries"] = _csv_values(industries)
    return "?" + urlencode(query)


def _state_from_explore_query(search: str | None, fallback: dict, profile: dict) -> dict:
    if not search:
        return fallback
    parsed = parse_qs(search.lstrip("?"))
    salary_min, salary_max = _salary_bounds(profile)
    state = dict(fallback)
    period_range = _range_from_text((parsed.get("period") or [None])[0], fallback.get("period_range", [0, _latest_period_index()]), _latest_period_index())
    salary_range = _range_from_text((parsed.get("salary") or [None])[0], fallback.get("salary_range", [salary_min, salary_max]))
    countries = _split_values((parsed.get("countries") or [None])[0])
    industries = _split_values((parsed.get("industries") or [None])[0])
    start, end = period_range
    state.update({
        "period_range": period_range,
        "salary_range": salary_range,
        "countries": countries,
        "industries": industries,
        "regions": sorted({COUNTRY_TO_REGION[c] for c in countries if c in COUNTRY_TO_REGION}),
        "years": [2024 + int(start) // 4, 2024 + int(end) // 4],
        "quarters": APP_QUARTERS,
    })
    return state


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
            return [], [], None
        if trigger == "ex-map":
            countries = _toggle(countries, _countries_from_map(map_click), limit=2)
        elif trigger in {"ex-role-industry", "ex-industry-layoffs"}:
            clicked_industry = _point_value(role_industry_click if trigger == "ex-role-industry" else industry_layoffs_click, "y")
            industries = _toggle(industries, clicked_industry)
        return countries or [], industries or [], role

    @app.callback(
        Output("ex-period", "value"),
        Output("ex-salary-range", "value"),
        Output("ex-map-metric", "value"),
        Output("ex-benchmark-view", "value"),
        Input("ex-reset", "n_clicks"),
        prevent_initial_call=True,
    )
    def reset_explore_filters(_clicks):
        salary_min, salary_max = _salary_bounds(profile)
        return [0, _latest_period_index()], [salary_min, salary_max], "layoffs_count", "avg_salary"

    @app.callback(
        Output("ex-period", "value", allow_duplicate=True),
        Output("ex-salary-range", "value", allow_duplicate=True),
        Output("ex-countries", "value", allow_duplicate=True),
        Output("ex-industries", "value", allow_duplicate=True),
        Output("ex-selected-role", "data", allow_duplicate=True),
        Output("ex-map-metric", "value", allow_duplicate=True),
        Input("url", "pathname"),
        Input("url", "search"),
        Input("journey-state", "data"),
        prevent_initial_call=True,
    )
    def hydrate_explore_from_journey(pathname, search, journey):
        if pathname != "/explore":
            raise PreventUpdate
        state = _state_from_explore_query(search, journey or DEFAULT_JOURNEY, profile)
        salary_min, salary_max = _salary_bounds(profile)
        role = state.get("selected_role")
        return (
            _clamp_period_range(state.get("period_range"), _latest_period_index()),
            state.get("salary_range", [salary_min, salary_max]),
            state.get("countries", []),
            state.get("industries", []),
            role,
            _map_metric_value(state.get("map_metric", "layoffs_count")),
        )

    @app.callback(
        Output("ex-map", "figure"),
        Output("ex-map-title", "children"),
        Output("ex-timeline", "figure"),
        Output("ex-momentum", "figure"),
        Output("ex-role-industry", "figure"),
        Output("ex-industry-layoffs", "figure"),
        Output("ex-salary-benchmark", "figure"),
        Output("ex-benchmark-title", "children"),
        Input("ex-period", "value"),
        Input("ex-salary-range", "value"),
        Input("ex-industries", "value"),
        Input("ex-countries", "value"),
        Input("ex-map-metric", "value"),
        Input("ex-benchmark-view", "value"),
        Input("ex-selected-role", "data"),
    )
    def update_explore(period_range, salary_range, industries, countries, map_metric, benchmark_view, selected_role):
        map_metric = _map_metric_value(map_metric)
        timeline_range = [0, _latest_period_index()]
        market = _salary_matched_layoffs(filter_layoffs(layoffs_df, period_range=period_range), bridge_df, period_range, salary_range)
        highlighted_market = _salary_matched_layoffs(filter_layoffs(layoffs_df, period_range=period_range, industries=industries, countries=countries, role=selected_role), bridge_df, period_range, salary_range)
        highlight_active = bool((industries or []) or (countries or []) or selected_role)
        period_brush_active = (period_range or timeline_range) != timeline_range
        bridge = filter_bridge(bridge_df, period_range=period_range, salary_range=salary_range)
        timeline_market = _salary_matched_layoffs(filter_layoffs(layoffs_df, period_range=timeline_range), bridge_df, timeline_range, salary_range)
        map_source = market
        map_title = f"Global {METRIC_OPTIONS.get(map_metric, map_metric)}"
        benchmark_labels = {
            "avg_salary": "Salary benchmark",
            "employee_satisfaction": "Employee satisfaction",
            "attrition_rate": "Attrition rate",
            "ai_adoption_score": "AI adoption",
            "layoff_risk_score": "Layoff risk",
        }
        benchmark_title = benchmark_labels.get(benchmark_view or "avg_salary", "Salary benchmark")
        selected_context = highlighted_market if highlight_active or period_brush_active else None
        return country_map(map_source, map_metric, countries), map_title, opportunity_timeline(timeline_market, selected_context), open_role_momentum(timeline_market, selected_context), role_vs_industry(market, selected_role, industries), industry_layoffs_bar(market, industries), country_industry_heatmap(bridge, benchmark_view or "avg_salary", countries, industries), benchmark_title

    @app.callback(
        Output("journey-state", "data"),
        Output("url", "pathname"),
        Input("ex-continue", "n_clicks"),
        State("ex-period", "value"),
        State("ex-salary-range", "value"),
        State("ex-countries", "value"),
        State("ex-industries", "value"),
        State("ex-selected-role", "data"),
        State("ex-map-metric", "value"),
        State("journey-state", "data"),
        prevent_initial_call=True,
    )
    def continue_to_decide(_clicks, period_range, salary_range, countries, industries, role, map_metric, journey):
        if not _clicks:
            raise PreventUpdate
        countries = countries or []
        state = dict(journey or DEFAULT_JOURNEY)
        start, end = _clamp_period_range(period_range, _latest_period_index())
        state.update({"period_range": [start, end], "years": [2024 + int(start) // 4, 2024 + int(end) // 4], "quarters": APP_QUARTERS, "countries": countries, "regions": sorted({COUNTRY_TO_REGION[c] for c in countries if c in COUNTRY_TO_REGION}), "industries": industries or [], "selected_role": role, "map_metric": _map_metric_value(map_metric), "salary_range": salary_range})
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
        salary_min, salary_max = _salary_bounds(profile)
        return _clamp_period_range(state.get("period_range"), _latest_period_index()), state.get("industries", []), state.get("countries", []), state.get("salary_range", [salary_min, salary_max]), "industry_norm"

    @app.callback(
        Output("journey-state", "data", allow_duplicate=True),
        Output("url", "pathname", allow_duplicate=True),
        Output("url", "search", allow_duplicate=True),
        Input("de-back-explore", "n_clicks"),
        State("de-period", "value"),
        State("de-salary-range", "value"),
        State("de-countries", "value"),
        State("de-industries", "value"),
        State("journey-state", "data"),
        prevent_initial_call=True,
    )
    def back_to_explore(_clicks, period_range, salary_range, countries, industries, journey):
        if not _clicks:
            raise PreventUpdate
        countries = countries or []
        start, end = _clamp_period_range(period_range, _latest_period_index())
        state = dict(journey or DEFAULT_JOURNEY)
        state.update({
            "period_range": [start, end],
            "years": [2024 + int(start) // 4, 2024 + int(end) // 4],
            "quarters": APP_QUARTERS,
            "countries": countries,
            "regions": sorted({COUNTRY_TO_REGION[c] for c in countries if c in COUNTRY_TO_REGION}),
            "industries": industries or [],
            "salary_range": salary_range,
        })
        return state, "/explore", _explore_query([start, end], salary_range, countries, industries)

    @app.callback(
        Output("de-selected-company", "data"),
        Input("de-reset", "n_clicks"),
        Input("de-clear-company", "n_clicks"),
        Input("de-company-scatter", "clickData"),
        Input("de-company-scatter-focus", "clickData"),
        Input("de-disruption-company", "clickData"),
        State("de-selected-company", "data"),
        prevent_initial_call=True,
    )
    def select_company(_reset, _clear_company, scatter_click, scatter_focus_click, company_click, selected_company):
        trigger = ctx.triggered_id
        if trigger in {"de-reset", "de-clear-company"}:
            return None
        if trigger in {"de-company-scatter", "de-company-scatter-focus"}:
            point = ((scatter_click if trigger == "de-company-scatter" else scatter_focus_click) or {}).get("points", [{}])[0]
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
        Output("de-company-scatter-focus", "figure"),
        Output("de-disruption-company", "figure"),
        Output("de-disruption-segment", "figure"),
        Output("de-company-table", "data"),
        Output("de-company-table", "columns"),
        Output("de-signal-cloud", "figure"),
        Output("de-selection-chips", "children"),
        Output("de-clear-company", "children"),
        Output("de-clear-company", "style"),
        Input("de-period", "value"),
        Input("de-industries", "value"),
        Input("de-countries", "value"),
        Input("de-salary-range", "value"),
        Input("de-disruption-scope", "value"),
        Input("de-scatter-x-metric", "value"),
        Input("de-selected-company", "data"),
        Input("journey-state", "data"),
    )
    def update_decide(period_range, industries, countries, salary_range, disruption_scope, scatter_x_metric, selected_company, journey):
        role = (journey or {}).get("selected_role")
        salary_is_active = _salary_active(salary_range, profile)
        market = _salary_matched_layoffs(filter_layoffs(layoffs_df, period_range=period_range, industries=industries, countries=countries, role=role), bridge_df, period_range, salary_range)
        role_market = filter_layoffs(layoffs_df, period_range=period_range, role=role)
        chart_market = filter_layoffs(layoffs_df, period_range=period_range)
        country_context = filter_layoffs(layoffs_df, period_range=period_range, role=role)
        industry_context = filter_layoffs(layoffs_df, period_range=period_range, role=role)
        if selected_company and selected_company not in set(chart_market["company_name"].unique()):
            selected_company = None
        salary_bridge = filter_bridge(bridge_df, period_range=period_range, salary_range=salary_range)

        recommendations = recommendation_scores(market)
        table = recommendations[["company_name", "country", "industry_norm", "open_roles", "open_role_change_pct", "layoffs", "remote_share", "sentiment", "job_security", "ai_risk", "disruption_index", "recommendation_score"]].copy() if not recommendations.empty else pd.DataFrame()
        if not table.empty:
            table = table.rename(columns={"company_name": "Company", "country": "Country", "industry_norm": "Industry", "open_roles": "Open roles", "open_role_change_pct": "Open-role change %", "layoffs": "Layoffs", "remote_share": "Remote %", "sentiment": "Sentiment", "job_security": "Job security", "ai_risk": "AI risk", "disruption_index": "Disruption", "recommendation_score": "Recommendation"})
            for column in ["Open-role change %", "Remote %", "Sentiment", "Job security", "AI risk", "Disruption", "Recommendation"]:
                table[column] = table[column].round(1)
            if selected_company:
                table = table.assign(_selected=(table["Company"] == selected_company).astype(int)).sort_values(["_selected", "Recommendation"], ascending=[False, False]).drop(columns="_selected")
        columns = [{"name": column, "id": column} for column in table.columns]
        chips = []
        cloud_market = chart_market
        company_chip_text = f"Highlighted company: {selected_company} ×" if selected_company else ""
        company_chip_style = {} if selected_company else {"display": "none"}
        selected_company_context = market if (countries or industries or salary_is_active) else None
        segment_context = market if (countries or industries or salary_is_active) else None
        segment_figure = disruption_ranking(country_context, "country", selected_values=countries, selected_df=segment_context) if disruption_scope == "country" else disruption_ranking(industry_context, "industry_norm", selected_values=industries, selected_df=segment_context)
        return (
            company_recommendation_vs_disruption(role_market, selected_company, selected_company_context),
            company_recommendation_scatter(role_market, selected_company, selected_company_context, scatter_x_metric, salary_bridge),
            company_disruption_bars(chart_market, selected_company, selected_company_context),
            segment_figure,
            table.to_dict("records"),
            columns,
            signal_cloud(cloud_market),
            chips,
            company_chip_text,
            company_chip_style,
        )
