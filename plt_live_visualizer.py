import nidaqmx
import matplotlib.pyplot as plt
import math
import nidaqmx.constants
import numpy as np

plt.ion() 

"""
WARNING:
Depending on the specified sampling rate and number of samples to read the plotting might crash because the GUI backend won't
handle the rendering. Default settings (sampling_rate = 1000, samples_to_read = 500) are proven to work for up to 8 channel simultaneously, resulting 
in a frame rate of 2 FPS.
"""
# Number of samples per second read by the DAQ board
SAMPLING_RATE = 1000
# number of samples to read per request (via task.read())
SAMPLES_TO_READ = 500
# list of input channels to be read -> e.g. ["ai1"] or ["ai1", "ai2", "ai3"]
# up to 8 input channels can be plotted simultaneusly
CHANNELS = ["ai0","ai1", "ai2", "ai3", "ai4", "ai5", "ai6","ai7"]

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


##################################################################################################################
#                                                                                                                #
#                                                   DAQ Task Creation                                            #
#                                                                                                                #
##################################################################################################################
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
if len(CHANNELS) <= 4:
    fig = plt.figure(figsize=(19,5))
else:
    fig = plt.figure(figsize=(19,11))
fig.canvas.manager.set_window_title("DAQ-Board Visualizer")
axs = create_subplots(num_subplots=len(CHANNELS))

# change x-axis tick labels to display time steps
x = np.linspace(0,SAMPLES_TO_READ,5)
time_labels = np.linspace(-SAMPLES_TO_READ/SAMPLING_RATE, 0, len(x))
time_labels_str = [f"{t:.4f}" for t in time_labels]
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
        # READING DAQ data
        if in_task.in_stream.avail_samp_per_chan == 0:
            continue
        """
        task.read()
        If one channel is selected it will return a list of values for this specific channel
        If multiple channels are selected it will return a multidimensional array where each dimension contains values for specific channel
        
        number_of_samples_per_channel
        In this case a specific amount of data will be read from the internal buffer. By setting
        number_of_samples_per_channel=nidaqmx.constants.READ_ALL_AVAILABLE all available data will be read from the internal buffer.
        More information: https://nidaqmx-python.readthedocs.io/en/stable/task.html#nidaqmx.task.InStream.read 
        """
        data = in_task.read(number_of_samples_per_channel=SAMPLES_TO_READ)
        
        # updating plots with new data
        if len(CHANNELS) > 1:
            for i, line in enumerate(lines):
                line.set_ydata(data[i])
                axs[i].set_ylim([min(data[i]), max(data[i])])
                axs[i].set_xlim([0, SAMPLES_TO_READ])
        else:
            lines[0].set_ydata(data)
            axs[0].set_ylim([min(data), max(data)])
            axs[0].set_xlim([0, SAMPLES_TO_READ])
        fig.tight_layout()
        fig.canvas.draw() 
        fig.canvas.flush_events()
except KeyboardInterrupt:
    in_task.close()

