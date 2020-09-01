"""Visualisation view"""
# Standard library imports
import time
import logging
from copy import copy

# Third-party imports
import wx
from pubsub import pub

# Local imports
from origami.utils.secret import get_short_hash
from origami.config.config import CONFIG
from origami.utils.utilities import report_time
from origami.visuals.mpl.gids import PlotIds
from origami.visuals.mpl.plot_overlay import PlotOverlay
# from origami.visuals.mpl.plot_spectrum import PlotSpectrum
from origami.gui_elements.views.view_base import ViewBase
from origami.gui_elements.views.view_base import ViewMPLMixin
from origami.gui_elements.views.view_mixins import ViewAxesMixin
from origami.gui_elements.views.view_mixins import ViewWaterfallMixin

LOGGER = logging.getLogger(__name__)


class ViewOverlayPanelMixin:
    """Spectrum panel base"""

    @staticmethod
    def make_panel(parent, figsize, plot_id, axes_size=None):
        """Initialize plot panel"""
        plot_panel = wx.Panel(parent)
        plot_window = PlotOverlay(plot_panel, figsize=figsize, axes_size=axes_size, plot_id=plot_id)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(plot_window, 1, wx.EXPAND)
        plot_panel.SetSizer(sizer)
        sizer.Fit(plot_panel)

        return plot_panel, plot_window, sizer


class ViewOverlay(ViewBase, ViewMPLMixin, ViewOverlayPanelMixin, ViewWaterfallMixin, ViewAxesMixin):
    """Viewer specialized in displaying overlay and comparison data"""

    VIEW_TYPE = "1d"
    DATA_KEYS = ("x", "y", "obj")
    MPL_KEYS = ["1d", "axes", "legend"]
    UPDATE_STYLES = ("line", "fill")
    ALLOWED_PLOTS = ("line", "multi-line", "waterfall")
    DEFAULT_PLOT = "line"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLOT_ID = get_short_hash()
        self.panel, self.figure, self.sizer = self.make_panel(self.parent, self.figsize, self.PLOT_ID, self.axes_size)

        # register view
        pub.sendMessage("view.register", view_id=self.PLOT_ID, view=self)

    def check_kwargs(self, **kwargs):
        """Check keyword parameters"""
        self._x_label = kwargs.pop("x_label", self.x_label)
        self._y_label = kwargs.pop("y_label", self.y_label)
        return kwargs

    def plot_1d_overlay(self, x=None, y=None, array=None, obj=None, repaint: bool = True, forced_kwargs=None, **kwargs):
        """Overlay multiple line plots"""
        t_start = time.time()

        #         self.can_plot("waterfall")
        # try to update plot first, as it can be quicker
        mpl_keys = copy(self.MPL_KEYS)
        mpl_keys.append("waterfall")

        self.set_document(obj, **kwargs)
        self.set_labels(obj, **kwargs)

        kwargs.update(**CONFIG.get_mpl_parameters(mpl_keys))
        kwargs.update(**self.FORCED_KWARGS)
        if isinstance(forced_kwargs, dict):
            kwargs.update(**forced_kwargs)
        self.figure.clear()
        self.figure.plot_waterfall(
            x, y, array, x_label=self.y_label, y_label="Offset intensity", callbacks=self._callbacks, obj=obj, **kwargs
        )
        self.figure.repaint(repaint)

        # set data
        #         self._data.update(x=x, y=y, array=array, obj=obj)  # noqa
        self.set_plot_parameters(**kwargs)
        LOGGER.debug(f"Plotted data in {report_time(t_start)}")

    def plot_1d_compare(self, x_top, x_bottom, y_top, y_bottom, obj=None, labels=None, forced_kwargs=None, **kwargs):
        """Overlay two line plots"""
        t_start = time.time()
        # try to update plot first, as it can be quicker
        self.set_document(obj, **kwargs)
        self.set_labels(obj, **kwargs)

        if labels is None:
            labels = ["", ""]
        kwargs.update(**CONFIG.get_mpl_parameters(["1d", "axes", "compare"]))  # self.MPL_KEYS))
        kwargs.update(**self.FORCED_KWARGS)
        if isinstance(forced_kwargs, dict):
            kwargs.update(**forced_kwargs)

        self.figure.clear()
        self.figure.plot_1d_compare(
            x_top,
            x_bottom,
            y_top,
            y_bottom,
            labels=labels,
            x_label=self.x_label,
            y_label=self.y_label,
            callbacks=self._callbacks,
            allow_extraction=self._allow_extraction,
            **kwargs,
        )
        self.figure.repaint()

        # # set data
        # self._data.update(
        #     x_top=x_top,
        #     x_bottom=x_bottom,
        #     y_top=y_top,
        #     y_bottom=y_bottom,
        #     obj_top=obj_top,
        #     obj_bottom=obj_bottom,
        #     labels=labels,
        # )
        self.set_plot_parameters(**kwargs)
        LOGGER.debug(f"Plotted data in {report_time(t_start)}")

    def plot_2d_overlay(self, x, y, array_1, array_2, obj=None, repaint: bool = True, forced_kwargs=None, **kwargs):
        """Overlay heatmaps using masking"""
        t_start = time.time()
        #         self.can_plot("heatmap")
        # try to update plot first, as it can be quicker
        self.set_document(obj, **kwargs)
        self.set_labels(obj, **kwargs)

        kwargs.update(**CONFIG.get_mpl_parameters(["2d", "colorbar", "normalization", "axes"]))  # self.MPL_KEYS))
        kwargs.update(**self.FORCED_KWARGS)
        if isinstance(forced_kwargs, dict):
            kwargs.update(**forced_kwargs)
        kwargs = self.check_kwargs(**kwargs)

        # x, y, array = self.check_input(x, y, array, obj)
        self.figure.clear()
        self.figure.plot_2d_overlay(
            x,
            y,
            array_1,
            array_2,
            x_label=self.x_label,
            y_label=self.y_label,
            callbacks=self._callbacks,
            obj=obj,
            **kwargs,
        )
        self.figure.repaint(repaint)

        # set data
        # self._data.update(x=x, y=y, array=array, obj=obj)
        # self.set_plot_parameters(**kwargs)
        LOGGER.debug(f"Plotted data in {report_time(t_start)}")

    def plot_2d_rgb(self, x, y, array, obj=None, repaint: bool = True, forced_kwargs=None, **kwargs):
        """Overlay multiple heatmaps using RGB overlay"""
        t_start = time.time()
        #         self.can_plot("heatmap")
        # try to update plot first, as it can be quicker
        self.set_document(obj, **kwargs)
        self.set_labels(obj, **kwargs)

        kwargs.update(**CONFIG.get_mpl_parameters(["2d", "colorbar", "normalization", "axes"]))
        kwargs.update(**self.FORCED_KWARGS)
        if isinstance(forced_kwargs, dict):
            kwargs.update(**forced_kwargs)
        kwargs = self.check_kwargs(**kwargs)

        # x, y, array = self.check_input(x, y, array, obj)
        self.figure.clear()
        self.figure.plot_2d_rgb(
            x, y, array, x_label=self.x_label, y_label=self.y_label, callbacks=self._callbacks, obj=obj, **kwargs
        )
        self.figure.repaint(repaint)

        # set data
        # self._data.update(x=x, y=y, array=array, obj=obj)
        # self.set_plot_parameters(**kwargs)
        LOGGER.debug(f"Plotted data in {report_time(t_start)}")

    def plot_2d_heatmap(self, x, y, array, obj=None, repaint: bool = True, forced_kwargs=None, **kwargs):
        """Overlay heatmap plots : mean, stddev, variance"""
        t_start = time.time()
        #         self.can_plot("heatmap")
        # try to update plot first, as it can be quicker
        self.set_document(obj, **kwargs)
        self.set_labels(obj, **kwargs)

        kwargs.update(**CONFIG.get_mpl_parameters(["2d", "colorbar", "normalization", "axes"]))
        kwargs.update(**self.FORCED_KWARGS)
        if isinstance(forced_kwargs, dict):
            kwargs.update(**forced_kwargs)
        kwargs = self.check_kwargs(**kwargs)

        # x, y, array = self.check_input(x, y, array, obj)
        self.figure.clear()
        self.figure.plot_2d(
            x, y, array, x_label=self.x_label, y_label=self.y_label, callbacks=self._callbacks, obj=obj, **kwargs
        )
        self.figure.repaint(repaint)

        # set data
        # self._data.update(x=x, y=y, array=array, obj=obj)
        # self.set_plot_parameters(**kwargs)
        LOGGER.debug(f"Plotted data in {report_time(t_start)}")

    def plot_2d_rmsd(self, x, y, array, rmsd_label, obj=None, repaint: bool = True, forced_kwargs=None, **kwargs):
        """Overlay two heatmaps using RMSD plot"""
        t_start = time.time()
        #         self.can_plot("heatmap")
        # try to update plot first, as it can be quicker
        self.set_document(obj, **kwargs)
        self.set_labels(obj, **kwargs)

        kwargs.update(**CONFIG.get_mpl_parameters(["2d", "colorbar", "normalization", "axes", "rmsd"]))
        kwargs.update(**self.FORCED_KWARGS)
        if isinstance(forced_kwargs, dict):
            kwargs.update(**forced_kwargs)
        kwargs = self.check_kwargs(**kwargs)

        # x, y, array = self.check_input(x, y, array, obj)
        self.figure.clear()
        self.figure.plot_2d(
            x, y, array, x_label=self.x_label, y_label=self.y_label, callbacks=self._callbacks, obj=obj, **kwargs
        )
        self.add_rmsd_label(x, y, rmsd_label, repaint=False)
        self.figure.repaint(repaint)

        # set data
        # self._data.update(x=x, y=y, array=array, obj=obj)
        # self.set_plot_parameters(**kwargs)
        LOGGER.debug(f"Plotted data in {report_time(t_start)}")

    def plot_2d_rmsf(
        self, x, y, array, y_top, rmsd_label, obj=None, repaint: bool = True, forced_kwargs=None, **kwargs
    ):
        """Overlay two heatmaps using RMSD + RMSF plot"""
        t_start = time.time()
        #         self.can_plot("heatmap")
        # try to update plot first, as it can be quicker
        self.set_document(obj, **kwargs)
        self.set_labels(obj, **kwargs)

        kwargs.update(**CONFIG.get_mpl_parameters(["2d", "colorbar", "normalization", "axes", "rmsd"]))
        kwargs.update(**self.FORCED_KWARGS)
        if isinstance(forced_kwargs, dict):
            kwargs.update(**forced_kwargs)
        kwargs = self.check_kwargs(**kwargs)

        self.figure.clear()
        self.figure.plot_heatmap_line(
            x, y, array, y_top, x_label=self.x_label, y_label=self.y_label, callbacks=self._callbacks, obj=obj, **kwargs
        )
        self.add_rmsd_label(x, y, rmsd_label, repaint=False)
        self.figure.repaint(repaint)

        # set data
        # self._data.update(x=x, y=y, array=array, obj=obj)
        # self.set_plot_parameters(**kwargs)
        LOGGER.debug(f"Plotted data in {report_time(t_start)}")

    def plot_2d_grid_compare_rmsd(
        self,
        x,
        y,
        array_top,
        array_bottom,
        array,
        rmsd_label,
        obj=None,
        repaint: bool = True,
        forced_kwargs=None,
        **kwargs,
    ):
        """Overlay two heatmaps using individual heatmaps -> RMSD plot"""
        t_start = time.time()
        # try to update plot first, as it can be quicker
        self.set_document(obj, **kwargs)
        self.set_labels(obj, **kwargs)

        kwargs.update(**CONFIG.get_mpl_parameters(["2d", "colorbar", "normalization", "axes", "grid"]))
        kwargs.update(**self.FORCED_KWARGS)
        if isinstance(forced_kwargs, dict):
            kwargs.update(**forced_kwargs)
        kwargs = self.check_kwargs(**kwargs)

        self.figure.clear()
        self.figure.plot_2d_grid_2_to_1(
            x,
            y,
            array_top,
            array_bottom,
            array,
            x_label=self.x_label,
            y_label=self.y_label,
            callbacks=self._callbacks,
            obj=obj,
            **kwargs,
        )
        self.add_rmsd_label(x, y, rmsd_label, repaint=False)
        self.figure.repaint(repaint)

        # set data
        # self._data.update(x=x, y=y, array=array, obj=obj)
        # self.set_plot_parameters(**kwargs)
        LOGGER.debug(f"Plotted data in {report_time(t_start)}")

    def plot_2d_rmsd_dot(self):
        """Generate RMSD dot plot from multiple heatmaps"""

    def plot_2d_rmsd_matrix(self):
        """Generate RMSD matrix plot from multiple heatmaps"""

    def plot_2d_grid_n_x_n(
        self, x, y, arrays, n_rows, n_cols, obj=None, repaint: bool = True, forced_kwargs=None, **kwargs
    ):
        """Overlay multiple heatmaps in a grid with linked zooming"""
        t_start = time.time()
        # try to update plot first, as it can be quicker
        self.set_document(obj, **kwargs)
        self.set_labels(obj, **kwargs)

        kwargs.update(**CONFIG.get_mpl_parameters(["2d", "colorbar", "normalization", "axes", "grid"]))
        kwargs.update(**self.FORCED_KWARGS)
        if isinstance(forced_kwargs, dict):
            kwargs.update(**forced_kwargs)
        kwargs = self.check_kwargs(**kwargs)

        self.figure.clear()
        self.figure.plot_2d_grid_n_x_n(
            x,
            y,
            arrays,
            n_rows,
            n_cols,
            x_label=self.x_label,
            y_label=self.y_label,
            callbacks=self._callbacks,
            obj=obj,
            **kwargs,
        )
        self.figure.repaint(repaint)
        # set data
        # self._data.update(x=x, y=y, array=array, obj=obj)
        # self.set_plot_parameters(**kwargs)
        LOGGER.debug(f"Plotted data in {report_time(t_start)}")

    def add_rmsd_label(self, x, y, label: str, repaint: bool = True, forced_kwargs=None, **kwargs):
        """Add RMSD label to plot"""
        kwargs.update(**CONFIG.get_mpl_parameters(["rmsd"]))
        kwargs.update(**self.FORCED_KWARGS)
        if isinstance(forced_kwargs, dict):
            kwargs.update(**forced_kwargs)
        kwargs = self.check_kwargs(**kwargs)

        self.figure.plot_add_rmsd_label(x, y, label, **kwargs)
        self.figure.repaint(repaint)

    def update_style(self, name: str):
        """Update plot style"""
        t_start = time.time()
        kwargs = dict()
        repaint: bool = False
        if name.startswith("axes"):
            kwargs = self._update_style_axes(name)
        elif name.startswith("legend"):
            kwargs = CONFIG.get_mpl_parameters(["legend"])
            repaint = self.figure.plot_update_legend(**kwargs)
        elif name.startswith("rmsd"):
            kwargs = CONFIG.get_mpl_parameters(["rmsd"])
            repaint = self.figure.plot_update_rmsd_label(**kwargs)
        elif name.startswith("rmsf"):
            if name.endswith(".fill"):
                repaint = self.figure.plot_1d_update_patch_style_by_label(
                    spectrum_line_fill_under=True,
                    spectrum_fill_color=CONFIG.rmsf_fill_color,
                    spectrum_fill_transparency=CONFIG.rmsf_fill_transparency,
                    spectrum_fill_hatch=CONFIG.rmsf_fill_hatch,
                    gid=PlotIds.PLOT_LH_PATCH,
                    ax=self.figure.plot_line_top,
                )
            elif name.endswith(".line"):
                repaint = self.figure.plot_1d_update_style_by_label(
                    spectrum_line_color=CONFIG.rmsf_line_color,
                    spectrum_line_style=CONFIG.rmsf_line_style,
                    spectrum_line_width=CONFIG.rmsf_line_width,
                    spectrum_line_transparency=CONFIG.rmsf_line_transparency,
                    gid=PlotIds.PLOT_LH_LINE,
                    ax=self.figure.plot_line_top,
                )
            elif name.endswith(".grid"):
                repaint = self.figure.plot_update_grid(self.figure.plot_line_gs, hspace=CONFIG.rmsf_h_space)
        self.figure.repaint()
        self.set_plot_parameters(**kwargs)
        LOGGER.debug(f"Updated plot styles - {name} in {report_time(t_start)}")

    def plot(self, *args, **kwargs):
        """Simple plot"""
        raise ValueError("This view does not support simple update - use appropriate method instead")

    def update(self, *args, **kwargs):
        """Update"""
        raise ValueError("This view does not support simple update - use appropriate method instead")

    def replot(self, **kwargs):
        """Full replot"""
        raise ValueError("This view does not support simple update - use appropriate method instead")

    def _update(self):
        """Update"""
        raise ValueError("This view does not support simple update - use appropriate method instead")