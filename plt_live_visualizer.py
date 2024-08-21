import nidaqmx
import matplotlib
import matplotlib.pyplot as plt
import math
import numpy as np

print(matplotlib.get_backend())
plt.ion() 

SAMPLING_RATE = 10000
SAMPLES_TO_READ = 1000
# list of input channels to be read -> ["ai1"] / ["ai1", "ai2", "ai3"]
CHANNELS = ["ai1", "ai2"]

def create_subplots(num_subplots: int, max_per_row: int = 4) -> list:
    """ Creates a list of <num_subplots> matplotlib axes objects. Subplots will be created so that if possible 
    each row of the figure contains an equal number of subplots.
    
    Parameters
    ----------
    num_subplots: int
        Number of subplots to be created
    max_per_row: int
        Maximum of subplots per row
    
    Returns
    -------
    list
        A 1d list containing all created subplots 
    """
    axs = []
    num_rows = math.ceil(num_subplots / max_per_row)
    # if only one row is needed
    if num_rows == 1:
        for i in range(num_subplots):
            axs.append(plt.subplot2grid(shape=(num_rows, num_subplots), loc=(0, i)))
        return axs
    
    for row in range(num_rows):
        if row == num_rows-1:
            for i in range(num_subplots - len(axs)):
                axs.append(plt.subplot2grid(shape=(num_rows, max_per_row), loc=(row, i)))
            return axs
        for i in range(max_per_row):
            axs.append(plt.subplot2grid(shape=(num_rows, max_per_row), loc=(row, i)))
    return axs


print("creating task")
in_task = nidaqmx.task.Task(new_task_name="AcquisitionTask")

# add channels to task
for channel in CHANNELS:
    in_task.ai_channels.add_ai_voltage_chan(f"/Dev1/{channel}")

# add timing for data acquisition
in_task.timing.cfg_samp_clk_timing(
    rate=SAMPLING_RATE,
    sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS,
    samps_per_chan=SAMPLES_TO_READ 
)

in_task.start()

# Creating matplotlib figure with subplots
fig = plt.figure(figsize=(15,10))
fig.canvas.manager.set_window_title("DAQ-Board Visualizer")
axs = create_subplots(num_subplots=len(CHANNELS))

# change x-axis tick labels
x = np.linspace(0,1000,10)
time_labels = np.linspace(-SAMPLES_TO_READ/SAMPLING_RATE, 0, len(x))
time_labels_str = [f"{t:.4f}" for t in time_labels]
print(time_labels_str)
plt.setp(axs, xticks=x, xticklabels=time_labels_str)

# correctly title each subplot after corresponding channel and initialize a line plot
lines = []
for i, ax in enumerate(axs):
    ax.set_title(CHANNELS[i])
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Amplitude")
    lines.append(ax.plot(list(range(SAMPLES_TO_READ)), [0 for _ in range(SAMPLES_TO_READ)])[0])
    

 
try:
    while True:
        if in_task.in_stream.avail_samp_per_chan == 0:
            continue
        # will return a list of values if one channel is selected, otherwise a multidimensional list of values for each channel
        data = in_task.read(number_of_samples_per_channel=1000)
        if len(CHANNELS) > 1:
            for i, line in enumerate(lines):
                line.set_ydata(data[i])
                axs[i].set_ylim([min(data[i]), max(data[i])])
                axs[i].set_xlim([0, 1000])
        else:
            lines[0].set_ydata(data)
            axs[0].set_ylim([min(data), max(data)])
            axs[0].set_xlim([0, 1000])
        fig.canvas.draw() 
        fig.canvas.flush_events()
except KeyboardInterrupt:
    in_task.close()

