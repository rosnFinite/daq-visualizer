import multiprocessing
import time
from dash import Dash, _dash_renderer, Input, Output, State, no_update, callback_context, html
from dash.dcc import Graph, Interval
from numpy import genfromtxt
from plotly_resampler import FigureResampler
import trace_updater
import dash_mantine_components as dmc
import plotly.graph_objects as go
import nidaqmx
import logging

import utility

_dash_renderer._set_react_version("18.2.0")
logger = logging.getLogger(__name__)

app = Dash(
    "DAQ-Dashboard",
    external_stylesheets=dmc.styles.ALL,
    suppress_callback_exceptions=True
)
fig = FigureResampler()

"""
Allgemeiner Aufbau der Oberfläche
- weitere Informationen zu den Komponenten und Parametern -> https://www.dash-mantine-components.com/

# Stack [beinhaltet Titeltext des Dashboards, Kindelemente sind vertikal angeordnet]
# Accordion [übergeordnetes Accordion Objekt]
    # AccordionItem [AccordionItem zur 'Datenaufzeichnung']
        # AccordionControl [Angzeigte Überschrift des AccordionItem]
        # AccordionPanel [Vollständiger Inhalt des AccordionItem]
    # AccordionItem  [AccordionItem zur 'Datenvisualisierung']
        # AccordionControl
        # AccordionPanel
            # Stack 
                # Select [Auswahlfeld der CSV-Datei]
                
"""

app.layout = dmc.MantineProvider(
    children=[
        dmc.NotificationProvider(),
        html.Div(id="notification-container"),
        dmc.Stack(
            children=[
                dmc.Space(h=1),
                dmc.Center(
                    dmc.Text("DAQ-Board Datenaufzeichnungstool", variant="gradient",
                             gradient={"from": "cyan", "to": "indigo", "deg": 45}, fw=800)
                ),
                dmc.Space(h=3),
                dmc.Highlight(
                    "Diese Tool ermöglicht das Aufzeichnen und Betrachten der Daten ausgewählter Eingangskanäle eines "
                    "angeschlossenen DAQ-Boards über die Schaltfläche Datenaufzeichnung. Bereits gespeicherte Messungen "
                    "können über die Schaltfläche Datenvisualisierung ausgewählt und erneut betrachtet werden.",
                    ta="center",
                    highlight=["Datenaufzeichnung", "Datenvisualisierung"], highlightStyles={
                        "backgroundImage": "linear-gradient(45deg, var(--mantine-color-cyan-5), var(--mantine-color-indigo-5))",
                        "fontWeight": 500, "WebkitBackgroundClip": "text", "WebkitTextFillColor": "transparent"}),
                dmc.Space(h=3)
            ]
        ),
        dmc.Accordion(
            chevronPosition="left",
            variant="separated",
            value=["measurement",],
            multiple=True,
            children=[
                dmc.AccordionItem(
                    value="visualization",
                    children=[
                        dmc.AccordionControl("Datenvisualisierung"),
                        dmc.AccordionPanel(
                            [
                                dmc.Stack(
                                    gap="xs",
                                    children=[
                                        dmc.Popover(
                                            [
                                                dmc.PopoverTarget(dmc.Button("Informationen zur Visualisierung")),
                                                dmc.PopoverDropdown([
                                                    dmc.Blockquote("Das Laden größerer Datensätze kann einige Sekunden "
                                                                   "benötigen. Um eine performante Darstellung und "
                                                                   "Interaktion mit der Visualisierung selbst für mehrere "
                                                                   "Millionen von Datenpunkten zu gewährleisten, wird ein "
                                                                   "Resampling-Algorithmus angewendet. Durch vergrößern und "
                                                                   "verkleinern der Ansicht, werden die Datenpunkte aktualisiert."),
                                                    dmc.Blockquote("Falls nach dem Laden des Datensatzes kein Liniengraph "
                                                                   "erkennbar ist, bitte das Dashbord neustarten !", color="red"),
                                                ])
                                            ],
                                            width=500,
                                            position="bottom",
                                            withArrow=True,
                                            shadow="md",
                                            zIndex=2000,
                                        ),
                                        dmc.Center(
                                            dmc.Select(
                                                label="Datensatz wählen",
                                                placeholder="CSV-Datei auswählen",
                                                id="data-selection",
                                                data=utility.get_measurement_file_names(),
                                                w=500
                                            )
                                        ),
                                        dmc.Center(
                                            dmc.Button("Datensatz laden", color="green", id="load-data-btn", loaderProps={"type": "dots"}, loading=False)
                                        ),
                                        Graph("data-plot")
                                    ]
                                )
                            ]
                        )
                    ]
                )
            ]
        ),
        trace_updater.TraceUpdater(id="trace-updater", gdID="data-plot"),
    ]
)



# TODO: Plot vertikal größer machen
@app.callback([
    Output("data-plot", "figure"),
    Output("notification-container", "children"),
], [Input("load-data-btn", "n_clicks"),
    State("data-selection", "value")]
)
def on_load_btn_click(n_clicks, file):
    ctx = callback_context
    if len(ctx.triggered) and "load-data-btn" in ctx.triggered[0]["prop_id"] and file is not None:
        # load data
        data = genfromtxt(file, delimiter=",", skip_header=1)
        global fig
        if len(fig.data):
            fig.replace(go.Figure())

        # num_channles = size of second dimension - 1 (first entry is timestamp)
        num_channels = data.shape[1]-1
        # for every data channel add a trace to plot
        for i in range(num_channels):
            fig.add_trace(go.Scattergl(name=f"ai{i}", hovertemplate="Zeit: %{x}s <br>Y: %{y} </br>"), hf_x=data[:, 0], hf_y=data[:, i+1])
        fig.update_layout(height=700)
        return fig, dmc.Notification(id="loading-notification", title="Messungen geladen",
                                     message="Visualisierung wurde erstellt", autoClose=2000, color="green",
                                     action="update")
    else:
        if n_clicks is None:
            return utility.default_plot, None
        return utility.default_plot , dmc.Notification(
            id="error-notification",
            title="Keine Messungen ausgewählt",
            action="show",
            autoClose=4000,
            color="red",
            message="Es wurde keine Messung zur Visualisierung ausgewählt."
        )

fig.register_update_graph_callback(app=app, graph_id="data-plot", trace_updater_id="trace-updater")

if __name__ == "__main__":
    app.run(debug=True)
