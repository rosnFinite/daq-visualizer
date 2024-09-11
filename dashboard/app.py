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
live_figs = {k: FigureResampler() for k in ["ai0", "ai1", "ai2", "ai3", "ai4", "ai5", "ai6", "ai7"]}
in_task = nidaqmx.task.Task(new_task_name="AcquisitionTask")
join_process_flag = multiprocessing.Event()
live_data_q = multiprocessing.Queue()
acquire_data_process = None


def acquire_data_loop(live_data_q, channels, sampling_rate, num_samps_per_read):
    global in_task
    for channel in channels:
        in_task.ai_channels.add_ai_voltage_chan(f"/Dev1/{channel}")
    in_task.timing.cfg_samp_clk_timing(
        rate=sampling_rate,
        sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS,
        samps_per_chan=num_samps_per_read
    )
    in_task.start()
    print("start loop")
    
    while join_process_flag.is_set():
        data = in_task.read(number_of_samples_per_channel=num_samps_per_read)
        live_data_q.put(data)
        logger.log(data)
    in_task.close()
    

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
                                    dmc.NumberInput(id="sampling-rate-input", label="Abtastrate in Hz", description="Von 1 bis 1.000.000 Hz",
                                                    value=10000, min=1, max=1000000),
                                    dmc.NumberInput(id="num-measurements-input", label="Messungen pro Abfrage", description="Von 1 bis 1.000.000",
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
                                ),
                                dmc.Space(h=5),
                                dmc.Center(dmc.ButtonGroup([
                                    dmc.Button(id="start-task-btn", children=["Starte Taks"], color="green", disabled=True),
                                    dmc.Button(id="stop-task-btn", children=["Stoppe Task"], color="red", disabled=True)
                                ])),
                                dmc.Center(dmc.Text(id="task-status-text", children=["Task Status: ", dmc.Mark("Offline", color="red")])),
                                dmc.SimpleGrid(id="live-plot-grid", cols=1, children=[
                                    html.Div(id="live-plot-ai0-div", children=[Graph("live-plot-ai0")], style={'display':'none'}),
                                    html.Div(id="live-plot-ai1-div", children=[Graph("live-plot-ai1")], style={'display':'none'}),
                                    html.Div(id="live-plot-ai2-div", children=[Graph("live-plot-ai2")], style={'display':'none'}),
                                    html.Div(id="live-plot-ai3-div", children=[Graph("live-plot-ai3")], style={'display':'none'}),
                                    html.Div(id="live-plot-ai4-div", children=[Graph("live-plot-ai4")], style={'display':'none'}),
                                    html.Div(id="live-plot-ai5-div", children=[Graph("live-plot-ai5")], style={'display':'none'}),
                                    html.Div(id="live-plot-ai6-div", children=[Graph("live-plot-ai6")], style={'display':'none'}),
                                    html.Div(id="live-plot-ai7-div", children=[Graph("live-plot-ai7")], style={'display':'none'}),
                                ])
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
        Interval(id="interval-component",
                interval=1000, # in milliseconds
                n_intervals=0
        ),
        trace_updater.TraceUpdater(id="trace-updater", gdID="data-plot"),
        trace_updater.TraceUpdater(id="trace-updater-ai0", gdID="live-plot-ai0"),
        trace_updater.TraceUpdater(id="trace-updater-ai1", gdID="live-plot-ai1"),
        trace_updater.TraceUpdater(id="trace-updater-ai2", gdID="live-plot-ai2"),
        trace_updater.TraceUpdater(id="trace-updater-ai3", gdID="live-plot-ai3"),
        trace_updater.TraceUpdater(id="trace-updater-ai4", gdID="live-plot-ai4"),
        trace_updater.TraceUpdater(id="trace-updater-ai5", gdID="live-plot-ai5"),
        trace_updater.TraceUpdater(id="trace-updater-ai6", gdID="live-plot-ai6"),
        trace_updater.TraceUpdater(id="trace-updater-ai7", gdID="live-plot-ai7"),
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


@app.callback(Output("start-task-btn", "disabled", allow_duplicate=True), 
              Input("data-input-channels-select", "value"), 
              prevent_initial_call=True)
def handle_start_task_btn_on_channels_selected(channels):
    if channels is None:
        return True
    return False        
        

@app.callback([
     Output("live-plot-grid", "cols"),
     Output("live-plot-ai0-div", "style"),
     Output("live-plot-ai0", "figure", allow_duplicate=True),
     Output("live-plot-ai1-div", "style"),
     Output("live-plot-ai1", "figure", allow_duplicate=True),  
     Output("live-plot-ai2-div", "style"),
     Output("live-plot-ai2", "figure", allow_duplicate=True),  
     Output("live-plot-ai3-div", "style"),
     Output("live-plot-ai3", "figure", allow_duplicate=True),  
     Output("live-plot-ai4-div", "style"),
     Output("live-plot-ai4", "figure", allow_duplicate=True),  
     Output("live-plot-ai5-div", "style"),
     Output("live-plot-ai5", "figure", allow_duplicate=True),  
     Output("live-plot-ai6-div", "style"),
     Output("live-plot-ai6", "figure", allow_duplicate=True),  
     Output("live-plot-ai7-div", "style"),
     Output("live-plot-ai7", "figure", allow_duplicate=True),   
], [Input("start-task-btn", "n_clicks"), State("data-input-channels-select", "value")], prevent_initial_call=True
)
def create_subplots_on_start_task_btn_click(n_clicks, selected_channels):
    if selected_channels is None:
        return no_update
    selected_channels = sorted(selected_channels)
    global live_figs
    output = [3 if len(selected_channels) > 2 else 1]
    for channel in ["ai0", "ai1", "ai2", "ai3", "ai4", "ai5", "ai6", "ai7"]:
        if channel in selected_channels:
            live_figs[channel].replace(go.Figure())
            live_figs[channel].update_layout(title_text=f"{channel}", margin=dict(l=20, r=20, t=50, b=50))
            output.append({"display": "block"})
            output.append(live_figs[channel])
        else:
            output.append({"display": "none"})
            output.append(None)
    return output


@app.callback([
    Output("task-status-text", "children", allow_duplicate=True),
    Output("start-task-btn", "disabled", allow_duplicate=True),
    Output("stop-task-btn", "disabled", allow_duplicate=True),
    Output("interval-component", "interval"),
], [
    Input("start-task-btn", "n_clicks"), 
    State("data-input-channels-select", "value"),
    State("sampling-rate-input", "value"),
    State("num-measurements-input", "value")], 
prevent_initial_call=True)
def start_task_on_start_task_btn_click(n_clicks, channels, sampling_rate, num_samps_per_read):
    if channels is None:
        ["Task Status: ", dmc.Mark("Online", color="green")], True, False, 1000
    global live_data_q
    global acquire_data_process
    print("Starting process")
    acquire_data_process = multiprocessing.Process(target=acquire_data_loop, args=(live_data_q, channels, sampling_rate, num_samps_per_read,))
    acquire_data_process.start()
    print("done")
    return ["Task Status: ", dmc.Mark("Online", color="green")], True, False, 1000 / (sampling_rate / num_samps_per_read)


@app.callback([
    Output("task-status-text", "children", allow_duplicate=True),
    Output("start-task-btn", "disabled", allow_duplicate=True),
    Output("stop-task-btn", "disabled", allow_duplicate=True)
], [Input("stop-task-btn", "n_clicks")], prevent_initial_call=True)
def stop_task_on_stop_task_btn_click(n_clicks):
    global join_process_flag
    global acquire_data_process
    join_process_flag.set()
    acquire_data_process.join()
    join_process_flag.clear()
    return ["Task Status: ", dmc.Mark("Offline", color="red")], False, True


@app.callback([
    Output("live-plot-ai0", "figure", allow_duplicate=True),
    Output("live-plot-ai1", "figure", allow_duplicate=True),
    Output("live-plot-ai2", "figure", allow_duplicate=True),
    Output("live-plot-ai3", "figure", allow_duplicate=True),
    Output("live-plot-ai4", "figure", allow_duplicate=True),
    Output("live-plot-ai5", "figure", allow_duplicate=True),
    Output("live-plot-ai6", "figure", allow_duplicate=True),
    Output("live-plot-ai7", "figure", allow_duplicate=True),
], [Input("interval-component", "n_intervals"), State("data-input-channels-select", "value")], prevent_initial_call=True)
def update_live_plots(n_intervals, selected_channels):
    if selected_channels is None:
        return [None] * 8
    selected_channels = sorted(selected_channels)
    global live_figs
    global live_data_q
    print("get data")
    data = live_data_q.get()
    print(data)
    channel_num = 0
    output = []
    for channel in ["ai0", "ai1", "ai2", "ai3", "ai4", "ai5", "ai6", "ai7"]:
        if channel in selected_channels:
            live_figs[channel].add_trace(go.Scattergl(name=f"{channel}", hovertemplate="Zeit: %{x}s <br>Y: %{y} </br>"), hf_x=list(range(len(data))), hf_y=data[channel_num])
            channel_num += 1
            output.append(live_figs[channel])
        else:
            output.append(None)
    return output
        

fig.register_update_graph_callback(app=app, graph_id="data-plot", trace_updater_id="trace-updater")
for channel in live_figs:
    live_figs[channel].register_update_graph_callback(app=app, graph_id=f"live-plot-{channel}", trace_updater_id=f"trace-updater-{channel}")

if __name__ == "__main__":
    app.run(debug=True)
