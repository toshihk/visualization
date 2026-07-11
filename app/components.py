from dash import dcc, html


def dropdown(component_id, label, options, value=None, multi=True, placeholder="All"):
    return html.Label(
        [html.Span(label, className="filter-label"), dcc.Dropdown(id=component_id, options=options, value=value, multi=multi, placeholder=placeholder, clearable=multi)],
        className="filter-control",
    )


def slider(component_id, label, minimum, maximum, value, step=1, marks=None):
    return html.Label(
        [html.Span(label, className="filter-label"), dcc.Slider(id=component_id, min=minimum, max=maximum, value=value, step=step, marks=marks, tooltip={"placement": "bottom", "always_visible": False})],
        className="filter-control slider-control",
    )


def graph_card(component_id, class_name="viz-card", config=None):
    return html.Div(dcc.Graph(id=component_id, config=config or {"displayModeBar": False}, responsive=True), className=class_name)


def kpi_cards(items):
    return [html.Div([html.Div(value, className="kpi-value"), html.Div(label, className="kpi-label")], className=f"kpi-card {tone}") for label, value, tone in items]


def page_intro(eyebrow, title, body):
    children = [html.P(eyebrow, className="eyebrow")]
    if title:
        children.append(html.H1(title, className="page-title"))
    if body:
        children.append(html.P(body, className="page-subtitle"))
    return html.Section(children, className="page-intro")


def disruption_methodology():
    return html.Details(
        [
            html.Summary("How the AI Disruption Index works"),
            html.P("40% AI replacement risk + 30% AI automation impact + 30% AI adoption level. Layoffs are not part of the index. The resulting 0–100 score is comparative, not predictive."),
        ],
        className="method-note",
    )


def section_heading(title, body):
    return html.Div([html.H2(title), html.P(body)], className="section-heading")
