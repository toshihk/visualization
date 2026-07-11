import dash
from dash import dcc, html

from app.components import dropdown, page_intro
from app.constants import APP_PERIODS, METRIC_OPTIONS
from app.data_loader import dropdown_options, load_profile


def layout(**_kwargs):
    profile = load_profile()
    latest_explore_period = len(APP_PERIODS) - 2
    sidebar_period_marks = {0: "2024", 4: "2025", 8: "2026"}
    filters = html.Section(
        [
            html.Div(
                [
                    html.Label([html.Span("Period · year and quarter", className="filter-label"), dcc.RangeSlider(id="ex-period", min=0, max=latest_explore_period, step=1, value=[0, latest_explore_period], marks=sidebar_period_marks, allowCross=False)], className="filter-control slider-control period-control"),
                    dropdown("ex-countries", "Country / comparison country", dropdown_options(profile.get("countries", [])), []),
                    dropdown("ex-industries", "Industry", dropdown_options(profile.get("industries", [])), []),
                    html.Div([html.Span("Role: ", className="filter-note-label"), html.Strong(id="ex-role-label", children="None selected")], className="selection-note compact-selection-note"),
                    html.Div([html.Button("Reset", id="ex-reset", n_clicks=0, className="button button-secondary"), html.Button("Continue →", id="ex-continue", n_clicks=0, className="button button-primary")], className="filter-actions compact-actions"),
                ],
                className="filter-grid explore-filter-grid compact-top-filter-grid",
            ),
        ],
        className="filters-panel top-filter-bar explore-top-filter-bar",
    )
    analysis = html.Div(
        [
            html.Section(id="ex-kpis", className="kpi-grid four-up"),
            html.Section(
                [
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.H3("The Global Open Roles", id="ex-map-title", className="chart-inline-title"),
                                    dropdown("ex-map-metric", "", [{"label": label, "value": value} for value, label in METRIC_OPTIONS.items()], "open_roles", multi=False),
                                ],
                                className="chart-local-toolbar",
                            ),
                            dcc.Graph(id="ex-map", config={"displayModeBar": False, "scrollZoom": False, "doubleClick": False}, responsive=True, className="map-stack-graph"),
                        ],
                        className="viz-card map-stack-card chart-with-control",
                    ),
                    html.Div(
                        [
                            dcc.Graph(id="ex-role-industry", config={"displayModeBar": False}, responsive=True, className="role-industry-graph"),
                            dcc.Graph(id="ex-industry-layoffs", config={"displayModeBar": False}, responsive=True, className="industry-layoffs-graph"),
                        ],
                        className="viz-card compact-chart-card role-industry-card industry-comparison-card",
                    ),
                ],
                className="dashboard-grid explore-hero-grid",
            ),
            html.Section(
                [
                    html.Div(dcc.Graph(id="ex-timeline", config={"displayModeBar": False}, responsive=True, className="explore-small-graph"), className="viz-card explore-third-card"),
                    html.Div(dcc.Graph(id="ex-momentum", config={"displayModeBar": False}, responsive=True, className="explore-small-graph"), className="viz-card explore-third-card"),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.H3("Salary benchmark", id="ex-benchmark-title", className="chart-inline-title"),
                                    dropdown("ex-benchmark-view", "", [{"label": "Salary benchmark", "value": "avg_salary"}, {"label": "Employee satisfaction", "value": "employee_satisfaction"}, {"label": "Attrition rate", "value": "attrition_rate"}, {"label": "AI adoption", "value": "ai_adoption_score"}, {"label": "Layoff risk", "value": "layoff_risk_score"}], "avg_salary", multi=False),
                                ],
                                className="chart-local-toolbar",
                            ),
                            dcc.Graph(id="ex-salary-benchmark", config={"displayModeBar": False}, responsive=True, className="explore-small-graph"),
                        ],
                        className="viz-card chart-with-control explore-third-card explore-heatmap-card",
                    ),
                ],
                className="dashboard-grid explore-thirds-grid",
            ),
        ],
        className="explore-main",
    )
    return html.Main(
        [
            dcc.Store(id="ex-selected-role"),
            page_intro(
                "Explore the job market",
                None,
                None,
            ),
            html.Div([filters, analysis], className="explore-workspace"),
        ],
        className="page-content",
    )


dash.register_page(__name__, path="/explore", name="Explore the Job Market", order=0, layout=layout)
