import dash
from dash import dash_table, dcc, html

from app.components import disruption_methodology, dropdown, page_intro, section_heading
from app.constants import APP_PERIODS
from app.data_loader import dropdown_options, load_profile


def layout(**_kwargs):
    profile = load_profile()
    salary_min = int(profile.get("salary_min", 30000) // 5000 * 5000)
    salary_max = int((profile.get("salary_max", 220000) // 5000 + 1) * 5000)
    latest_decision_period = len(APP_PERIODS) - 2
    sidebar_period_marks = {0: "2024", 4: "2025", 8: "2026"}
    filters = html.Section(
        [
            html.Div(
                [
                    html.Label([html.Span("Period · year and quarter", className="filter-label"), dcc.RangeSlider(id="de-period", min=0, max=latest_decision_period, step=1, value=[0, latest_decision_period], marks=sidebar_period_marks, allowCross=False)], className="filter-control slider-control period-control"),
                    dropdown("de-countries", "Country", dropdown_options(profile.get("countries", [])), []),
                    dropdown("de-industries", "Industry", dropdown_options(profile.get("industries", [])), []),
                    html.Label([html.Span("Salary benchmark range", className="filter-label"), dcc.RangeSlider(id="de-salary-range", min=salary_min, max=salary_max, step=5000, value=[salary_min, salary_max], marks={salary_min: f"${salary_min//1000}k", salary_max: f"${salary_max//1000}k"})], className="filter-control slider-control"),
                    html.Div([html.Button("Reset", id="de-reset", n_clicks=0, className="button button-secondary"), html.Button("← Explore", id="de-back-explore", n_clicks=0, className="button button-primary edit-exploration-button")], className="filter-actions compact-actions"),
                ],
                className="filter-grid decision-filter-grid compact-top-filter-grid",
            ),
        ],
        className="filters-panel top-filter-bar decision-top-filter-bar",
    )
    analysis = html.Div(
        [
            html.Div(
                [
                    disruption_methodology(),
                    html.Details([html.Summary("How the recommendation score works"), html.P("30% demand, 20% job security, 15% sentiment, 10% remote availability, 10% positive salary-budget change, 10% inverse AI replacement risk, and 5% inverse layoff pressure.")], className="method-note"),
                ],
                className="benchmark-methodology benchmark-methodology-row",
            ),
            html.Section(
                [
                    html.Div(
                        [
                            html.Div(dcc.Graph(id="de-company-scatter", config={"displayModeBar": False}, responsive=True, className="decision-stack-graph"), className="viz-card decision-stack-card"),
                            html.Div(
                                [
                                    html.Div(dropdown("de-disruption-scope", "Compare disruption by", [{"label": "Industry", "value": "industry_norm"}, {"label": "Country", "value": "country"}], "industry_norm", multi=False), className="chart-local-toolbar"),
                                    dcc.Graph(id="de-disruption-segment", config={"displayModeBar": False}, responsive=True, className="decision-stack-graph"),
                                ],
                                className="viz-card decision-stack-card chart-with-control",
                            ),
                        ],
                        className="decision-left-stack",
                    ),
                    html.Div(
                        [
                            html.Div(
                                dropdown(
                                    "de-scatter-x-metric",
                                    "X axis",
                                    [
                                        {"label": "Open roles", "value": "open_roles"},
                                        {"label": "Sentiment", "value": "sentiment"},
                                        {"label": "Job security", "value": "job_security"},
                                        {"label": "Salary budget change", "value": "salary_budget_change"},
                                        {"label": "AI replacement risk", "value": "ai_risk"},
                                        {"label": "Layoff percentage", "value": "layoff_percentage"},
                                    ],
                                    "open_roles",
                                    multi=False,
                                ),
                                className="chart-local-toolbar",
                            ),
                            dcc.Graph(id="de-company-scatter-focus", config={"displayModeBar": False}, responsive=True, className="decision-bubble-graph"),
                        ],
                        className="viz-card chart-with-control decision-bubble-card",
                    ),
                ],
                className="dashboard-grid decision-disruption-grid",
            ),
            section_heading("Decision", "Use the linked shortlist and layoff reasons to make the final comparison."),
            html.Section(
                [
                    html.Div(
                        [
                            html.Div([html.H2("Recommended companies"), html.P("Ranked from current filters; company salary is not inferred.", className="panel-note")], className="panel-heading"),
                            dash_table.DataTable(id="de-company-table", page_size=6, sort_action="native", filter_action="native", style_table={"overflowX": "auto"}, style_cell={"fontFamily": "Inter, system-ui, sans-serif", "fontSize": 11, "padding": "5px 7px", "textAlign": "left", "minWidth": "82px"}, style_header={"backgroundColor": "#eef3f8", "fontWeight": "700", "border": "none"}, style_data={"border": "none", "borderBottom": "1px solid #edf1f5"}),
                        ],
                        className="table-panel",
                    )
                ]
            ),
            html.Section(
                [
                    html.Div(dcc.Graph(id="de-disruption-company", config={"displayModeBar": False}, responsive=True, className="decision-bottom-graph"), className="viz-card decision-bottom-card"),
                    html.Div(dcc.Graph(id="de-signal-cloud", config={"displayModeBar": False}, responsive=True, className="decision-bottom-cloud"), className="viz-card signal-cloud-card decision-bottom-card"),
                ],
                className="dashboard-grid decision-bottom-grid",
            ),
        ],
        className="decision-main",
    )
    return html.Main(
        [
            dcc.Store(id="de-selected-company"),
            page_intro(
                "Narrow the choice",
                None,
                None,
            ),
            html.Div([html.Div(id="de-selection-chips", className="chip-row"), html.Button(id="de-clear-company", n_clicks=0, className="selection-chip company-chip removable-chip", style={"display": "none"}, title="Clear company highlight")], className="journey-summary"),
            html.Div([filters, analysis], className="decision-workspace"),
        ],
        className="page-content",
    )


dash.register_page(__name__, path="/decide", name="AI Disruption Index", order=1, layout=layout)
