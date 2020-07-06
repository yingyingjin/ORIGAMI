# Standard library imports
import logging

# Third-party imports
import wx

# Local imports
from origami.utils.secret import get_short_hash
from origami.config.config import CONFIG
from origami.visuals.mpl.plot_heatmap_2d import PlotHeatmap2D
from origami.gui_elements.views.view_base import ViewBase

LOGGER = logging.getLogger(__name__)


class ViewHeatmap(ViewBase):
    """Viewer class for heatmap-based objects"""

    DATA_KEYS = ("array", "x", "y")
    MPL_KEYS = ["2D"]
    NAME = get_short_hash()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.panel, self.figure, self.sizer = self.make_panel()

    def _update(self):
        """Update plot with current data"""
        self.update(self._data["x"], self._data["y"], **self._plt_kwargs)

    def make_panel(self):
        """Initialize plot panel"""
        plot_panel = wx.Panel(self.parent)
        plot_window = PlotHeatmap2D(plot_panel, figsize=self.figsize, axes_size=self.axes_size, plot_id=self.NAME)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(plot_window, 1, wx.EXPAND)
        plot_panel.SetSizer(sizer)
        sizer.Fit(plot_panel)

        return plot_panel, plot_window, sizer

    def check_input(self, x, y, array, obj):
        """Check user-input"""
        if x is None and y is None and array is None and obj is None:
            raise ValueError("You must provide the x/y/array values or container object")
        if x is None and y is None and array is None and obj is not None:
            x = obj.x
            y = obj.y
        return x, y, obj.array

    def check_kwargs(self, **kwargs):
        """Check kwargs"""
        if "allow_extraction" not in kwargs:
            kwargs["allow_extraction"] = self._allow_extraction
        #         if "x_label" not in kwargs:
        #             kwargs["x_label"] = self.x_label
        #         if "y_label" not in kwargs:
        #             kwargs["y_label"] = self.y_label
        return kwargs

    def plot(self, x=None, y=None, array=None, obj=None, **kwargs):
        """Simple line plot"""
        # try to update plot first, as it can be quicker
        self.set_document(obj, **kwargs)
        self.set_labels(obj, **kwargs)

        kwargs.update(**CONFIG.get_mpl_parameters(self.MPL_KEYS))
        kwargs = self.check_kwargs(**kwargs)

        try:
            self.update(x, y, array, obj, **kwargs)
        except AttributeError:
            x, y, array = self.check_input(x, y, array, obj)
            _ = kwargs.pop("x_label", "?")
            self.figure.clear()
            self.figure.plot_2d(
                x, y, array, x_label=self.x_label, y_label=self.y_label, callbacks=self._callbacks, **kwargs
            )
            self.figure.repaint()

            # set data
            self._data.update(x=x, y=y, array=array)
            self._plt_kwargs = kwargs
            LOGGER.debug("Plotted data")

    def update(self, x=None, y=None, array=None, obj=None, **kwargs):
        """Update plot without having to clear it"""
        self.set_document(obj, **kwargs)
        self.set_labels(obj, **kwargs)

        # update plot
        x, y, array = self.check_input(x, y, array, obj)
        self.figure.plot_2d_update_data(x, y, array, self.x_label, self.y_label, **kwargs)
        self.figure.repaint()

        # set data
        self._data.update(x=x, y=y, array=array)
        self._plt_kwargs = kwargs
        LOGGER.debug("Updated plot data")

    def replot(self, **kwargs):
        """Replot the current plot"""

    def plot_violin(self):
        """Plot object as a violin plot"""
        pass

    def plot_waterfall(self):
        """Plot object as a waterfall"""
        pass

    def plot_joint(self):
        """Plot object as a joint-plot with top/side panels"""
        pass


class ViewIonHeatmap(ViewHeatmap):
    """Viewer class for extracted ions"""

    NAME = get_short_hash()

    def __init__(self, parent, figsize, title="IonHeatmap", **kwargs):
        ViewHeatmap.__init__(self, parent, figsize, title, **kwargs)
        self._x_label = kwargs.pop("x_label", "Scans")
        self._y_label = kwargs.pop("y_label", "Drift time (bins)")


class ViewImagingIonHeatmap(ViewHeatmap):
    """Viewer class for extracted ions - LESA/Imaging documents"""

    NAME = get_short_hash()

    def __init__(self, parent, figsize, title="ImagingIonHeatmap", **kwargs):
        ViewHeatmap.__init__(self, parent, figsize, title, **kwargs)
        self._x_label = kwargs.pop("x_label", "x")
        self._y_label = kwargs.pop("y_label", "y")


class ViewMassSpectrumHeatmap(ViewHeatmap):
    """Viewer class for MS/DT heatmap"""

    NAME = get_short_hash()

    def __init__(self, parent, figsize, title="MassSpectrumHeatmap", **kwargs):
        ViewHeatmap.__init__(self, parent, figsize, title, **kwargs)
        self._x_label = kwargs.pop("x_label", "m/z (Da)")
        self._y_label = kwargs.pop("y_label", "Drift time (bins)")
