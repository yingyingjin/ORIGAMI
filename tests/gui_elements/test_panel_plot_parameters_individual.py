"""Test PanelAbout dialog"""
# Third-party imports
import pytest

# Local imports
from origami.config.config import CONFIG
from origami.gui_elements.plot_parameters.panel_1d import Panel1dSettings
from origami.gui_elements.plot_parameters.panel_2d import Panel2dSettings
from origami.gui_elements.plot_parameters.panel_3d import Panel3dSettings
from origami.gui_elements.plot_parameters.panel_ui import PanelUISettings
from origami.gui_elements.plot_parameters.panel_rmsd import PanelRMSDSettings
from origami.gui_elements.plot_parameters.panel_sizes import PanelSizesSettings
from origami.gui_elements.plot_parameters.panel_legend import PanelLegendSettings
from origami.gui_elements.plot_parameters.panel_violin import PanelViolinSettings
from origami.gui_elements.plot_parameters.panel_general import PanelGeneralSettings
from origami.gui_elements.plot_parameters.panel_colorbar import PanelColorbarSettings
from origami.gui_elements.plot_parameters.panel_waterfall import PanelWaterfallSettings

from ..wxtc import WidgetTestCase


@pytest.mark.guitest
class TestPanelGeneralSettings(WidgetTestCase):
    """Test dialog"""

    def test_panel_create(self):
        dlg = PanelGeneralSettings(self.frame, None)

        # update settings
        for value in [True, False]:
            self.sim_checkbox_click_evt(dlg.plot_axis_on_off_check, value, [dlg.on_apply, dlg.on_toggle_controls])
            assert CONFIG.axes_frame_show is dlg.plot_axis_on_off_check.GetValue() is value
            assert dlg.plot_right_spines_check.IsEnabled() is value
            assert dlg.plot_frame_width_value.IsEnabled() is value


@pytest.mark.guitest
class TestPanel1dSettings(WidgetTestCase):
    """Test dialog"""

    def test_panel_create(self):
        dlg = Panel1dSettings(self.frame, None)

        # fill parameters
        for value in [True, False]:
            self.sim_checkbox_click_evt(dlg.spectrum_line_fill_under, value, [dlg.on_apply, dlg.on_toggle_controls])
            assert dlg.spectrum_line_fill_under.GetValue() is dlg.spectrum_line_fill_under.GetValue() is value
            assert dlg.spectrum_fill_transparency.IsEnabled() is value
            assert dlg.plot1d_underline_color_btn.IsEnabled() is value

        # marker parameters
        for value in [True, False]:
            self.sim_checkbox_click_evt(dlg.marker_edge_same_as_fill, value, [dlg.on_apply, dlg.on_toggle_controls])
            assert CONFIG.marker_edge_same_as_fill is dlg.marker_edge_same_as_fill.GetValue() is value
            assert dlg.plot1d_marker_edge_color_btn.IsEnabled() is value

        # marker parameters
        for value in [True, False]:
            self.sim_checkbox_click_evt(dlg.bar_edge_same_as_fill, value, [dlg.on_apply, dlg.on_toggle_controls])
            assert CONFIG.bar_edge_same_as_fill is dlg.bar_edge_same_as_fill.GetValue() is value
            assert dlg.bar_edge_color_btn.IsEnabled() is value


@pytest.mark.guitest
class TestPanel2dSettings(WidgetTestCase):
    """Test dialog"""

    def test_panel_create(self):
        dlg = Panel2dSettings(self.frame, None)

        dlg.on_apply(None)
        dlg.on_toggle_controls(None)


@pytest.mark.guitest
class TestPanel3dSettings(WidgetTestCase):
    """Test dialog"""

    def test_panel_create(self):
        dlg = Panel3dSettings(self.frame, None)

        dlg.on_apply(None)
        dlg.on_toggle_controls(None)


@pytest.mark.guitest
class TestPanelColorbarSettings(WidgetTestCase):
    """Test dialog"""

    def test_panel_create(self):
        dlg = PanelColorbarSettings(self.frame, None)

        # update controls
        for value in [True, False]:
            self.sim_toggle_click_evt(dlg.colorbar_tgl, value, [dlg.on_apply, dlg.on_toggle_controls])
            assert CONFIG.colorbar is dlg.colorbar_tgl.GetValue() is value
            assert dlg.colorbar_position_value.IsEnabled() is value
            assert dlg.colorbar_width_value.IsEnabled() is value
            assert dlg.colorbar_fontsize_value.IsEnabled() is value
            assert dlg.colorbar_label_format.IsEnabled() is value
            assert dlg.colorbar_outline_width_value.IsEnabled() is value
            assert dlg.colorbar_label_color_btn.IsEnabled() is value
            assert dlg.colorbar_outline_color_btn.IsEnabled() is value

        self.sim_toggle_click_evt(dlg.colorbar_tgl, True, [dlg.on_apply, dlg.on_toggle_controls])
        # change position
        for value in ["left", "right", "top", "bottom"]:
            self.sim_combobox_click_evt(dlg.colorbar_position_value, value, [dlg.on_apply, dlg.on_toggle_controls])
            assert CONFIG.colorbar_position == dlg.colorbar_position_value.GetStringSelection() == value
            assert dlg.colorbar_pad_value.IsEnabled() is True
            assert dlg.colorbar_width_inset_value.IsEnabled() is False

        for value in ["inside (top-left)", "inside (top-right)", "inside (bottom-left)", "inside (bottom-right)"]:
            self.sim_combobox_click_evt(dlg.colorbar_position_value, value, [dlg.on_apply, dlg.on_toggle_controls])
            assert CONFIG.colorbar_position == dlg.colorbar_position_value.GetStringSelection() == value
            assert dlg.colorbar_pad_value.IsEnabled() is False
            assert dlg.colorbar_width_inset_value.IsEnabled() is True


@pytest.mark.guitest
class TestPanelWaterfallSettings(WidgetTestCase):
    """Test dialog"""

    def test_panel_create(self):
        dlg = PanelWaterfallSettings(self.frame, None)

        # update controls
        for value in [True, False]:
            self.sim_checkbox_click_evt(
                dlg.waterfall_line_sameAsShade_check, value, [dlg.on_apply, dlg.on_toggle_controls]
            )
            assert CONFIG.waterfall_line_same_as_fill is dlg.waterfall_line_sameAsShade_check.GetValue() is value
            assert dlg.waterfall_color_line_btn.IsEnabled() is not value

        for value in [True, False]:
            self.sim_checkbox_click_evt(dlg.waterfall_fill_under_check, value, [dlg.on_apply, dlg.on_toggle_controls])
            assert CONFIG.waterfall_fill_under is dlg.waterfall_fill_under_check.GetValue() is value
            assert dlg.waterfall_fill_transparency_value.IsEnabled() is value
            assert dlg.waterfall_fill_n_limit_value.IsEnabled() is value

        for value in [True, False]:
            self.sim_checkbox_click_evt(dlg.waterfall_showLabels_check, value, [dlg.on_apply, dlg.on_toggle_controls])
            assert CONFIG.waterfall_labels_show is dlg.waterfall_showLabels_check.GetValue() is value
            assert dlg.waterfall_label_format_value.IsEnabled() is value
            assert dlg.waterfall_label_font_size_value.IsEnabled() is value
            assert dlg.waterfall_label_font_weight_check.IsEnabled() is value
            assert dlg.waterfall_label_frequency_value.IsEnabled() is value
            assert dlg.waterfall_label_x_offset_value.IsEnabled() is value
            assert dlg.waterfall_label_y_offset_value.IsEnabled() is value


@pytest.mark.guitest
class TestPanelViolinSettings(WidgetTestCase):
    """Test dialog"""

    def test_panel_create(self):
        dlg = PanelViolinSettings(self.frame, None)

        # update controls
        for value in [True, False]:
            self.sim_checkbox_click_evt(
                dlg.violin_line_same_as_fill_check, value, [dlg.on_apply, dlg.on_toggle_controls]
            )
            assert CONFIG.violin_line_same_as_fill is dlg.violin_line_same_as_fill_check.GetValue() is value
            assert dlg.violin_color_line_btn.IsEnabled() is not value

        # update controls
        for value in [True, False]:
            self.sim_checkbox_click_evt(dlg.violin_smooth_value, value, [dlg.on_apply, dlg.on_toggle_controls])
            assert CONFIG.violin_smooth is dlg.violin_smooth_value.GetValue() is value
            assert dlg.violin_smooth_sigma_value.IsEnabled() is value


@pytest.mark.guitest
class TestPanelLegendSettings(WidgetTestCase):
    """Test dialog"""

    def test_panel_create(self):
        dlg = PanelLegendSettings(self.frame, None)

        # update controls
        for value in [True, False]:
            self.sim_toggle_click_evt(dlg.legend_toggle, value, [dlg.on_apply, dlg.on_toggle_controls])
            assert CONFIG.legend is dlg.legend_toggle.GetValue() is value
            assert dlg.legend_position_value.IsEnabled() is value
            assert dlg.legend_columns_value.IsEnabled() is value
            assert dlg.legend_fontsize_value.IsEnabled() is value
            assert dlg.legend_frame_check.IsEnabled() is value
            assert dlg.legend_alpha_value.IsEnabled() is value
            assert dlg.legend_marker_size_value.IsEnabled() is value
            assert dlg.legend_n_markers_value.IsEnabled() is value
            assert dlg.legend_marker_before_check.IsEnabled() is value
            assert dlg.legend_fancybox_check.IsEnabled() is value
            assert dlg.legend_patch_alpha_value.IsEnabled() is value

        self.sim_toggle_click_evt(dlg.legend_toggle, True, [dlg.on_apply, dlg.on_toggle_controls])


@pytest.mark.guitest
class TestPanelSizesSettings(WidgetTestCase):
    """Test dialog"""

    def test_panel_create(self):
        dlg = PanelSizesSettings(self.frame, None)

        dlg.on_apply(None)
        dlg.on_toggle_controls(None)


@pytest.mark.guitest
class TestPanelUISettings(WidgetTestCase):
    """Test dialog"""

    def test_panel_create(self):
        dlg = PanelUISettings(self.frame, None)

        dlg.on_apply(None)
        dlg.on_toggle_controls(None)


@pytest.mark.guitest
class TestPanelRMSDSettings(WidgetTestCase):
    """Test dialog"""

    def test_panel_create(self):
        dlg = PanelRMSDSettings(self.frame, None)

        dlg.on_apply(None)
        dlg.on_toggle_controls(None)
