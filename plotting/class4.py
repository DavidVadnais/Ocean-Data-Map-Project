from textwrap import wrap

import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np

# from flask_babel import gettext
from netCDF4 import Dataset, chartostring

import plotting.utils as utils
from oceannavigator.settings import get_settings
from plotting.plotter import Plotter

settings = get_settings()


class Class4Plotter(Plotter):
    def __init__(self, dataset_name: str, query: str, **kwargs):
        self.plottype: str = "class4"
        self.class4_type: str = None
        super(Class4Plotter, self).__init__(dataset_name, query, **kwargs)

    def parse_query(self, query):
        super(Class4Plotter, self).parse_query(query)

        class4 = query.get("class4id")
        if isinstance(class4, str):
            class4 = class4.split(",")

        self.class4 = np.array([c.rsplit("_", 1) for c in class4])
        self.forecast = query.get("forecast")
        self.climatology = query.get("climatology") is None or bool(
            query.get("climatology")
        )
        self.error = query.get("error")
        self.class4_type = query.get("class4type")

        if self.class4_type == "ocean_predict":
            self.fname_pattern = settings.class4_op_path
        else:
            self.fname_pattern = settings.class4_rao_path
        self.fname_pattern += settings.class4_fname_pattern

        models = query.get("models")
        if models is None:
            models = []

        self.models = models

    def load_data(self):
        indices = self.class4[:, 1].astype(int)
        # Expecting specific class4 ID format: "class4_YYYMMDD_*.nc"

        with Dataset(
            self.fname_pattern
            % (self.class4[0][0][7:11], self.class4[0][0][7:15], self.class4[0][0]),
            "r",
        ) as ds:
            self.latitude = ds["latitude"][indices]
            self.longitude = ds["longitude"][indices]
            self.ids = list(map(str.strip, chartostring(ds["id"][indices])))

            self.variables = list(map(str.strip, chartostring(ds["varname"][:])))
            self.variable_units = list(map(str.strip, chartostring(ds["unitname"][:])))

            forecast_data = []
            observed_data = []
            climatology_data = []
            depths = []
            for i in indices:
                f_data = []
                o_data = []
                c_data = []
                for j in range(0, len(self.variables)):
                    if self.forecast == "best":
                        f_data.append(ds["best_estimate"][i, j, :])
                    else:
                        f_data.append(ds["forecast"][i, j, int(self.forecast), :])
                    o_data.append(ds["observation"][i, j, :])
                    c_data.append(ds["climatology"][i, j, :])
                forecast_data.append(np.ma.vstack(f_data))
                observed_data.append(np.ma.vstack(o_data))
                climatology_data.append(np.ma.vstack(c_data))
                depths.append(ds["depth"][i, :])

            self.depth_unit = ds["depth"].units

        self.forecast_data = np.ma.array(forecast_data)
        self.observed_data = np.ma.array(observed_data)
        self.climatology_data = np.ma.array(climatology_data)
        self.depths = np.ma.vstack(depths)

        additional_model_data = []
        additional_model_names = []
        for m in self.models:
            additional_model_names.append(m.split("_")[2])
            # Expecting specific class4 ID format: "class4_YYYMMDD_*.nc"

            with Dataset(self.fname_pattern % (m[7:11], m[7:15], m), "r") as ds:
                m_data = []
                for i in indices:
                    data = []
                    for j in range(0, len(self.variables)):
                        data.append(ds["best_estimate"][i, j, :])
                    m_data.append(np.ma.vstack(data))

                additional_model_data.append(np.ma.array(m_data))

        self.additional_model_data = np.ma.array(additional_model_data)
        self.additional_model_names = additional_model_names

    def csv(self):
        header = []
        columns = ["ID", "Latitude", "Longitude", "Depth"]
        for v in self.variables:
            columns.extend(["%s Model" % v, "%s Observed" % v, "%s Climatology" % v])

        data = []
        for p_idx in range(0, len(self.ids)):
            for idx in range(0, len(self.depths[p_idx])):
                if self.observed_data[p_idx, :, idx].mask.all():
                    continue

                entry = [
                    self.ids[p_idx],
                    "%0.4f" % self.latitude[p_idx],
                    "%0.4f" % self.longitude[p_idx],
                    "%0.1f" % self.depths[p_idx][idx],
                ]
                for v in range(0, len(self.variables)):
                    entry.extend(
                        [
                            "%0.1f" % self.forecast_data[p_idx, v, idx],
                            "%0.1f" % self.observed_data[p_idx, v, idx],
                            "%0.1f" % self.climatology_data[p_idx, v, idx],
                        ]
                    )

                data.append(entry)

        return super(Class4Plotter, self).csv(header, columns, data)

    def plot(self):
        figuresize = list(map(float, self.size.split("x")))
        fig = plt.figure(figsize=figuresize, dpi=self.dpi)

        width = len(self.variables)

        if self.showmap:
            width += 1  # Shift graphs to the right

        gs = gridspec.GridSpec(2, width)

        subplot = 0

        # Render point location
        if self.showmap:
            utils.point_plot(np.array([self.latitude, self.longitude]), gs[0, subplot])
            subplot += 1
            if len(self.ids) > 1:
                plt.legend(self.ids, loc="best")

        if self.class4_type == "ocean_predict":
            model_label = "GIOPS"
            plot_label = "Class4 GIOPS OceanPredict"
        else:
            model_label = "RIOPS"
            plot_label = "Class4 RIOPS Assimilated Observations"

        for idx, v in enumerate(self.variables):
            plt.subplot(gs[:, subplot])
            subplot += 1

            handles = []
            legend = []
            for i in range(0, len(self.forecast_data)):
                id_label = f"{self.ids[i]} " if len(self.ids) > 1 else ""

                form = "-"
                obs = self.observed_data[i, idx, :]
                if np.count_nonzero(~np.isnan(obs)) < 3:
                    form = "o-"

                if self.error in ["climatology", "observation"]:
                    if self.error == "climatology":
                        plot_label = (
                            "Error wrt Climatology"  # gettext("Error wrt Climatology")
                        )
                        handles.append(
                            plt.plot(
                                self.observed_data[i, idx, :]
                                - self.climatology_data[i, idx, :],
                                self.depths[i],
                                form,
                            )
                        )
                        legend.append(
                            f"{id_label} {'Observed'}"
                        )  # {gettext('Observed')}")

                        data = self.climatology_data
                    else:
                        plot_label = (
                            "Error wrt Observation"  # gettext("Error wrt Observation")
                        )

                        data = self.observed_data

                    handles.append(
                        plt.plot(
                            self.forecast_data[i, idx, :] - data[i, idx, :],
                            self.depths[i],
                            form,
                        )
                    )
                    legend.append(f"{id_label} {model_label}")

                    for j, model_name in enumerate(self.additional_model_names):
                        handles.append(
                            plt.plot(
                                self.additional_model_data[j, i, idx, :]
                                - data[i, idx, :],
                                self.depths[i],
                                form,
                            )
                        )
                        legend.append(f"{id_label} {model_name}")

                    if self.error == "observation" and self.climatology:
                        handles.append(
                            plt.plot(
                                self.climatology_data[i, idx, :]
                                - self.observed_data[i, idx, :],
                                self.depths[i],
                                form,
                            )
                        )
                        legend.append(
                            f"{id_label} {'Climatology'}"
                        )  # {gettext('Climatology')}")
                    lim = np.abs(plt.xlim()).max()
                    plt.xlim([-lim, lim])
                else:
                    handles.append(
                        plt.plot(self.observed_data[i, idx, :], self.depths[i], form)
                    )
                    legend.append(
                        "%s %s" % (id_label, "Observed")
                    )  # gettext("Observed")))
                    handles.append(
                        plt.plot(self.forecast_data[i, idx, :], self.depths[i], form)
                    )
                    legend.append(f"{id_label} {model_label}")
                    for j, model_name in enumerate(self.additional_model_names):
                        handles.append(
                            plt.plot(
                                self.additional_model_data[j, i, idx, :],
                                self.depths[i],
                                form,
                            )
                        )
                        legend.append(f"{id_label} {model_name}")

                    if self.climatology:
                        handles.append(
                            plt.plot(
                                self.climatology_data[i, idx, :], self.depths[i], form
                            )
                        )
                        legend.append(
                            f"{id_label} {'Climatology'}"
                        )  # {gettext('Climatology')}")

            plt.xlim([np.floor(plt.xlim()[0]), np.ceil(plt.xlim()[1])])

            plt.gca().xaxis.set_label_position("top")
            plt.gca().xaxis.set_ticks_position("top")
            plt.xlabel(f"{v} ({utils.mathtext(self.variable_units[idx])})", fontsize=14)
            plt.gca().invert_yaxis()
            plt.ylabel(
                f"Depth ({utils.mathtext(self.depth_unit)})",
                fontsize=14,  # gettext(f"Depth ({utils.mathtext(self.depth_unit)})"), fontsize=14
            )
            plt.grid(True)

        leg = fig.legend(
            [x[0] for x in handles],
            legend,
            loc="lower left",
            bbox_to_anchor=(0.05, 0.05),
        )
        for legobj in leg.legendHandles:
            legobj.set_linewidth(4.0)

        names = [
            "{} ({:0.2f}, {:0.2f})".format(*x)
            for x in zip(self.ids, self.latitude, self.longitude)
        ]
        wrapped_names = "\n".join(wrap(", ".join(names), 60))
        plt.suptitle(f"{wrapped_names}\n{plot_label}", fontsize=15)
        fig.tight_layout(pad=3, w_pad=4)
        fig.subplots_adjust(top=0.85)

        return super(Class4Plotter, self).plot(fig)
