import matplotlib.pyplot as plt
import plotly.express as px
import pandas as pd
import plotly.graph_objects as go

import os

class Visualization:
    def __init__(self, path, dpi):
            self._path = path
            self._dpi = dpi


    def save_data_and_plot(self, data, filename, xlabel, ylabel,tl_names):
        """
        Produce a plot of performance of the agent over the session and save the relative data to txt
        """
        import plotly.graph_objects as go

        x = [*range(15)]

        plotly_fig = go.Figure()


        for tl_name in tl_names:
            plotly_fig.add_trace(go.Scatter(
                x=[*range(len(data[tl_name]))],
                y=data[tl_name],
                connectgaps=True  # override default to connect the gaps
            ))

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

        plotly_fig.write_image(self._path+"/"+filename+"_plot_plotly.png")