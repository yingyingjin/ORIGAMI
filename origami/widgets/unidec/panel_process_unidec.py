"""UniDec processing panel"""
# Standard library imports
import time
import logging

# Third-party imports
import wx
import wx.lib.scrolledpanel as wxScrolledPanel
from pubsub import pub
from pubsub.core import TopicNameError

# Local imports
from origami.styles import MiniFrame
from origami.styles import Validator
from origami.config.config import CONFIG
from origami.utils.utilities import report_time
from origami.utils.converters import str2int
from origami.utils.converters import str2num
from origami.utils.exceptions import MessageError
from origami.gui_elements.mixins import DatasetMixin
from origami.gui_elements.mixins import ConfigUpdateMixin
from origami.gui_elements.helpers import set_tooltip
from origami.gui_elements.helpers import make_tooltip
from origami.gui_elements.helpers import make_checkbox
from origami.gui_elements.helpers import set_item_font
from origami.gui_elements.helpers import make_menu_item
from origami.gui_elements.helpers import make_bitmap_btn
from origami.handlers.queue_handler import QUEUE
from origami.widgets.unidec.view_unidec import ViewBarChart
from origami.widgets.unidec.view_unidec import ViewFitMassSpectrum
from origami.widgets.unidec.view_unidec import ViewIndividualPeaks
from origami.widgets.unidec.view_unidec import ViewMolecularWeight
from origami.widgets.unidec.view_unidec import ViewMassSpectrumGrid
from origami.widgets.unidec.view_unidec import ViewChargeDistribution
from origami.widgets.unidec.view_unidec import ViewMolecularWeightGrid
from origami.objects.containers.spectrum import MassSpectrumObject
from origami.widgets.unidec.unidec_handler import UNIDEC_HANDLER
from origami.gui_elements.views.view_register import VIEW_REG
from origami.widgets.unidec.processing.utilities import unidec_sort_mw_list
from origami.widgets.unidec.processing.containers import UniDecResultsObject

logger = logging.getLogger(__name__)

TEXTCTRL_SIZE = (40, -1)
BTN_SIZE = (100, -1)

# TODO: Add table
# TODO: Add display difference and FWHM
# TODO: FIXME: There is an issue with adding markers to MW plot


class PanelProcessUniDec(MiniFrame, DatasetMixin, ConfigUpdateMixin):
    """UniDec panel"""

    # module specific parameters
    PUB_SUBSCRIBE_EVENT = "widget.picker.update.spectrum"
    HELP_LINK = "https://origami.lukasz-migas.com/"
    PANEL_BASE_TITLE = "UniDec"

    current_page = None
    _unidec_sort_column = 0

    # ui elements
    plot_notebook, view_mz, view_mw, view_mz_grid, main_sizer = None, None, None, None, None
    view_mw_grid, view_peaks, view_barchart, view_charge = None, None, None, None
    plot_panel, peak_width_value, peak_threshold_value, peak_normalization_choice = None, None, None, None
    line_separation_value, markers_check, individual_line_check, weight_list_choice = None, None, None, None
    charges_check, adduct_choice, charges_threshold_value, charges_offset_value = None, None, None, None
    restore_all_btn, isolate_charges_btn, label_charges_btn, weight_list_sort = None, None, None, None
    detect_peaks_btn, show_peaks_btn, z_start_value, z_end_value = None, None, None, None
    unidec_auto_btn, unidec_init_btn, unidec_unidec_btn, unidec_peak_btn = None, None, None, None
    unidec_all_btn, unidec_cancel_btn, unidec_customise_btn, mw_start_value = None, None, None, None
    mw_end_value, mw_sample_frequency_value, fit_peak_width_value, peak_width_btn = None, None, None, None
    peak_shape_func_choice, run_unidec_btn, peak_width_auto_check, process_settings_btn = None, None, None, None
    process_btn, smooth_nearby_points, mz_to_mw_transform_choice, adduct_mass_value = None, None, None, None
    softmax_beta_value, smooth_z_distribution, mass_nearby_points, negative_mode_check = None, None, None, None
    _dlg_width_tool, _dlg_ms_process_tool, settings_panel = None, None, None

    def __init__(
        self,
        parent,
        presenter,
        icons,
        document_title: str = None,
        dataset_name: str = None,
        mz_obj: MassSpectrumObject = None,
    ):
        """Initialize panel"""
        MiniFrame.__init__(self, parent, title="UniDec...", style=wx.DEFAULT_FRAME_STYLE)
        t_start = time.time()
        self.view = parent
        self.presenter = presenter
        self._icons = icons

        self._window_size = self._get_window_size(parent, [0.9, 0.9])

        # initialize gui
        self.make_gui()
        self.on_toggle_controls(None)

        # setup kwargs
        self.document_title = document_title
        self.dataset_name = dataset_name
        self.mz_obj = mz_obj
        self.unsaved = False

        self.setup()

        # bind events
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_CONTEXT_MENU, self.on_right_click)
        logger.debug(f"Started-up UniDec panel in {report_time(t_start)}")

        self.CenterOnParent()
        self.SetFocus()
        self.SetSize(self._window_size)

    def setup(self):
        """Setup window"""
        self._config_mixin_setup()
        self._dataset_mixin_setup()
        if self.PUB_SUBSCRIBE_EVENT:
            pub.subscribe(self.on_process, self.PUB_SUBSCRIBE_EVENT)

        if self.mz_obj:
            self.view_mz.plot(obj=self.mz_obj)

    def on_close(self, evt, force: bool = False):
        """Close window"""
        self._config_mixin_teardown()
        self._dataset_mixin_teardown()
        try:
            if self.PUB_SUBSCRIBE_EVENT:
                pub.unsubscribe(self.on_process, self.PUB_SUBSCRIBE_EVENT)
        except TopicNameError:
            pass
        super(PanelProcessUniDec, self).on_close(evt, force)

    # @property
    # def data_handling(self):
    #     """Return handle to `data_handling`"""
    #     return self.presenter.data_handling
    #
    # @property
    # def data_processing(self):
    #     """Return handle to `data_processing`"""
    #     return self.presenter.data_processing
    #
    # @property
    # def panel_plot(self):
    #     """Return handle to `panel_plot`"""
    #     return self.view.panelPlots
    #
    # @property
    # def document_tree(self):
    #     """Return handle to `document_tree`"""
    #     return self.presenter.view.panelDocuments.documents

    def set_new_dataset(self, document_title: str, dataset_name: str, mz_obj: MassSpectrumObject):
        """Set new data in the panel"""
        self.document_title = document_title
        self.dataset_name = dataset_name
        self.mz_obj = mz_obj
        CONFIG.unidec_engine = None

    def on_right_click(self, evt):
        """Right-click menu"""
        if hasattr(evt.EventObject, "figure"):
            view = VIEW_REG.view
            menu = view.get_right_click_menu(self)
            save_all_figures_menu_item = make_menu_item(
                menu, evt_id=wx.ID_ANY, text="Save all figures as...", bitmap=self._icons.save_all
            )
            menu.Insert(4, save_all_figures_menu_item)

            self.Bind(wx.EVT_MENU, self.on_save_all_figures, save_all_figures_menu_item)

            self.PopupMenu(menu)
            menu.Destroy()
            self.SetFocus()

    def make_gui(self):
        """Make gui"""
        # make settings controls
        #         settings_panel = self.make_settings_panel(panel_settings)
        self.settings_panel = self.make_settings_panel(self)

        self.plot_panel = self.make_plot_panel(self)

        # pack element
        main_sizer = wx.BoxSizer()
        main_sizer.Add(self.plot_panel, 3, wx.EXPAND, 0)

        # add settings panel
        if "Left" in CONFIG.unidec_plot_settings_view:
            main_sizer.Insert(0, self.settings_panel, 1, wx.EXPAND, 0)
        else:
            main_sizer.Add(self.settings_panel, 1, wx.EXPAND, 0)

        # fit layout
        main_sizer.Fit(self)
        self.SetSizer(main_sizer)
        #         self.SetSizerAndFit(main_sizer)
        self.settings_panel.SetMinSize((450, -1))
        self.settings_panel.SetSize((450, -1))

        self.Layout()

    def make_plot_panel(self, split_panel):
        """Make plot panel"""

        #         _settings_panel_size = self.settings_panel.GetSize()
        #         pixel_size = [(self._window_size[0] - _settings_panel_size[0]), (self._window_size[1] - 50)]
        #         figsize = [pixel_size[0] / self._display_resolution[0], pixel_size[1] / self._display_resolution[1]]
        #         figsize_1d = [figsize[0] / 2.75, figsize[1] / 3]
        #         figsize_2d = [figsize[0] / 2.75, figsize[1] / 1.5]
        #         print(figsize_1d, figsize_2d)
        figsize_1d = (6, 3)
        figsize_2d = (6, 6)

        CONFIG.unidec_plot_panel_view = "Single page view"

        # setup plot base
        if CONFIG.unidec_plot_panel_view == "Single page view":
            plot_panel = wxScrolledPanel.ScrolledPanel(split_panel)
            plot_parent = plot_panel
        else:
            plot_panel = wx.Panel(split_panel)
            plot_parent = wx.Notebook(plot_panel)

        # mass spectrum
        self.view_mz = ViewFitMassSpectrum(
            plot_parent, figsize_1d, CONFIG, allow_extraction=False, filename="mass-spectrum"
        )

        # molecular weight
        self.view_mw = ViewMolecularWeight(
            plot_parent, figsize_1d, CONFIG, allow_extraction=False, filename="molecular-weight"
        )

        # molecular weight
        self.view_mz_grid = ViewMassSpectrumGrid(
            plot_parent, figsize_2d, CONFIG, allow_extraction=False, filename="ms-grid"
        )

        # molecular weight
        self.view_mw_grid = ViewMolecularWeightGrid(
            plot_parent, figsize_2d, CONFIG, allow_extraction=False, filename="mw-grid"
        )

        # molecular weight
        self.view_peaks = ViewIndividualPeaks(
            plot_parent, figsize_2d, CONFIG, allow_extraction=False, filename="isolated-peaks"
        )

        # molecular weight
        self.view_barchart = ViewBarChart(plot_parent, figsize_2d, CONFIG, allow_extraction=False, filename="barchart")
        # molecular weight
        self.view_charge = ViewChargeDistribution(
            plot_parent, figsize_1d, CONFIG, allow_extraction=False, filename="charge-distribution"
        )

        if CONFIG.unidec_plot_panel_view == "Single page view":
            plot_parent = wx.BoxSizer(wx.VERTICAL)

            _row_0 = wx.BoxSizer()
            _row_0.Add(self.view_mz.panel, 1, wx.EXPAND)
            _row_0.Add(self.view_mw.panel, 1, wx.EXPAND)

            _row_1 = wx.BoxSizer()
            _row_1.Add(self.view_mz_grid.panel, 1, wx.EXPAND)
            _row_1.Add(self.view_mw_grid.panel, 1, wx.EXPAND)

            _row_2 = wx.BoxSizer()
            _row_2.Add(self.view_peaks.panel, 1, wx.EXPAND)
            _row_2.Add(self.view_barchart.panel, 1, wx.EXPAND)

            _row_3 = wx.BoxSizer()
            _row_3.Add(self.view_charge.panel, 1, wx.EXPAND)

            plot_parent.Add(_row_0, 1, wx.EXPAND)
            plot_parent.Add(_row_1, 1, wx.EXPAND)
            plot_parent.Add(_row_2, 1, wx.EXPAND)
            plot_parent.Add(_row_3, 1, wx.EXPAND)

            main_sizer = wx.BoxSizer(wx.VERTICAL)
            main_sizer.Add(plot_parent, 1, wx.EXPAND, 2)
            self.plot_panel = plot_panel

            # setup scrolling
            plot_panel.SetupScrolling()
        else:
            plot_parent.AddPage(self.view_mz.panel, "MS")
            plot_parent.AddPage(self.view_mw.panel, "MW")
            plot_parent.AddPage(self.view_mz_grid.panel, "m/z vs Charge")
            plot_parent.AddPage(self.view_mw_grid.panel, "MW vs Charge")
            plot_parent.AddPage(self.view_peaks.panel, "Isolated MS")
            plot_parent.AddPage(self.view_barchart.panel, "Barchart")
            plot_parent.AddPage(self.view_charge.panel, "Charge distribution")

            plot_parent.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_page_changed)
            self.plot_notebook = plot_parent

            main_sizer = wx.BoxSizer(wx.VERTICAL)
            main_sizer.Add(plot_parent, 1, wx.EXPAND, 2)
            self.plot_panel = plot_panel
            self.on_page_changed(None)

        # fit layout
        main_sizer.Fit(self.plot_panel)
        self.plot_panel.SetSizer(main_sizer)
        #         self.plot_panel.SetSizerAndFit(main_sizer)

        return self.plot_panel

    def make_settings_panel(self, split_panel):
        """Make settings panel"""
        panel = wxScrolledPanel.ScrolledPanel(split_panel, size=(-1, -1), name="main")

        n_span = 3
        n_col = 4
        grid = wx.GridBagSizer(2, 2)

        # make buttons
        grid, n = self.make_buttons_settings_panel(panel, grid, 0, n_span, n_col)
        n += 1
        grid.Add(wx.StaticLine(panel, -1, style=wx.LI_HORIZONTAL), (n, 0), wx.GBSpan(1, n_col), flag=wx.EXPAND)

        # pre-processing
        preprocessing_label = wx.StaticText(panel, -1, "Pre-processing")
        set_item_font(preprocessing_label)
        n += 1
        grid.Add(preprocessing_label, (n, 0), wx.GBSpan(1, n_col), flag=wx.ALIGN_CENTER)
        n += 1
        grid.Add(wx.StaticLine(panel, -1, style=wx.LI_HORIZONTAL), (n, 0), wx.GBSpan(1, n_col), flag=wx.EXPAND)
        grid, n = self.make_preprocess_settings_panel(panel, grid, n, n_span, n_col)

        # unidec
        unidec_label = wx.StaticText(panel, -1, "UniDec")
        set_item_font(unidec_label)
        n += 1
        grid.Add(wx.StaticLine(panel, -1, style=wx.LI_HORIZONTAL), (n, 0), wx.GBSpan(1, n_col), flag=wx.EXPAND)
        n += 1
        grid.Add(unidec_label, (n, 0), wx.GBSpan(1, n_col), flag=wx.ALIGN_CENTER)
        n += 1
        grid.Add(wx.StaticLine(panel, -1, style=wx.LI_HORIZONTAL), (n, 0), wx.GBSpan(1, n_col), flag=wx.EXPAND)
        grid, n = self.make_unidec_settings_panel(panel, grid, n, n_span, n_col)

        # peak detection
        peak_label = wx.StaticText(panel, -1, "Peak detection")
        set_item_font(peak_label)
        n += 1
        grid.Add(wx.StaticLine(panel, -1, style=wx.LI_HORIZONTAL), (n, 0), wx.GBSpan(1, n_col), flag=wx.EXPAND)
        n += 1
        grid.Add(peak_label, (n, 0), wx.GBSpan(1, n_col), flag=wx.ALIGN_CENTER)
        n += 1
        grid.Add(wx.StaticLine(panel, -1, style=wx.LI_HORIZONTAL), (n, 0), wx.GBSpan(1, n_col), flag=wx.EXPAND)
        grid, n = self.make_peaks_settings_panel(panel, grid, n, n_span, n_col)

        # visualisation
        view_label = wx.StaticText(panel, -1, "Visualisation")
        set_item_font(view_label)
        n += 1
        grid.Add(wx.StaticLine(panel, -1, style=wx.LI_HORIZONTAL), (n, 0), wx.GBSpan(1, n_col), flag=wx.EXPAND)
        n += 1
        grid.Add(view_label, (n, 0), wx.GBSpan(1, n_col), flag=wx.ALIGN_CENTER)
        n += 1
        grid.Add(wx.StaticLine(panel, -1, style=wx.LI_HORIZONTAL), (n, 0), wx.GBSpan(1, n_col), flag=wx.EXPAND)
        grid, n = self.make_visualise_settings_panel(panel, grid, n, n_span, n_col)
        grid.AddGrowableCol(0, 1)

        info_sizer = self.make_statusbar(panel)

        settings_sizer = wx.BoxSizer(wx.VERTICAL)
        settings_sizer.Add(grid, 1, wx.EXPAND | wx.ALL, 5)
        settings_sizer.Add(info_sizer, 0, wx.EXPAND, 5)

        # fit layout
        settings_sizer.Fit(panel)
        panel.SetSizerAndFit(settings_sizer)
        panel.SetupScrolling()

        return panel

    def make_buttons_settings_panel(self, panel, grid, n: int, n_span: int, n_col: int):  # noqa
        """Make buttons sub-section"""
        self.unidec_auto_btn = make_bitmap_btn(panel, -1, self._icons.rocket)
        self.unidec_auto_btn.Bind(wx.EVT_BUTTON, self.on_auto_unidec)
        self.unidec_auto_btn.SetToolTip(make_tooltip("Autorun..."))

        self.unidec_init_btn = make_bitmap_btn(panel, -1, self._icons.run)
        self.unidec_init_btn.Bind(wx.EVT_BUTTON, self.on_initialize_unidec)
        self.unidec_init_btn.SetToolTip(make_tooltip("Initialize and pre-process..."))

        self.unidec_unidec_btn = make_bitmap_btn(panel, -1, self._icons.unidec)
        self.unidec_unidec_btn.Bind(wx.EVT_BUTTON, self.on_run_unidec)
        self.unidec_unidec_btn.SetToolTip(make_tooltip("Run UniDec..."))

        self.unidec_peak_btn = make_bitmap_btn(panel, -1, self._icons.peak)
        self.unidec_peak_btn.Bind(wx.EVT_BUTTON, self.on_detect_peaks_unidec)
        self.unidec_peak_btn.SetToolTip(make_tooltip("Detect peaks..."))

        self.unidec_all_btn = wx.Button(panel, wx.ID_OK, "All", size=(40, -1))
        self.unidec_all_btn.Bind(wx.EVT_BUTTON, self.on_all_unidec)
        self.unidec_all_btn.SetToolTip(make_tooltip("Run all..."))

        self.unidec_cancel_btn = wx.Button(panel, wx.ID_OK, "Cancel", size=(-1, -1))
        self.unidec_cancel_btn.Bind(wx.EVT_BUTTON, self.on_close)
        self.unidec_cancel_btn.SetToolTip(make_tooltip("Close window..."))

        self.unidec_customise_btn = make_bitmap_btn(panel, -1, self._icons.gear)
        self.unidec_customise_btn.SetToolTip(make_tooltip("Open customisation window..."))
        self.unidec_customise_btn.Bind(wx.EVT_BUTTON, self.on_open_customisation_settings)

        btn_sizer = wx.BoxSizer()
        btn_sizer.Add(self.unidec_auto_btn, 0, wx.EXPAND)
        btn_sizer.AddSpacer(5)
        btn_sizer.Add(self.unidec_init_btn, 0, wx.EXPAND)
        btn_sizer.AddSpacer(5)
        btn_sizer.Add(self.unidec_unidec_btn, 0, wx.EXPAND)
        btn_sizer.AddSpacer(5)
        btn_sizer.Add(self.unidec_peak_btn, 0, wx.EXPAND)
        btn_sizer.AddSpacer(5)
        btn_sizer.Add(self.unidec_all_btn, 0, wx.EXPAND)
        btn_sizer.AddSpacer(5)
        btn_sizer.Add(self.unidec_cancel_btn, 0, wx.EXPAND)
        btn_sizer.AddSpacer(5)
        btn_sizer.Add(self.unidec_customise_btn, 0, wx.EXPAND)

        grid.Add(btn_sizer, (n, 0), (1, n_col), flag=wx.ALIGN_CENTER_HORIZONTAL)

        return grid, n

    def make_preprocess_settings_panel(self, panel, grid, n: int, n_span: int, n_col: int):  # noqa
        """Make pre-processing sub-section"""

        process_label = wx.StaticText(
            panel,
            wx.ID_ANY,
            "Process MS data before running UniDec. You can change the "
            "\nsettings by clicking on the `Settings` button. Data will be "
            "\nautomatically plotted as you adjust the parameters",
            size=(-1, -1),
        )
        set_item_font(process_label, weight=wx.FONTWEIGHT_NORMAL)

        self.process_settings_btn = make_bitmap_btn(
            panel, -1, self._icons.process_ms, tooltip="Change MS pre-processing parameters"
        )
        self.process_settings_btn.Bind(wx.EVT_BUTTON, self.on_open_process_ms_settings)

        self.process_btn = wx.Button(panel, -1, "Process mass spectrum", size=(-1, -1), name="show_peaks_unidec")
        self.process_btn.Bind(wx.EVT_BUTTON, self.on_process_unidec)

        btn_sizer = wx.BoxSizer()
        btn_sizer.Add(self.process_settings_btn, 0, wx.EXPAND)
        btn_sizer.AddSpacer(5)
        btn_sizer.Add(self.process_btn, 0, wx.EXPAND)

        n += 1
        grid.Add(process_label, (n, 0), (1, n_col), flag=wx.ALIGN_CENTER_HORIZONTAL)
        n += 1
        grid.Add(btn_sizer, (n, 0), (1, n_col), flag=wx.ALIGN_CENTER_HORIZONTAL)

        return grid, n

    def make_unidec_settings_panel(self, panel, grid, n: int, n_span: int, n_col: int):  # noqa
        """Make unidec settings sub-section"""
        z_start_value = wx.StaticText(panel, wx.ID_ANY, "Charge states:")
        self.z_start_value = wx.TextCtrl(panel, -1, "", size=TEXTCTRL_SIZE, validator=Validator("floatPos"))
        self.z_start_value.SetValue(str(CONFIG.unidec_panel_z_start))
        self.z_start_value.Bind(wx.EVT_TEXT, self.on_apply)

        z_end_value = wx.StaticText(panel, wx.ID_ANY, "-")
        self.z_end_value = wx.TextCtrl(panel, -1, "", size=TEXTCTRL_SIZE, validator=Validator("floatPos"))
        self.z_end_value.SetValue(str(CONFIG.unidec_panel_z_end))
        self.z_end_value.Bind(wx.EVT_TEXT, self.on_apply)

        unidec_mw_min_label = wx.StaticText(panel, wx.ID_ANY, "Molecular weights:")
        self.mw_start_value = wx.TextCtrl(panel, -1, "", size=TEXTCTRL_SIZE, validator=Validator("floatPos"))
        self.mw_start_value.SetValue(str(CONFIG.unidec_panel_mw_start))
        self.mw_start_value.Bind(wx.EVT_TEXT, self.on_apply)

        unidec_mw_max_label = wx.StaticText(panel, wx.ID_ANY, "-")
        self.mw_end_value = wx.TextCtrl(panel, -1, "", size=TEXTCTRL_SIZE, validator=Validator("floatPos"))
        self.mw_end_value.SetValue(str(CONFIG.unidec_panel_mw_end))
        self.mw_end_value.Bind(wx.EVT_TEXT, self.on_apply)

        mw_sample_frequency_label = wx.StaticText(panel, wx.ID_ANY, "Sample frequency (Da):")
        self.mw_sample_frequency_value = wx.TextCtrl(panel, -1, "", size=TEXTCTRL_SIZE, validator=Validator("floatPos"))
        self.mw_sample_frequency_value.SetValue(str(CONFIG.unidec_panel_mw_bin_size))
        self.mw_sample_frequency_value.Bind(wx.EVT_TEXT, self.on_apply)

        adduct_mass_value = wx.StaticText(panel, wx.ID_ANY, "Adduct mass:")
        self.adduct_mass_value = wx.TextCtrl(panel, -1, "", size=TEXTCTRL_SIZE, validator=Validator("floatPos"))
        self.adduct_mass_value.SetValue(str(CONFIG.unidec_panel_adduct_mass))
        self.adduct_mass_value.Bind(wx.EVT_TEXT, self.on_apply)

        peak_width_label = wx.StaticText(panel, wx.ID_ANY, "Peak FWHM (Da):")
        self.fit_peak_width_value = wx.TextCtrl(panel, -1, "", size=TEXTCTRL_SIZE, validator=Validator("floatPos"))
        self.fit_peak_width_value.SetValue(str(CONFIG.unidec_panel_peak_width))
        self.fit_peak_width_value.Bind(wx.EVT_TEXT, self.on_apply)
        self.fit_peak_width_value.Bind(wx.EVT_TEXT, self.on_update_peak_width)

        self.peak_width_btn = make_bitmap_btn(panel, -1, self._icons.measure)
        self.peak_width_btn.SetToolTip(make_tooltip("Open peak width tool..."))
        self.peak_width_btn.Bind(wx.EVT_BUTTON, self.on_open_width_tool)

        self.peak_width_auto_check = make_checkbox(panel, "Auto")
        self.peak_width_auto_check.SetValue(CONFIG.unidec_panel_peak_width_auto)
        self.peak_width_auto_check.Bind(wx.EVT_CHECKBOX, self.on_apply)
        self.peak_width_auto_check.Bind(wx.EVT_CHECKBOX, self.on_toggle_controls)

        peak_shape_label = wx.StaticText(panel, wx.ID_ANY, "Peak Shape:")
        self.peak_shape_func_choice = wx.Choice(panel, -1, choices=CONFIG.unidec_panel_peak_func_choices, size=(-1, -1))
        self.peak_shape_func_choice.SetStringSelection(CONFIG.unidec_panel_peak_func)
        self.peak_shape_func_choice.Bind(wx.EVT_CHOICE, self.on_apply)

        softmax_beta_value = wx.StaticText(panel, wx.ID_ANY, "Beta:")
        self.softmax_beta_value = wx.TextCtrl(panel, -1, "", size=TEXTCTRL_SIZE, validator=Validator("floatPos"))
        self.softmax_beta_value.SetValue(str(CONFIG.unidec_panel_softmax_beta))
        self.softmax_beta_value.Bind(wx.EVT_TEXT, self.on_apply)
        set_tooltip(
            self.softmax_beta_value,
            "Parameter for defining the degree of Softmax distribution applied to the charge state vectors."
            "\n0 will shut it off.",
        )

        smooth_z_distribution = wx.StaticText(panel, wx.ID_ANY, "Smooth charge distribution:")
        self.smooth_z_distribution = wx.TextCtrl(panel, -1, "", size=TEXTCTRL_SIZE, validator=Validator("floatPos"))
        self.smooth_z_distribution.SetValue(str(CONFIG.unidec_panel_smooth_charge_distribution))
        self.smooth_z_distribution.Bind(wx.EVT_TEXT, self.on_apply)
        set_tooltip(
            self.smooth_z_distribution,
            "Parameter for defining the width of the charge state smooth."
            "\nUniDec will use a mean filter of width 2n+1 on log_e of the charge distribution",
        )

        smooth_nearby_points = wx.StaticText(panel, wx.ID_ANY, "Point smooth width:")
        self.smooth_nearby_points = wx.TextCtrl(panel, -1, "", size=TEXTCTRL_SIZE, validator=Validator("floatPos"))
        self.smooth_nearby_points.SetValue(str(CONFIG.unidec_panel_smooth_nearby_points))
        self.smooth_nearby_points.Bind(wx.EVT_TEXT, self.on_apply)
        set_tooltip(
            self.smooth_nearby_points,
            "Parameter for defining the width of the data point smooth."
            "\nUniDec will weight +/- n data points to have the same charge state.",
        )

        mass_nearby_points = wx.StaticText(panel, wx.ID_ANY, "Mass smooth width:")
        self.mass_nearby_points = wx.TextCtrl(panel, -1, "", size=TEXTCTRL_SIZE, validator=Validator("floatPos"))
        self.mass_nearby_points.SetValue(str(CONFIG.unidec_panel_smooth_mass_width))
        self.mass_nearby_points.Bind(wx.EVT_TEXT, self.on_apply)
        set_tooltip(self.mass_nearby_points, "Width of the mass smooth filter")

        mz_to_mw_transform_choice = wx.StaticText(panel, wx.ID_ANY, "m/z to MW transformation:")
        self.mz_to_mw_transform_choice = wx.Choice(
            panel, -1, choices=CONFIG.unidec_panel_mz_to_mw_transform_choices, size=(-1, -1)
        )
        self.mz_to_mw_transform_choice.SetStringSelection(CONFIG.unidec_panel_mz_to_mw_transform)
        self.mz_to_mw_transform_choice.Bind(wx.EVT_CHOICE, self.on_apply)

        negative_mode_check = wx.StaticText(panel, wx.ID_ANY, "Negative ionization mode:")
        self.negative_mode_check = make_checkbox(panel, "")
        self.negative_mode_check.SetValue(CONFIG.unidec_panel_negative_mode)
        self.negative_mode_check.Bind(wx.EVT_CHECKBOX, self.on_apply)
        self.negative_mode_check.Bind(wx.EVT_CHECKBOX, self.on_update_polarity)

        # buttons
        self.run_unidec_btn = wx.Button(panel, -1, "Run UniDec", size=BTN_SIZE, name="run_unidec")
        self.run_unidec_btn.Bind(wx.EVT_BUTTON, self.on_run_unidec)

        btn_sizer = wx.BoxSizer()
        btn_sizer.Add(self.run_unidec_btn, 0, wx.EXPAND)

        # pack elements
        n += 1
        grid.Add(z_start_value, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.z_start_value, (n, 1), flag=wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)
        grid.Add(z_end_value, (n, 2), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_CENTER_HORIZONTAL)
        grid.Add(self.z_end_value, (n, 3), flag=wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)
        n += 1
        grid.Add(unidec_mw_min_label, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.mw_start_value, (n, 1), flag=wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)
        grid.Add(unidec_mw_max_label, (n, 2), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_CENTER_HORIZONTAL)
        grid.Add(self.mw_end_value, (n, 3), flag=wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)
        n += 1
        grid.Add(mw_sample_frequency_label, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.mw_sample_frequency_value, (n, 1), flag=wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)
        n += 1
        grid.Add(adduct_mass_value, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.adduct_mass_value, (n, 1), flag=wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        n += 1
        grid.Add(peak_width_label, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.fit_peak_width_value, (n, 1), flag=wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)
        grid.Add(self.peak_width_btn, (n, 2), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_CENTER_HORIZONTAL)
        grid.Add(self.peak_width_auto_check, (n, 3), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_CENTER_HORIZONTAL)
        n += 1
        grid.Add(peak_shape_label, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.peak_shape_func_choice, (n, 1), flag=wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        n += 1
        grid.Add(mz_to_mw_transform_choice, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.mz_to_mw_transform_choice, (n, 1), flag=wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        n += 1
        grid.Add(softmax_beta_value, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.softmax_beta_value, (n, 1), flag=wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        n += 1
        grid.Add(smooth_z_distribution, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.smooth_z_distribution, (n, 1), flag=wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        n += 1
        grid.Add(smooth_nearby_points, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.smooth_nearby_points, (n, 1), flag=wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        n += 1
        grid.Add(mass_nearby_points, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.mass_nearby_points, (n, 1), flag=wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        n += 1
        grid.Add(negative_mode_check, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.negative_mode_check, (n, 1), flag=wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        n += 1
        grid.Add(btn_sizer, (n, 0), (1, n_col), flag=wx.ALIGN_CENTER_HORIZONTAL)

        return grid, n

    def make_peaks_settings_panel(self, panel, grid, n: int, n_span: int, n_col: int):  # noqa
        """Make peaks sub-section"""
        peak_width_value = wx.StaticText(panel, wx.ID_ANY, "Window (Da):")
        self.peak_width_value = wx.TextCtrl(panel, -1, "", size=TEXTCTRL_SIZE, validator=Validator("floatPos"))
        self.peak_width_value.SetValue(str(CONFIG.unidec_panel_peak_detect_width))
        self.peak_width_value.Bind(wx.EVT_TEXT, self.on_apply)

        unidec_peak_threshold_label = wx.StaticText(panel, wx.ID_ANY, "Threshold:")
        self.peak_threshold_value = wx.TextCtrl(panel, -1, "", size=TEXTCTRL_SIZE, validator=Validator("floatPos"))
        self.peak_threshold_value.SetValue(str(CONFIG.unidec_panel_peak_detect_threshold))
        self.peak_threshold_value.Bind(wx.EVT_TEXT, self.on_apply)

        peak_normalization_choice = wx.StaticText(panel, wx.ID_ANY, "Normalization:")
        self.peak_normalization_choice = wx.Choice(
            panel, -1, choices=CONFIG.unidec_panel_peak_detect_norm_choices, size=(-1, -1)
        )
        self.peak_normalization_choice.SetStringSelection(CONFIG.unidec_panel_peak_detect_norm)
        self.peak_normalization_choice.Bind(wx.EVT_CHOICE, self.on_apply)

        line_separation_value = wx.StaticText(panel, wx.ID_ANY, "Line separation:")
        self.line_separation_value = wx.TextCtrl(panel, -1, "", size=TEXTCTRL_SIZE, validator=Validator("floatPos"))
        self.line_separation_value.SetValue(str(CONFIG.unidec_panel_plot_line_sep))
        self.line_separation_value.Bind(wx.EVT_TEXT, self.on_apply)

        markers_label = wx.StaticText(panel, wx.ID_ANY, "Show markers:")
        self.markers_check = make_checkbox(panel, "")
        self.markers_check.SetValue(CONFIG.unidec_panel_plot_markers_show)
        self.markers_check.Bind(wx.EVT_CHECKBOX, self.on_apply)
        self.markers_check.Bind(wx.EVT_CHECKBOX, self.on_show_peaks_unidec)

        individual_line_check = wx.StaticText(panel, wx.ID_ANY, "Show individual lines:")
        self.individual_line_check = make_checkbox(panel, "")
        self.individual_line_check.SetValue(CONFIG.unidec_panel_plot_line_show)
        self.individual_line_check.Bind(wx.EVT_CHECKBOX, self.on_apply)
        self.individual_line_check.Bind(wx.EVT_CHECKBOX, self.on_show_peaks_unidec)

        self.detect_peaks_btn = wx.Button(panel, -1, "Detect peaks", size=BTN_SIZE, name="pick_peaks_unidec")
        self.detect_peaks_btn.Bind(wx.EVT_BUTTON, self.on_detect_peaks_unidec)

        self.show_peaks_btn = wx.Button(panel, -1, "Show peaks", size=BTN_SIZE, name="show_peaks_unidec")
        self.show_peaks_btn.Bind(wx.EVT_BUTTON, self.on_show_peaks_unidec)

        btn_sizer = wx.BoxSizer()
        btn_sizer.Add(self.detect_peaks_btn, 0, wx.EXPAND)
        btn_sizer.AddSpacer(5)
        btn_sizer.Add(self.show_peaks_btn, 0, wx.EXPAND)

        n += 1
        grid.Add(peak_width_value, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.peak_width_value, (n, 1), flag=wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        n += 1
        grid.Add(unidec_peak_threshold_label, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.peak_threshold_value, (n, 1), flag=wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        n += 1
        grid.Add(peak_normalization_choice, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.peak_normalization_choice, (n, 1), flag=wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        n += 1
        grid.Add(line_separation_value, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.line_separation_value, (n, 1), flag=wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        n += 1
        grid.Add(markers_label, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.markers_check, (n, 1), flag=wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        n += 1
        grid.Add(individual_line_check, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.individual_line_check, (n, 1), flag=wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        n += 1
        grid.Add(btn_sizer, (n, 0), (1, n_col), flag=wx.ALIGN_CENTER_HORIZONTAL)

        return grid, n

    def make_visualise_settings_panel(self, panel, grid, n: int, n_span: int, n_col: int):  # noqa
        """Make visualisation sub-section"""
        unidec_plotting_weights_label = wx.StaticText(panel, wx.ID_ANY, "Molecular weights:")
        self.weight_list_choice = wx.ComboBox(
            panel, -1, choices=[], size=(150, -1), style=wx.CB_READONLY, name="ChargeStates"
        )
        self.weight_list_choice.Bind(wx.EVT_COMBOBOX, self.on_isolate_peak_unidec)

        self.weight_list_sort = make_bitmap_btn(panel, -1, self._icons.sort)
        self.weight_list_sort.SetBackgroundColour((240, 240, 240))
        self.weight_list_sort.Bind(wx.EVT_BUTTON, self.on_sort_unidec_mw)

        charges_label = wx.StaticText(panel, wx.ID_ANY, "Show charges:")
        self.charges_check = make_checkbox(panel, "")
        self.charges_check.SetValue(CONFIG.unidec_panel_plot_charges_show)
        self.charges_check.Bind(wx.EVT_CHECKBOX, self.on_apply)
        self.charges_check.Bind(wx.EVT_CHECKBOX, self.on_show_charge_states_unidec)
        self.charges_check.Bind(wx.EVT_CHECKBOX, self.on_toggle_controls)

        adduct_choice = wx.StaticText(panel, wx.ID_ANY, "Adduct:")
        self.adduct_choice = wx.Choice(
            panel,
            -1,
            choices=["H+", "H+ Na+", "Na+", "Na+ x2", "Na+ x3", "K+", "K+ x2", "K+ x3", "NH4+", "H-", "Cl-"],
            size=(-1, -1),
            name="ChargeStates",
        )
        self.adduct_choice.SetStringSelection("H+")
        self.adduct_choice.Bind(wx.EVT_CHOICE, self.on_show_charge_states_unidec)

        unidec_charges_threshold_label = wx.StaticText(panel, wx.ID_ANY, "Intensity threshold:")
        self.charges_threshold_value = wx.SpinCtrlDouble(
            panel,
            -1,
            value=str(CONFIG.unidec_panel_plot_charges_label_threshold),
            min=0,
            max=1,
            initial=CONFIG.unidec_panel_plot_charges_label_threshold,
            inc=0.01,
            size=(90, -1),
        )
        self.charges_threshold_value.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_apply)
        self.charges_threshold_value.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_show_charge_states_unidec)

        unidec_charges_offset_label = wx.StaticText(panel, wx.ID_ANY, "Vertical charge offset:")
        self.charges_offset_value = wx.SpinCtrlDouble(
            panel,
            -1,
            value=str(CONFIG.unidec_panel_plot_charges_label_offset),
            min=0,
            max=1,
            initial=CONFIG.unidec_panel_plot_charges_label_offset,
            inc=0.05,
            size=(90, -1),
        )
        self.charges_offset_value.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_apply)
        self.charges_offset_value.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_show_charge_states_unidec)

        self.restore_all_btn = wx.Button(panel, -1, "Restore all", size=(-1, -1))
        self.restore_all_btn.Bind(wx.EVT_BUTTON, self.on_show_peaks_unidec)

        self.isolate_charges_btn = wx.Button(panel, -1, "Isolate", size=(-1, -1))
        self.isolate_charges_btn.Bind(wx.EVT_BUTTON, self.on_isolate_peak_unidec)

        self.label_charges_btn = wx.Button(panel, -1, "Label", size=(-1, -1))
        self.label_charges_btn.Bind(wx.EVT_BUTTON, self.on_show_charge_states_unidec)

        btn_sizer = wx.BoxSizer()
        btn_sizer.Add(self.restore_all_btn, 0, wx.EXPAND)
        btn_sizer.AddSpacer(5)
        btn_sizer.Add(self.isolate_charges_btn, 0, wx.EXPAND)
        btn_sizer.AddSpacer(5)
        btn_sizer.Add(self.label_charges_btn, 0, wx.EXPAND)

        # pack elements
        n += 1
        grid.Add(unidec_plotting_weights_label, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.weight_list_choice, (n, 1), wx.GBSpan(1, 2), flag=wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)
        grid.Add(self.weight_list_sort, (n, 3), flag=wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL)
        n += 1
        grid.Add(charges_label, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.charges_check, (n, 1), flag=wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)
        n += 1
        grid.Add(adduct_choice, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.adduct_choice, (n, 1), flag=wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)
        n += 1
        grid.Add(unidec_charges_threshold_label, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.charges_threshold_value, (n, 1), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        n += 1
        grid.Add(unidec_charges_offset_label, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.charges_offset_value, (n, 1), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        n += 1
        grid.Add(btn_sizer, (n, 0), (1, n_col), flag=wx.ALIGN_CENTER_HORIZONTAL)

        return grid, n

    def on_toggle_controls(self, evt):
        """Event driven GUI updates"""

        CONFIG.unidec_panel_peak_width_auto = self.peak_width_auto_check.GetValue()
        obj_list = [self.fit_peak_width_value, self.peak_width_btn]
        for item in obj_list:
            item.Enable(enable=not CONFIG.unidec_panel_peak_width_auto)

        CONFIG.unidec_panel_plot_charges_show = self.charges_check.GetValue()
        obj_list = [self.adduct_choice, self.charges_threshold_value, self.charges_offset_value, self.label_charges_btn]
        for item in obj_list:
            item.Enable(enable=CONFIG.unidec_panel_plot_charges_show)

        if evt is not None:
            evt.Skip()

    def on_update_polarity(self, evt):
        """Update several values after user clicked the `Negative ionisation mode` checkbox"""
        print("on_update_polarity", self)

        if evt is not None:
            evt.Skip()

    def on_apply(self, evt):
        """Event driven GUI updates"""
        CONFIG.unidec_panel_z_start = str2int(self.z_start_value.GetValue())
        CONFIG.unidec_panel_z_end = str2int(self.z_end_value.GetValue())
        CONFIG.unidec_panel_mw_start = str2num(self.mw_start_value.GetValue())
        CONFIG.unidec_panel_mw_end = str2num(self.mw_end_value.GetValue())
        CONFIG.unidec_panel_mw_bin_size = str2num(self.mw_sample_frequency_value.GetValue())
        CONFIG.unidec_panel_peak_width = str2num(self.fit_peak_width_value.GetValue())
        CONFIG.unidec_panel_peak_func = self.peak_shape_func_choice.GetStringSelection()
        CONFIG.unidec_panel_peak_width_auto = self.peak_width_auto_check.GetValue()
        CONFIG.unidec_panel_softmax_beta = self.softmax_beta_value.GetValue()
        CONFIG.unidec_panel_smooth_charge_distribution = self.smooth_z_distribution.GetValue()
        CONFIG.unidec_panel_smooth_nearby_points = self.smooth_nearby_points.GetValue()
        CONFIG.unidec_panel_smooth_mass_width = self.mass_nearby_points.GetValue()
        CONFIG.unidec_panel_mz_to_mw_transform = self.mz_to_mw_transform_choice.GetStringSelection()
        CONFIG.unidec_panel_negative_mode = self.negative_mode_check.GetValue()
        CONFIG.unidec_panel_adduct_mass = str2num(self.adduct_mass_value.GetValue())

        CONFIG.unidec_panel_peak_detect_width = str2num(self.peak_width_value.GetValue())
        CONFIG.unidec_panel_peak_detect_threshold = str2num(self.peak_threshold_value.GetValue())
        CONFIG.unidec_panel_peak_detect_norm = self.peak_normalization_choice.GetStringSelection()
        CONFIG.unidec_panel_plot_line_sep = str2num(self.line_separation_value.GetValue())

        CONFIG.unidec_panel_plot_markers_show = self.markers_check.GetValue()
        CONFIG.unidec_panel_plot_line_show = self.individual_line_check.GetValue()

        CONFIG.unidec_panel_plot_charges_label_threshold = str2num(self.charges_threshold_value.GetValue())
        CONFIG.unidec_panel_plot_charges_label_offset = str2num(self.charges_offset_value.GetValue())
        CONFIG.unidec_panel_plot_charges_show = self.charges_check.GetValue()

        if evt is not None:
            evt.Skip()

    def on_page_changed(self, _evt):
        """Triggered by change of panel in the plot section"""
        # get current page
        self.current_page = self.plot_notebook.GetPageText(self.plot_notebook.GetSelection())
        view = self.get_view_from_name(self.current_page)
        pub.sendMessage("view.activate", view_id=view.PLOT_ID)

    def get_view_from_name(self, plot_name: str = None):
        """Retrieve view from name"""
        plot_dict = {
            "ms": self.view_mz,
            "mw": self.view_mw,
            "m/z vs charge": self.view_mz_grid,
            "mw vs charge": self.view_mw_grid,
            "isolated ms": self.view_peaks,
            "barchart": self.view_barchart,
            "charge distribution": self.view_charge,
        }
        if plot_name is None:
            plot_name = self.current_page
        plot_name = plot_name.lower()
        plot_obj = plot_dict.get(plot_name, None)
        if plot_obj is None:
            logger.error(f"Could not find view object with name `{plot_name}")
        return plot_obj

    def on_save_all_figures(self, evt):
        """Save all figures"""
        for view in [
            self.view_mz,
            self.view_mw,
            self.view_mz_grid,
            self.view_mw_grid,
            self.view_peaks,
            self.view_barchart,
            self.view_charge,
        ]:
            view.on_save_figure(evt)

    def on_open_customisation_settings(self, _evt):
        """Open UniDec customisation window"""
        from origami.widgets.unidec.dialog_customise_unidec_visuals import DialogCustomiseUniDecVisuals

        dlg = DialogCustomiseUniDecVisuals(self)
        dlg.ShowModal()

    def on_open_width_tool(self, _evt):
        """Open UniDec width tool"""
        from origami.widgets.unidec.panel_process_unidec_peak_width_tool import PanelPeakWidthTool

        if not self._dlg_width_tool:
            self._dlg_width_tool = PanelPeakWidthTool(self, self.presenter, self.view, self.mz_obj)
        self._dlg_width_tool.Show()
        self._dlg_width_tool.SetFocus()

    def on_open_process_ms_settings(self, _evt):
        """Open MS pre-processing panel"""
        from origami.gui_elements.panel_process_spectrum import PanelProcessMassSpectrum

        if not self._dlg_ms_process_tool:
            self._dlg_ms_process_tool = PanelProcessMassSpectrum(
                self.view,
                self.presenter,
                disable_plot=True,
                disable_process=True,
                update_widget=self.PUB_SUBSCRIBE_EVENT,
            )
        self._dlg_ms_process_tool.Show()
        self._dlg_ms_process_tool.SetFocus()

    def on_sort_unidec_mw(self, _evt):
        """Sort molecular weights"""
        if self._unidec_sort_column == 0:
            self._unidec_sort_column = 1
        else:
            self._unidec_sort_column = 0

        mass_list = self.weight_list_choice.GetItems()
        mass_list = unidec_sort_mw_list(mass_list, self._unidec_sort_column)

        self.weight_list_choice.SetItems(mass_list)
        self.weight_list_choice.SetStringSelection(mass_list[0])

    def on_show_peaks_unidec(self, _evt):
        """Show peaks"""
        # self.data_processing.on_threading("custom.action", ("show_peak_lines_and_markers",), fcn=self.on_plot)

    def on_process(self):
        """Process mass spectrum"""
        if CONFIG.unidec_engine is not None:
            wx.CallAfter(self.on_process_unidec, None)
        else:
            logger.warning("UniDec engine has not been initialized yet")

    def on_plot(self, task):
        """Plot data"""
        # update settings first
        print("on_plot", task)
        self.on_apply(None)

    #
    #     # generate kwargs
    #     kwargs = {
    #         "show_markers": CONFIG.unidec_show_markers,
    #         "show_individual_lines": CONFIG.unidec_show_individualComponents,
    #         "speedy": CONFIG.unidec_speedy,
    #     }
    #
    #     try:
    #         # get data and plot in the panel
    #         data = self.on_get_unidec_data()
    #         if data:
    #             # called after `pre-processed` is executed
    #             if task in ["all", "preprocess_unidec", "load_data_and_preprocess_unidec"]:
    #                 replot_data = data.get("Processed", None)
    #                 if replot_data:
    #                     self.panel_plot.on_plot_unidec_MS(
    #                         replot=replot_data, plot=None, plot_obj=self.plotUnidec_MS, **kwargs
    #                     )
    #
    #             # called after `run unidec` is executed
    #             if task in ["all", "run_unidec"]:
    #                 replot_data = data.get("Fitted", None)
    #                 if replot_data:
    #                     self.panel_plot.on_plot_unidec_MS_v_Fit(
    #                         replot=replot_data, plot=None, plot_obj=self.plotUnidec_MS, **kwargs
    #                     )
    #                 replot_data = data.get("MW distribution", None)
    #                 if replot_data:
    #                     self.panel_plot.on_plot_unidec_mwDistribution(
    #                         replot=replot_data, plot=None, plot_obj=self.plotUnidec_mwDistribution, **kwargs
    #                     )
    #                 replot_data = data.get("m/z vs Charge", None)
    #                 if replot_data:
    #                     self.panel_plot.on_plot_unidec_mzGrid(
    #                         replot=replot_data, plot=None, plot_obj=self.plotUnidec_mzGrid, **kwargs
    #                     )
    #                 replot_data = data.get("MW vs Charge", None)
    #                 if replot_data:
    #                     self.panel_plot.on_plot_unidec_MW_v_Charge(
    #                         replot=replot_data, plot=None, plot_obj=self.plotUnidec_mwVsZ, **kwargs
    #                     )
    #
    #             # called after `detect peaks` is executed
    #             if task in ["all", "pick_peaks_unidec"]:
    #                 # update mass list
    #                 self.on_update_mass_list()
    #
    #                 replot_data = data.get("m/z with isolated species", None)
    #                 if replot_data:
    #                     self.panel_plot.on_plot_unidec_individualPeaks(
    #                         replot=replot_data, plot=None, plot_obj=self.plotUnidec_individualPeaks, **kwargs
    #                     )
    #                     self.on_plot_mw_normalization()
    #                     self.panel_plot.on_plot_unidec_MW_add_markers(
    #                         data["m/z with isolated species"],
    #                         data["MW distribution"],
    #                         plot=None,
    #                         plot_obj=self.plotUnidec_mwDistribution,
    #                         **kwargs,
    #                     )
    #                 replot_data = data.get("Barchart", None)
    #                 if replot_data:
    #                     self.panel_plot.on_plot_unidec_barChart(
    #                         replot=replot_data, plot=None, plot_obj=self.plotUnidec_barChart, **kwargs
    #                     )
    #                 replot_data = data.get("Charge information", None)
    #                 if replot_data is not None:
    #                     self.panel_plot.on_plot_unidec_ChargeDistribution(
    #                         replot=replot_data, plot=None, plot_obj=self.plotUnidec_chargeDistribution, **kwargs
    #                     )
    #
    #             # called after `show peaks` is exectured
    #             if task in ["show_peak_lines_and_markers"]:
    #                 replot_data = data.get("m/z with isolated species", None)
    #                 if replot_data:
    #                     self.panel_plot.on_plot_unidec_add_individual_lines_and_markers(
    #                         replot=replot_data, plot=None, plot_obj=self.plotUnidec_individualPeaks, **kwargs
    #                     )
    #                 else:
    #                     raise MessageError("Missing data", "Please detect peaks first")
    #
    #             # called after `isolate` is executed
    #             if task in ["isolate_mw_unidec"]:
    #                 mw_selection = "MW: {}".format(self.unidec_weightList_choice.GetStringSelection().split()[1])
    #                 kwargs["show_isolated_mw"] = True
    #                 kwargs["mw_selection"] = mw_selection
    #                 replot_data = data.get("m/z with isolated species", None)
    #                 if replot_data:
    #                     self.panel_plot.on_plot_unidec_add_individual_lines_and_markers(
    #                         replot=replot_data, plot=None, plot_obj=self.plotUnidec_individualPeaks, **kwargs
    #                     )
    #
    #             # show individual charge states
    #             if task in ["charge_states"]:
    #                 charges = data["Charge information"]
    #                 xvals = data["Processed"]["xvals"]
    #
    #                 mw_selection = self.unidec_weightList_choice.GetStringSelection().split()[1]
    #                 adduct_ion = self.unidec_adductMW_choice.GetStringSelection()
    #
    #                 peakpos, charges, __ = unidec_utils.calculate_charge_positions(
    #                     charges, mw_selection, xvals, adduct_ion, remove_below=CONFIG.unidec_charges_label_charges
    #                 )
    #                 self.panel_plot.on_plot_charge_states(
    #                     peakpos, charges, plot=None, plot_obj=self.plotUnidec_individualPeaks, **kwargs
    #                 )
    #
    #         # update peak width
    #         self.on_update_peak_width()
    #     except RuntimeError:
    #         logger.warning("The panel was closed before the action could be completed")

    def on_update_peak_width(self):
        """Update peak width"""
        self.fit_peak_width_value.SetValue(f"{CONFIG.unidec_panel_peak_width:.4f}")

    def on_plot_mw_normalization(self):
        """Trigger replot of the MW plot since the scaling might change"""
        # try:
        #     replot_data = dict(
        #         xvals=CONFIG.unidec_engine.data.massdat[:, 0], yvals=CONFIG.unidec_engine.data.massdat[:, 1]
        #     )
        # except IndexError:
        #     return
        #
        # if replot_data:
        #     self.panel_plot.on_plot_unidec_mwDistribution(
        #         replot=replot_data, plot=None, plot_obj=self.plotUnidec_mwDistribution
        #     )

    def on_clear_plot_as_task(self, task):
        """Clear plots"""
        if task in ["all", "init", "preprocess"]:
            self.view_mz.clear()

        if task in ["all", "init", "preprocess", "run"]:
            self.view_mw.clear()
            self.view_mw_grid.clear()
            self.view_mz_grid.clear()
            self.view_peaks.clear()
            self.view_charge.clear()
            self.view_barchart.clear()

        if task in ["peaks"]:
            self.view_peaks.clear()
            self.view_barchart.clear()

    @staticmethod
    def check_unidec_engine(state: str):
        """Checks whether UniDec engine has been instantiated"""
        if CONFIG.unidec_engine is None:
            return False

        if state == "init":
            return True
        if state == "preprocessed":
            return CONFIG.unidec_engine.is_processed
        if state == "executed":
            return CONFIG.unidec_engine.is_executed

    def on_initialize_unidec(self, _evt):
        """Initialize UniDec"""
        QUEUE.add_call(
            UNIDEC_HANDLER.unidec_initialize_and_preprocess,
            (self.mz_obj, None),
            func_result=self.on_show_initialize_unidec,
        )

    def on_show_initialize_unidec(self, unidec_engine: UniDecResultsObject):
        """Show UniDec results"""
        self.on_clear_plot_as_task("all")
        self.on_show_process_unidec(unidec_engine)

    def on_process_unidec(self, _evt):
        """Process mass spectrum"""
        self.on_clear_plot_as_task("preprocess")
        QUEUE.add_call(
            UNIDEC_HANDLER.unidec_initialize_and_preprocess,
            (self.mz_obj, None),
            func_result=self.on_show_process_unidec,
        )

    def on_show_process_unidec(self, unidec_engine: UniDecResultsObject):
        """Show UniDec results"""
        if CONFIG.ms_normalize:
            self.mz_obj.normalize()
        self.view_mz.plot(obj=self.mz_obj, label="Raw", repaint=False)
        self.view_mz.add_line(
            obj=unidec_engine.mz_processed_obj, line_color=CONFIG.unidec_plot_fit_lineColor, label="Fit data"
        )

    def on_run_unidec(self, _evt):
        """Run UniDec"""
        if self.check_unidec_engine("preprocessed"):
            self.on_clear_plot_as_task("run")
            QUEUE.add_call(UNIDEC_HANDLER.unidec_run, (), func_result=self.on_show_run_unidec)
        else:
            raise MessageError("Error", "Mass spectrum has not been pre-processed yet - please pre-process it first")

    def on_show_run_unidec(self, unidec_engine: UniDecResultsObject):
        """Show UniDec results"""
        self.view_mw.plot(obj=unidec_engine.mw_obj)
        self.view_mz_grid.plot(obj=unidec_engine.mz_grid_obj)
        self.view_mw_grid.plot(obj=unidec_engine.mw_grid_obj)

    def on_detect_peaks_unidec(self, _evt):
        """Detect features"""
        if self.check_unidec_engine("executed"):
            self.on_clear_plot_as_task("peaks")
            QUEUE.add_call(UNIDEC_HANDLER.unidec_find_peaks, (), func_result=self.on_show_detect_peaks_unidec)
        else:
            raise MessageError(
                "Error", "UniDec has not been executed yet - please execute it before trying peak picking"
            )

    def on_show_detect_peaks_unidec(self, unidec_engine: UniDecResultsObject):
        """Show UniDec results"""
        # add markers to the MW plot
        self.view_mw.remove_scatter()
        peaks = unidec_engine.peaks
        mw_obj = unidec_engine.mw_obj

        # update MW plot data
        self.view_mw.plot(obj=mw_obj)

        # add markers
        # since the mw can be divided by 1000, we need to ensure that peak position is also transformed
        masses = mw_obj.x_axis_transform(peaks.masses)
        for x, y, color, marker, label in zip(masses, peaks.intensities, peaks.colors, peaks.markers, peaks.labels):
            self.view_mw.add_scatter(
                x, y, color, marker, size=CONFIG.unidec_plot_MW_markerSize, label=label, repaint=False
            )
        self.view_mw.show_legend(True)

        # show barchart
        self.view_barchart.plot(obj=peaks)

        # show charge states
        self.view_charge.plot(obj=unidec_engine.z_obj)

    def on_all_unidec(self, _evt):
        """Run all"""
        QUEUE.add_call(UNIDEC_HANDLER.unidec_autorun, (self.mz_obj, None), func_result=self.on_show_all_unidec)

    def on_show_all_unidec(self, unidec_engine: UniDecResultsObject):
        """Show UniDec results"""
        self.on_show_initialize_unidec(unidec_engine)
        self.on_show_run_unidec(unidec_engine)
        self.on_show_detect_peaks_unidec(unidec_engine)

    def on_auto_unidec(self, _evt):
        """Auto UniDec"""
        QUEUE.add_call(UNIDEC_HANDLER.unidec_autorun, (self.mz_obj, None), func_result=self.on_show_autorun_unidec)

    def on_show_autorun_unidec(self, unidec_engine: UniDecResultsObject):
        """Show UniDec results"""
        self.on_show_initialize_unidec(unidec_engine)
        self.on_show_run_unidec(unidec_engine)
        self.on_show_detect_peaks_unidec(unidec_engine)

    def on_isolate_peak_unidec(self, _evt):
        """Isolate peaks"""
        # self.on_plot("isolate_mw_unidec")
        # self.on_plot("charge_states")

    def on_show_charge_states_unidec(self, evt):
        """Show charge states"""
        print("on_show_charge_states_unidec", self)
        # self.on_plot("charge_states")

        if evt is not None:
            evt.Skip()

    def on_update_mass_list(self):
        """Update mass list"""
        # data = self.on_get_unidec_data()
        # data = data.get("m/z with isolated species", None)
        # if data:
        #     mass_list, mass_max = data["_massList_"]
        #     self.weight_list_choice.SetItems(mass_list)
        #     self.weight_list_choice.SetStringSelection(mass_max)


def _main():
    from origami.icons.assets import Icons
    from origami.handlers.load import LoadHandler

    path = r"D:\Data\ORIGAMI\text_files\MS_p27-FL-K31.csv"
    loader = LoadHandler()
    document = loader.load_text_mass_spectrum_document(path)
    mz_obj = document["MassSpectra/Summed Spectrum", True]

    app = wx.App()
    icons = Icons()
    ex = PanelProcessUniDec(None, None, icons, mz_obj=mz_obj)
    ex.Show()
    app.MainLoop()


if __name__ == "__main__":
    _main()