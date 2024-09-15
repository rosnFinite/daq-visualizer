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
    """
    Custom argparse Action to accumulate unique values into a list.

    This action ensures that all values are added to a list with no duplicates.
    Insertion order of unique elements is not preserved.
    List of unique elements is sorted lexicographically.

    Parameters
    ----------
    option_strings : list
        The option strings associated with this action.
    dest : str
        The name of the attribute to hold the values.
    nargs : None, optional
        Not allowed. Will raise ValueError if set.
    **kwargs : dict
        Additional keyword arguments to pass to the superclass.

    Raises
    ------
    ValueError
        If 'nargs' is provided, as it's not allowed for this action.

    Examples
    --------
    >>> parser = argparse.ArgumentParser()
    >>> parser.add_argument('--unique', action=UniqueListAction)
    >>> args = parser.parse_args(['--unique', 'c', '--unique', 'b', '--unique', 'a', '--unique', 'c'])
    >>> print(args.unique)
    ['a', 'b', 'c']
    """
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

parser.add_argument("-t", "--task_name", dest="task_name", action="store", type=str,
                    default="AcquisitionTask",
                    help="Name of the data reading task", required=False)
parser.add_argument("-c", "--channel", dest="channels", action=UniqueListAction,
                    choices=["ai0", "ai1", "ai2", "ai3", "ai4", "ai5", "ai6", "ai7"],
                    help="Channel from which data is to be read (e.g. 'ai0'), multiple channels can be added by "
                         "providing the argument multiple times",
                    required=True)
parser.add_argument("-tc", "--trigger_channel", dest="trigger_channel", action="store", type=str,
                    default=None,
                    choices=["ai0", "ai1", "ai2", "ai3", "ai4", "ai5", "ai6", "ai7"])
parser.add_argument("-sr", "--sampling_rate", dest="sampling_rate", action="store", type=int,
                    help="Rate at which samples are read from provided channels (positive integer up to 1000000)",
                    required=True)
parser.add_argument("-ns", "--number_of_samples", dest="number_of_samples", action="store", type=int,
                    help="Number of samples to be read at once. If not provided all available samples will be read "
                         "on read.", default=None)
parser.add_argument("-v", "--visualize", dest="visualize", action="store_true", default=False,
                    help="Live visualization of read data. Can be problematic for high sampling rate and number of "
                         "samples to read! Default: False")
parser.add_argument("-f", "--filename", dest="filename", action="store", type=str,
                    default="measurements.csv",
                    help="Filename to which read data will be written (has to be a csv file) stored inside data "
                         "folder. Default: measurements.csv")

args = parser.parse_args()


def main_data_loop(data_q):
    print("Starting " + Fore.BLUE + f"{args.task_name}" + Style.RESET_ALL)
    print("Input channels: " + Fore.BLUE + str(args.channels) + Style.RESET_ALL)
    print("Trigger channel: " + Fore.BLUE + f"{args.trigger_channel if args.trigger_channel is not None else 'None'}" +
          Style.RESET_ALL)
    print("Sampling rate: " + Fore.BLUE + str(args.sampling_rate) + "Hz" + Style.RESET_ALL)
    if args.number_of_samples is None:
        print("Number of samples per read: " + Fore.BLUE +
              f"{'READ ALL' if args.trigger_channel is None else args.sampling_rate}" + Style.RESET_ALL)
    else:
        print("Number of samples per read: " + Fore.BLUE + str(args.number_of_samples) + Style.RESET_ALL)
    # creating task
    in_task = nidaqmx.task.Task(new_task_name=args.task_name)
    for channel in args.channels:
        in_task.ai_channels.add_ai_voltage_chan(f"/Dev1/{channel}")
    in_task.timing.cfg_samp_clk_timing(
        rate=args.sampling_rate,
        sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS,
        samps_per_chan=args.number_of_samples
    )

    # setting reference signal for analog input task
    if args.trigger_channel is not None:
        in_task.triggers.reference_trigger.cfg_anlg_edge_ref_trig(
            trigger_source=f"/Dev1/{args.trigger_channel}",
            pretrigger_samples=args.number_of_samples
        )
    in_task.start()

    try:
        while True:
            # main data reading logic
            if in_task.in_stream.avail_samp_per_chan == 0:
                continue
            if args.trigger_channel is None:
                data = in_task.read(number_of_samples_per_channel=args.number_of_samples)
            else:
                data = in_task.read(number_of_samples_per_channel=args.number_of_samples,
                                    timeout=nidaqmx.constants.WAIT_INFINITELY)
            data_q.put(data)
    except KeyboardInterrupt:
        in_task.close()


def write_to_file(filename, channels, sampling_rate, data_q):
    print("Saving samples in"+ Fore.RED +  f"'data/{filename}" + Style.RESET_ALL)
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
                # pair measured values for each channel into one element => e.g. 3 samples for 2 channels
                # [[1,2,3],[4,5,6]] => [(1,4),(2,5),(3,6)]
                if len(channels) > 1:
                    samples = list(zip(*samples))
                total_samples += len(samples)
                for item in samples:
                    # in case measurements of multiple channels were paired
                    if type(item) is tuple:
                        csv_writer.writerow([timestamp, *item])
                    else:
                        csv_writer.writerow([timestamp, item])
                    timestamp += 1 / sampling_rate
                print(
                    Fore.GREEN + "#samples per channel: " + Style.RESET_ALL + f"{total_samples:<15}" + Fore.GREEN +
                    5 * " " + "file_size: " + Style.RESET_ALL +
                    f"{os.stat(f'data/{filename}').st_size / (1024 * 1024):.2f} Mb" + Style.RESET_ALL)
    except KeyboardInterrupt:
        print("")


if __name__ == "__main__":
    data_q = multiprocessing.Queue()

    write_process = multiprocessing.Process(target=write_to_file,
                                            args=(args.filename, args.channels, args.sampling_rate, data_q,))
    write_process.start()

    main_data_loop(data_q)
    write_process.join()
