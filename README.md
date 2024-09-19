# DAQ-Visualizer

## Description

The `DAQ-Visualizer` consists of a Python script `daq_reader` designed to acquire data from a National Instruments (NI) DAQ board using specific input channels and store the acquired data as a CSV file in the local file system and a plotly Dash application for a simple visualization of stored measurements. The `daq_reader` script offers several command-line options to customize the acquisition process, such as specifying channels, setting triggers, and defining the sampling rate.

This tool is useful for tasks that involve reading analog signals and storing data for further analysis.

## Features

- Read data from multiple analog input channels.
- Support for trigger-based data acquisition (analog or digital).
- Customizable sampling rate and number of samples.
- Data stored as CSV files for easy analysis.
- Supports continuous and finite data acquisition modes.
- Handles both pre-trigger and post-trigger samples.
- Configurable file overwriting or renaming in case of existing files.

## Requirements

- Python 3.x
- NI-DAQmx
- Required Python libraries:
  - `nidaqmx`
  - `matplotlib`
  - `numpy`
  - `argparse`
  - `csv`
  - `colorama`
  - `dash`
  - `dash-mantine-components`
  - `plotly-resampler`

### Installation

To install the required Python packages, use the provided `environment.yml` to create a conda environment:

```bash
conda create -f environment.yml
```

Ensure that the NI-DAQmx driver is installed on your system to interact with the DAQ device.

## Usage

Run the script from the command line and provide the required arguments to customize the data acquisition.
Be sure to have to corresponding conda environment activated.

### Example Command:

```bash
python daq_reader.py -c ai0 -sr 1000 -f data.csv
```

This command will read data from channel `ai0` at a sampling rate of 1000 Hz and save the data in `data.csv`.

```bash
python dashboard/app.py
```

This command will start the plotly Dash application for easy visualization of stored measurements inside `/data`.

### Command-line Arguments

- `-t, --task_name`: Name of the data acquisition task (default: `AcquisitionTask`).
- `-c, --channel`: Analog input channel to read data from. You can specify multiple channels by providing this argument multiple times (e.g., `-c ai0 -c ai1`).
- `-tc, --trigger_channel`: Channel to use as a trigger (analog or digital). If not provided, data will be acquired continuously.
- `-ts, --trigger_slope`: Defines which slope of the signal to trigger on. Options are `RISING` or `FALLING`.
- `-tl, --trigger_level`: Sets the threshold at which to trigger (value in the units of measurement).
- `-sr, --sampling_rate`: Defines the rate at which samples are read from the channels (must be a positive integer up to 1,000,000 Hz).
- `-ns, --number_of_samples`: Number of samples to read at once. If not specified, all available samples will be read.
- `-f, --filename`: Name of the CSV file to store the data (default: `measurements.csv`).

### Overwriting Files

If a file with the specified name already exists in the `data/` folder, the script will prompt you to either overwrite the file or provide a new name.

### Continuous and Finite Acquisition

- **Continuous Acquisition**: If no trigger is provided, data will be acquired continuously at the specified sampling rate.
- **Finite Acquisition**: If a trigger is provided, a finite number of samples (predefined by the `number_of_samples` argument) will be captured before and after the trigger event.

## Example Workflow

1. Start the script with appropriate arguments, for example:

   ```bash
   python daq_reader.py -c ai0 -sr 1000 -f measurements.csv
   ```

   This starts continuous data acquisition on channel `ai0` at a 1000 Hz sampling rate and saves the data to `measurements.csv`.

2. Optionally, specify a trigger channel and trigger settings:

   ```bash
   python daq_reader.py -c ai0 -sr 1000 -tc ai1 -ts RISING -tl 2.5
   ```

   This triggers data acquisition when the signal on channel `ai1` crosses 2.5 volts on a rising edge.

3. If the output file (`measurements.csv`) already exists, the script will prompt you for a decision:

   ```
   File 'measurements.csv' does already exist inside data/
   Would you like to overwrite it? [y/n]
   ```

4. The acquired data is written to a CSV file. The script prints information about the number of samples and file size in real-time.

## Example CSV Output

The CSV file will contain the following columns:
```
time, channel1, channel2, ...
```

For example:
```csv
time, ai0, ai1
0.0, 1.23, 2.34
0.001, 1.25, 2.35
...
```