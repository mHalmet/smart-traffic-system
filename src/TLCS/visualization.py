import matplotlib.pyplot as plt
import os

class Visualization:
    def __init__(self, path, dpi):
            self._path = path
            self._dpi = dpi


    def save_data_and_plot(self, data, filename, xlabel, ylabel,tl_names):
        """
        Produce a plot of performance of the agent over the session and save the relative data to txt
        """
        for tl_name in tl_names:

            min_val = min(data[tl_name])
            max_val = max(data[tl_name])

            plt.rcParams.update({'font.size': 24})  # set bigger font size

            plt.plot(data[tl_name])
            plt.ylabel(ylabel)
            plt.xlabel(xlabel)
            plt.margins(0)
            plt.ylim(min_val - 0.05 * abs(min_val), max_val + 0.05 * abs(max_val))
            fig = plt.gcf()
            fig.set_size_inches(20, 11.25)
            fig.savefig(os.path.join(self._path, 'plot_'+filename+'_'+tl_name+'.png'), dpi=self._dpi)
            plt.close("all")

            with open(os.path.join(self._path, 'plot_'+filename + '_data_'+tl_name+'.txt'), "w") as file:
                for value in data[tl_name]:
                        file.write("%s\n" % value)
    