from dash import Dash, _dash_renderer, Input, Output, State, no_update, callback_context, html
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

"""
Allgemeiner Aufbau der Oberfläche
- weitere Informationen zu den Komponenten und Parametern -> https://www.dash-mantine-components.com/

# Accordion [übergeordnetes Accordion Objekt]
    # AccordionItem [AccordionItem zur 'Datenaufzeichnung']
        # AccordionControl [Angzeigte Überschrift des AccordionItem]
        # AccordionPanel [Vollständiger Inhalt des AccordionItem]
    # AccordionItem  [AccordionItem zur 'Datenvisualisierung']
        # AccordionControl
        # AccordionPanel
            # Stack [steuert vertikale Anordnung von Kindelementen]
                # Select [Auswahlfeld der CSV-Datei]
                # Space [visueller Abstand zwischen zwei Komponenten]
                
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
                    "Diese Tool ermöglicht das Aufzeichnen und Betrachten von ausgewählten Datenkanälen eines "
                    "angeschlossenen DAQ-Boards über die Schaltfläche Datenaufzeichnung. Bereits erfasste Aufnahmen "
                    "können über die Schaltfläche Datenvisualisierung erneut betrachtet werden.",
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
            children=[
                dmc.AccordionItem(
                    value="measurement",
                    children=[
                        dmc.AccordionControl(
                            "Datenaufzeichnung",
                        ),
                        dmc.AccordionPanel(
                            children=[
                                dmc.Blockquote(
                                    "Die 'Abtastrate in Hz' gibt die Anzahl an Messungen pro Sekunde an, während über "
                                    "die 'Messungen pro Abfrage' die Abfragerate der gemessenen Daten aus dem internen "
                                    "Puffer des DAQ-Boards zum PC geregelt wird. Bei einer Abtastrate von 10.000 Hz und "
                                    "1.000 Messungen pro Abfrage, werden 10x in der Sekunde die Daten aus dem internen "
                                    "Puffer des DAQ-Boards gezogen, visualisiert und gespeichert."),
                                dmc.Space(h=10),
                                dmc.SimpleGrid(cols=2, spacing="md", children=[
                                    dmc.NumberInput(label="Abtastrate in Hz", description="Von 1 bis 1.000.000 Hz",
                                                    value=10000, min=1, max=1000000),
                                    dmc.NumberInput(label="Messungen pro Abfrage", description="Von 1 bis 1.000.000",
                                                    value=1000, min=1, max=1000000)]),
                                dmc.Space(h=5),
                                dmc.MultiSelect(
                                    label="Datenkanäle auswählen",
                                    placeholder="Alle zu erfassenden Kanäle wählen",
                                    id="data-input-channels-select",
                                    data=[
                                        {"value": "ai0", "label": "AI 0"},
                                        {"value": "ai1", "label": "AI 1"},
                                        {"value": "ai2", "label": "AI 2"},
                                        {"value": "ai3", "label": "AI 3"},
                                        {"value": "ai4", "label": "AI 4"},
                                        {"value": "ai5", "label": "AI 5"},
                                        {"value": "ai6", "label": "AI 6"},
                                        {"value": "ai7", "label": "AI 7"}
                                    ]
                                )
                            ]
                        )
                    ]
                ),
                dmc.AccordionItem(
                    value="visualization",
                    children=[
                        dmc.AccordionControl("Datenvisualisierung"),
                        dmc.AccordionPanel(
                            [
                                dmc.Stack(
                                    gap="xs",
                                    children=[
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
                                            dmc.Button("Datensatz laden", color="green", id="load-data-btn")
                                        ),
                                        Graph(id="data-plot")
                                    ]
                                )
                            ]
                        )
                    ]
                )
            ]
        ),
        trace_updater.TraceUpdater(id="trace-updater", gdID="data-plot")
    ]
)


# TODO: Plot vertikal größer machen
@app.callback([
    Output("data-plot", "figure"),
    Output("notification-container", "children", allow_duplicate=True)
], [Input("load-data-btn", "n_clicks"),
    State("data-selection", "value")],
    prevent_initial_call=True
)
def on_load_btn_click(n_clicks, value):
    ctx = callback_context
    if len(ctx.triggered) and "load-data-btn" in ctx.triggered[0]["prop_id"] and value is not None:
        # load data
        data = genfromtxt(value, delimiter=",", skip_header=1)
        global fig
        if len(fig.data):
            fig.replace(go.Figure())

        fig.add_trace(go.Scattergl(name="data"), hf_x=data[:, 0], hf_y=data[:, 1])
        fig.update_layout(height=400)
        return fig, dmc.Notification(id="loading-notification", title="Messungen geladen",
                                     message="Visualisierung wurde erstellt", autoClose=2000, color="green",
                                     action="update")
    else:
        return None, dmc.Notification(
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
