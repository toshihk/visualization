import importlib
import os

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, html
from flask import redirect, request

from app.callbacks import register_callbacks
from app.constants import ROOT_DIR
from app.data_loader import ProcessedDataMissingError, load_bridge, load_layoffs, load_profile, load_workforce
from app.layout import build_shell


def missing_data_layout(error: Exception):
    return html.Div([html.H1("Processed data is missing"), html.P(str(error)), html.Pre("source .venv/bin/activate\npython -m app.preprocess\npython -m app.main")], className="missing-data")


def create_app():
    app = dash.Dash(
        __name__,
        use_pages=True,
        pages_folder="",
        assets_folder=str(ROOT_DIR / "assets"),
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        suppress_callback_exceptions=True,
        title="The Guide for Job Seekers",
        update_title="Reading the market…",
    )
    try:
        workforce = load_workforce()
        layoffs = load_layoffs()
        bridge = load_bridge()
        profile = load_profile()
    except ProcessedDataMissingError as exc:
        app.layout = missing_data_layout(exc)
        return app

    importlib.import_module("app.pages.explore")
    importlib.import_module("app.pages.decide")
    app.layout = build_shell(profile)
    register_callbacks(app, workforce, layoffs, bridge, profile)

    @app.server.before_request
    def redirect_home_to_explore():
        if request.path == "/":
            return redirect("/explore")

    app.clientside_callback(
        "function(pathname) { window.scrollTo(0, 0); return pathname; }",
        Output("scroll-sentinel", "data"),
        Input("url", "pathname"),
    )
    return app


app = create_app()
server = app.server


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 8888)))
