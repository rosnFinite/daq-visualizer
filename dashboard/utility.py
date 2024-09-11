from typing import List
import os

module_path = os.path.abspath(__file__)
module_dir = os.path.dirname(module_path)

default_plot = {
    "layout": {
        "xaxis": {
            "visible": False
        },
        "yaxis": {
            "visible": False
        },
        "annotations": [
            {
                "text": "Keine Daten zum Visualisieren",
                "xref": "paper",
                "yref": "paper",
                "showarrow": False,
                "font": {
                    "size": 20
                }
            }
        ]
    }
}


def get_measurement_file_names() -> List[dict[str, str]]:
    return [{"value": os.path.join(root, file), "label": file}
            for root, _, files in os.walk(os.path.abspath(os.path.join(module_dir, "..", "data"))) 
            for file in files if file.endswith(".csv")]
