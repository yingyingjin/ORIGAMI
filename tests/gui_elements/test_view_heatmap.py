"""Test `views`"""
# Third-party imports
import wx
import numpy as np
import pytest

# Local imports
from origami.objects.containers import IonHeatmapObject
from origami.objects.containers import MassSpectrumHeatmapObject
from origami.gui_elements.views.view_heatmap import ViewIonHeatmap
from origami.gui_elements.views.view_heatmap import ViewMassSpectrumHeatmap

from ..wxtc import WidgetTestCase


@pytest.mark.guitest
class TestPlotView(WidgetTestCase):
    """Test panel"""

    def set_plot(self, view):
        """Set view in the panel"""
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(view.panel, 1, wx.EXPAND)
        self.frame.SetSizerAndFit(sizer)
        self.frame.Layout()


@pytest.mark.guitest
class TestPanelViewIonHeatmap(TestPlotView):
    """Test dialog"""

    def test_panel_create(self):
        view = ViewIonHeatmap(self.frame, (12, 12))
        self.set_plot(view)

        # test plot using x/y
        obj = IonHeatmapObject(np.random.randint(0, 100, (3, 4)), np.arange(4), np.arange(3))

        # test plot using object
        view.plot(obj=obj)
        view.plot_contour(obj=obj)
        view.plot_joint(obj=obj)
        view.plot_violin(obj=obj)
        view.plot_waterfall(obj=obj)


@pytest.mark.guitest
class TestPanelViewMassSpectrumHeatmap(TestPlotView):
    """Test dialog"""

    def test_panel_create(self):
        view = ViewMassSpectrumHeatmap(self.frame, (12, 12))
        self.set_plot(view)

        # test plot using x/y
        obj = MassSpectrumHeatmapObject(np.random.randint(0, 100, (3, 4)), np.arange(4), np.arange(3))

        # test plot using object
        view.plot(obj=obj)
        view.plot_joint(obj=obj)
        view.plot_violin(obj=obj)
        view.plot_waterfall(obj=obj)
