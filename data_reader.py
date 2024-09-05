import argparse
import csv
import math
import multiprocessing
import os

import numpy as np
import nidaqmx
import matplotlib.pyplot as plt
import nidaqmx.constants
from colorama import just_fix_windows_console, Fore, Style

just_fix_windows_console()
plt.ion()

class UniqueListAction(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super().__init__(option_strings, dest, **kwargs)
    
    def __call__(self, parser, namespace, values, option_string=None):
        if getattr(namespace, self.dest) is None:
            setattr(namespace, self.dest, [values])
        else:
            value_set = set(getattr(namespace, self.dest))
            value_set.add(values)
            setattr(namespace, self.dest, sorted(list(value_set)))
        

parser = argparse.ArgumentParser(
    prog="DAQ-Board-Reader",
    description="This program reads and visualizes the data of specified input channels of a connected DAQ-Board",
)

parser.add_argument("-t", "--task_name", dest="task_name", action="store", type=str, default="AcquisitionTask",
                    help="Name of the data reading task", required=False)
parser.add_argument("-c", "--channel", dest="channels", action=UniqueListAction, 
                    choices=["ai0", "ai1", "ai2", "ai3", "ai4", "ai5", "ai6", "ai7"],
                    help="Channel from which data is to be read (e.g. 'ai0'), multiple channels can be added by providing the argument multiple times",
                    required=True)
parser.add_argument("-sr", "--sampling_rate", dest="sampling_rate", action="store", type=int,
                    help="Rate at which samples are read from provided channels (positive integer up to 1000000)",
                    required=True)
parser.add_argument("-ns", "--number_of_samples", dest="number_of_samples", action="store", type=int,
                    help="Number of samples to be read at once. If not provided all available samples will be read on read.",
                    required=True)
parser.add_argument("-v", "--visualize", dest="visualize", action="store_true", default=False,
                    help="Live visualization of read data. Can be problematic for high sampling rate and number of samples to read! Default: False")
parser.add_argument("-f", "--filename", dest="filename", action="store", type=str, default="measurements.csv",
                    help="Filename to which read data will be written (has to be a csv file) stored inside data folder. Default: measurements.csv")

args = parser.parse_args()


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


def main_data_loop(data_q):
    # creating task
    in_task = nidaqmx.task.Task(new_task_name=args.task_name) 
    for channel in args.channels:
        in_task.ai_channels.add_ai_voltage_chan(f"/Dev1/{channel}")
    in_task.timing.cfg_samp_clk_timing(
        rate=args.sampling_rate,
        sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS,
        samps_per_chan=args.number_of_samples
    )
    in_task.start()
    
    if args.visualize:
        # Creating matplotlib figure with subplots
        if len(args.channels) <= 4:
            fig = plt.figure(figsize=(19,5))
        else:
            fig = plt.figure(figsize=(19,11))
        fig.canvas.manager.set_window_title("DAQ-Board Visualizer")
        axs = create_subplots(num_subplots=len(args.channels))

        # change x-axis tick labels to display time steps
        x = np.linspace(0,args.number_of_samples, 5)
        time_labels = np.linspace(-args.number_of_samples/args.sampling_rate, 0, len(x))
        time_labels_str = [f"{t:.4f}" for t in time_labels]
        plt.setp(axs, xticks=x, xticklabels=time_labels_str)

        # correctly title each subplot after corresponding channel and initialize a line plot
        lines = []
        for i, ax in enumerate(axs):
            ax.set_title(args.channels[i])
            ax.set_xlabel("Time (s)")
            ax.set_ylabel("Amplitude")
            lines.append(ax.plot(list(range(args.number_of_samples)), [0 for _ in range(args.number_of_samples)])[0])
        
    try:
        while True:
            # main data reading logic
            if in_task.in_stream.avail_samp_per_chan == 0:
                continue
            data = in_task.read(number_of_samples_per_channel=args.number_of_samples)
            data_q.put(data)
            
            if args.visualize:
                # updating plots with new data
                if len(args.channels) > 1:
                    for i, line in enumerate(lines):
                        line.set_ydata(data[i])
                        axs[i].set_ylim([min(data[i]), max(data[i])])
                        axs[i].set_xlim([0, args.number_of_samples])
                else:
                    lines[0].set_ydata(data)
                    axs[0].set_ylim([min(data), max(data)])
                    axs[0].set_xlim([0, args.number_of_samples])
                fig.tight_layout()
                fig.canvas.draw() 
                fig.canvas.flush_events()
    except KeyboardInterrupt:
        in_task.close()
        
        
def write_to_file(filename, channels, sampling_rate, data_q):
    print(f"Saving samples in 'data/{filename}")
    try:
        with open(f"data/{filename}", "w+", newline="") as f:
            csv_writer = csv.writer(f)
            header = ["time"]
            header.extend(channels)
            # csv header
            csv_writer.writerow(header)
            timestamp = 0
            total_samples = 0
            while True:
                samples = data_q.get()
                total_samples += len(samples)
                for item in samples:
                    csv_writer.writerow([timestamp, item])
                    timestamp += 1/sampling_rate
                print(Fore.GREEN + "#samples: " + Style.RESET_ALL + f"{total_samples:<15}" + Fore.GREEN + 5 * " " +"file_size: " + Style.RESET_ALL + f"{os.stat(f'data/{filename}').st_size / (1024 * 1024):.2f} Mb" + Style.RESET_ALL)
    except KeyboardInterrupt:
        print("")

if __name__ == "__main__":
    data_q = multiprocessing.Queue()
    
    write_process = multiprocessing.Process(target=write_to_file, args=(args.filename, args.channels, args.sampling_rate, data_q,))
    write_process.start()
    
    main_data_loop(data_q)
    write_process.join()