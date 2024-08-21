from dash import Dash, _dash_renderer
import dash_mantine_components as dmc
_dash_renderer._set_react_version("18.2.0")

app = Dash(
    "DAQ-Dashboard",
    external_stylesheets=dmc.styles.ALL
)

app.layout = dmc.MantineProvider(
    dmc.Alert(
       "Hi from Dash Mantine Components. You can create some great looking dashboards using me!",
       title="Welcome!",
       color="violet",
    )
)


if __name__ == "__main__":
    app.run(debug=True)