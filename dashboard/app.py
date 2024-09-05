from dash import Dash, _dash_renderer, Input, Output, State, no_update, callback_context
from dash.dcc import Graph
from numpy import genfromtxt
from plotly_resampler import FigureResampler
import trace_updater
import dash_mantine_components as dmc
import plotly.graph_objects as go
import utility

_dash_renderer._set_react_version("18.2.0")

app = Dash(
    "DAQ-Dashboard",
    external_stylesheets=dmc.styles.ALL
)
fig = FigureResampler()

app.layout = dmc.MantineProvider(
    dmc.Stack(
        [
            dmc.Container([
                dmc.Select(
                    label="Datensatz auswählen",
                    placeholder="Datei hinzufügen",
                    id="data-selection",
                    data=utility.get_measurement_file_names(),
                    w=500
                    ),
                dmc.Space(h=5),
                dmc.Center(
                    dmc.Button("Datensatz laden", color="green", id="load-data-btn")
                )
            ]),
            Graph(id="data-plot"),
            trace_updater.TraceUpdater(id="trace-updater", gdID="data-plot")
        ]
    )
)

@app.callback(
    Output("data-plot", "figure"),
    Input("load-data-btn", "n_clicks"),
    State("data-selection", "value"),
    prevent_initial_call=True
)
def on_load_btn_click(n_clicks, value):
    ctx = callback_context
    if len(ctx.triggered) and "load-data-btn" in ctx.triggered[0]["prop_id"]:
        # load data
        data = genfromtxt(value, delimiter=",", skip_header=1)
        global fig
        if len(fig.data):
            fig.replace(go.Figure())
            
        fig.add_trace(go.Scattergl(name="data"), hf_x = data[:, 0], hf_y = data[:, 1])
        return fig
    else:
        no_update

fig.register_update_graph_callback(app=app, graph_id="data-plot", trace_updater_id="trace-updater")

if __name__ == "__main__":
    app.run(debug=True)