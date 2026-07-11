import dash
from dash import dcc, html

from app.constants import DEFAULT_JOURNEY


def build_shell(profile: dict):
    return html.Div(
        [
            dcc.Location(id="url", refresh="callback-nav"),
            dcc.Store(id="journey-state", storage_type="session", data=DEFAULT_JOURNEY),
            dcc.Store(id="scroll-sentinel"),
            html.Header(
                [
                    dcc.Link(
                        [html.Img(src="/assets/job-guide-icon.svg", alt="Career opportunity guide", className="brand-mark"), html.Div([html.Strong("The Guide for Job Seekers"), html.Span("The AI Disruption Index: Mapping Layoffs, Hiring Trends, and Workforce Restructuring in Tech.")], className="brand-copy")],
                        href="/explore",
                        className="brand",
                    ),
                    html.Nav([dcc.Link("Explore", id="nav-explore", href="/explore", className="nav-link"), dcc.Link("Discover", id="nav-decide", href="/decide", className="nav-link")], className="top-nav"),
                ],
                className="app-header",
            ),
            dash.page_container,
            html.Footer(
                [html.Strong("The Guide for Job Seekers"), html.Span(f"{profile.get('workforce_rows', 0):,} workforce records · {profile.get('layoffs_rows', 0):,} market records · six covered markets")],
                className="app-footer",
            ),
        ],
        className="app-shell",
    )
