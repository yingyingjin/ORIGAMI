"""ORIGAMI parameters dialog"""
# Standard library imports
import os
import logging

# Third-party imports
import wx
import numpy as np

# Local imports
import origami.widgets.origami_ms.processing.origami_ms as pr_origami
from origami.styles import Dialog
from origami.styles import Validator
from origami.config.config import CONFIG
from origami.objects.document import DocumentGroups
from origami.utils.converters import str2int
from origami.utils.converters import str2num
from origami.utils.exceptions import MessageError
from origami.config.environment import ENV
from origami.gui_elements.misc_dialogs import DialogBox
from origami.gui_elements.views.view_spectrum import ViewSpectrum

LOGGER = logging.getLogger(__name__)

# TODO: Add limits to some of the parameters as in ORIGAMI-MS GUI
#    Botlzmann offset: min = 10.0 max = 100
#    exponential increment < 0.075 and > 0.0


class DialogOrigamiMsSettings(Dialog):
    """Dialog to setup ORIGAMI-MS settings"""

    # UI elements
    origami_method_choice = None
    origami_scansPerVoltage_value = None
    origami_start_scan_value = None
    origami_start_voltage_value = None
    origami_end_voltage_value = None
    origami_step_voltage_value = None
    origami_boltzmann_offset_value = None
    origami_exponential_percentage_value = None
    origami_exponential_increment_value = None
    origami_load_list_btn = None
    origami_calculate_btn = None
    origami_apply_btn = None
    origami_cancel_btn = None
    view_cv = None
    plot_panel = None
    info_value = None
    preprocess_check = None
    process_btn = None
    origami_extract_btn = None
    user_settings = dict()

    def __init__(self, parent, presenter, document_title: str = None, debug: bool = False):
        Dialog.__init__(
            self,
            parent,
            title="ORIGAMI-MS settings...",
            style=wx.DEFAULT_FRAME_STYLE | wx.RESIZE_BORDER & ~wx.MAXIMIZE_BOX,
        )
        self.view = parent
        self.presenter = presenter
        self._debug = debug

        self.document_title = document_title
        if self.document_title is None and not self._debug:
            document = ENV.on_get_document()
            if document is None:
                self.Destroy()
                raise MessageError(
                    "Please load a document",
                    "Could not find a document. Please load a document before trying this action again",
                )
            self.document_title = document.title

        # load user settings from configuration file
        self.user_settings = self.on_setup_gui()
        self.user_settings_changed = False

        self._window_size = self._get_window_size(self.parent, [0.5, 0.4])

        self.make_gui()
        self.on_toggle_controls(None)
        self.Layout()
        self.CenterOnParent()
        self.SetFocus()
        self.SetTitle(f"ORIGAMI-MS settings: {self.document_title}")

        # bind events
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_CONTEXT_MENU, self.on_right_click)

        # instantiate
        self.on_plot()

    @property
    def data_handling(self):
        """Return handle to `data_handling`"""
        return self.presenter.data_handling

    @property
    def document_tree(self):
        """Return handle to `document_tree`"""
        return self.presenter.view.panelDocuments.documents

    def on_right_click(self, evt):
        """Right-click menu"""
        if hasattr(evt.EventObject, "figure"):
            menu = self.view_cv.get_right_click_menu(self)

            self.PopupMenu(menu)
            menu.Destroy()
            self.SetFocus()

    def on_setup_gui(self):
        """Setup UI with correct parameters"""
        document = ENV.on_get_document(self.document_title)

        origami_settings = None
        if document is not None:
            origami_settings = document.get_config("origami_ms")

        # there are no user specified settings yet, so we preset them with the global settings
        if origami_settings is None:
            origami_settings = {
                "method": CONFIG.origami_method,
                "start_scan": CONFIG.origami_start_scan,
                "scans_per_voltage": CONFIG.origami_scans_per_voltage,
                "start_voltage": CONFIG.origami_start_voltage,
                "end_voltage": CONFIG.origami_end_voltage,
                "step_voltage": CONFIG.origami_step_voltage,
                "boltzmann_offset": CONFIG.origami_boltzmann_offset,
                "exponential_percentage": CONFIG.origami_exponential_percentage,
                "exponential_increment": CONFIG.origami_exponential_increment,
                "start_scan_end_scan_cv_list": [],
            }
            # update document with these global settings
            if document:
                document.add_config("origami_ms", origami_settings)
                LOGGER.info("Document did not have any ORIGAMI-MS settings present")

        return origami_settings

    def on_close(self, evt, force: bool = False):
        """Destroy this frame"""

        if self.user_settings_changed and not self._debug and not force:
            dlg = DialogBox(
                title="Would you like to continue?",
                msg="You've made some changes to the ORIGAMI-MS settings but have not saved them."
                "\nWould you like to continue?",
                kind="Question",
            )
            if dlg == wx.ID_NO:
                return

        super(DialogOrigamiMsSettings, self).on_close(evt, force)

    def on_ok(self, _=None):
        """Close panel with OK event"""
        self.on_apply_to_document(None)

    def make_gui(self):
        """Make UI"""
        # make panel
        settings_panel = self.make_panel_settings(self)
        buttons_panel = self.make_buttons_panel(self)

        plot_panel = self.make_plot_panel(self)

        extraction_panel = self.make_spectrum_panel(self)

        # pack element
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(settings_panel, 1, wx.EXPAND, 10)
        sizer.Add(extraction_panel, 0, wx.EXPAND, 10)
        sizer.Add(buttons_panel, 0, wx.EXPAND, 10)

        main_sizer = wx.BoxSizer()
        main_sizer.Add(sizer, 0, wx.EXPAND, 10)
        main_sizer.Add(plot_panel, 1, wx.EXPAND, 10)

        # fit layout
        main_sizer.Fit(self)
        self.SetSizer(main_sizer)

    # noinspection DuplicatedCode
    def make_panel_settings(self, split_panel):
        """Make settings panel"""
        panel = wx.Panel(split_panel, -1, name="settings")

        acquisition_label = wx.StaticText(panel, wx.ID_ANY, "Acquisition method:")
        self.origami_method_choice = wx.Choice(panel, -1, choices=CONFIG.origami_method_choices, size=(-1, -1))
        self.origami_method_choice.SetStringSelection(self.user_settings["method"])
        self.origami_method_choice.Bind(wx.EVT_CHOICE, self.on_apply)
        self.origami_method_choice.Bind(wx.EVT_CHOICE, self.on_toggle_controls)

        spv_label = wx.StaticText(panel, wx.ID_ANY, "Scans per voltage:")
        self.origami_scansPerVoltage_value = wx.TextCtrl(panel, -1, "", size=(-1, -1), validator=Validator("intPos"))
        self.origami_scansPerVoltage_value.SetValue(str(self.user_settings["scans_per_voltage"]))
        self.origami_scansPerVoltage_value.Bind(wx.EVT_TEXT, self.on_apply)

        scan_label = wx.StaticText(panel, wx.ID_ANY, "First scan:")
        self.origami_start_scan_value = wx.TextCtrl(panel, -1, "", size=(-1, -1), validator=Validator("intPos"))
        self.origami_start_scan_value.SetValue(str(self.user_settings["start_scan"]))
        self.origami_start_scan_value.Bind(wx.EVT_TEXT, self.on_apply)

        start_voltage_label = wx.StaticText(panel, wx.ID_ANY, "First voltage:")
        self.origami_start_voltage_value = wx.TextCtrl(panel, -1, "", size=(-1, -1), validator=Validator("floatPos"))
        self.origami_start_voltage_value.SetValue(str(self.user_settings["start_voltage"]))
        self.origami_start_voltage_value.Bind(wx.EVT_TEXT, self.on_apply)

        end_voltage_label = wx.StaticText(panel, wx.ID_ANY, "Final voltage:")
        self.origami_end_voltage_value = wx.TextCtrl(panel, -1, "", size=(-1, -1), validator=Validator("floatPos"))
        self.origami_end_voltage_value.SetValue(str(self.user_settings["end_voltage"]))
        self.origami_end_voltage_value.Bind(wx.EVT_TEXT, self.on_apply)

        step_voltage_label = wx.StaticText(panel, wx.ID_ANY, "Voltage step:")
        self.origami_step_voltage_value = wx.TextCtrl(panel, -1, "", size=(-1, -1), validator=Validator("floatPos"))
        self.origami_step_voltage_value.SetValue(str(self.user_settings["step_voltage"]))
        self.origami_step_voltage_value.Bind(wx.EVT_TEXT, self.on_apply)

        boltzmann_label = wx.StaticText(panel, wx.ID_ANY, "Boltzmann offset:")
        self.origami_boltzmann_offset_value = wx.TextCtrl(panel, -1, "", size=(-1, -1), validator=Validator("floatPos"))
        self.origami_boltzmann_offset_value.SetValue(str(self.user_settings["boltzmann_offset"]))
        self.origami_boltzmann_offset_value.Bind(wx.EVT_TEXT, self.on_apply)

        exponential_percentage_label = wx.StaticText(panel, wx.ID_ANY, "Exponential percentage:")
        self.origami_exponential_percentage_value = wx.TextCtrl(
            panel, -1, "", size=(-1, -1), validator=Validator("floatPos")
        )
        self.origami_exponential_percentage_value.SetValue(str(self.user_settings["exponential_percentage"]))
        self.origami_exponential_percentage_value.Bind(wx.EVT_TEXT, self.on_apply)

        exponential_increment_label = wx.StaticText(panel, wx.ID_ANY, "Exponential increment:")
        self.origami_exponential_increment_value = wx.TextCtrl(
            panel, -1, "", size=(-1, -1), validator=Validator("floatPos")
        )
        self.origami_exponential_increment_value.SetValue(str(self.user_settings["exponential_increment"]))
        self.origami_exponential_increment_value.Bind(wx.EVT_TEXT, self.on_apply)

        import_label = wx.StaticText(panel, wx.ID_ANY, "Import list:")
        self.origami_load_list_btn = wx.Button(panel, wx.ID_ANY, "...", size=(-1, -1))
        self.origami_load_list_btn.Bind(wx.EVT_BUTTON, self.on_load_origami_list)

        self.origami_calculate_btn = wx.Button(panel, wx.ID_OK, "Calculate", size=(-1, -1))
        self.origami_calculate_btn.Bind(wx.EVT_BUTTON, self.on_plot)

        btn_grid = wx.GridBagSizer(2, 2)
        btn_grid.Add(self.origami_calculate_btn, (0, 0), flag=wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL)

        horizontal_line = wx.StaticLine(panel, -1, style=wx.LI_HORIZONTAL)

        # pack elements
        grid = wx.GridBagSizer(2, 2)
        n = 0
        grid.Add(acquisition_label, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.origami_method_choice, (n, 1), flag=wx.EXPAND)
        n += 1
        grid.Add(spv_label, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.origami_scansPerVoltage_value, (n, 1), flag=wx.EXPAND)
        n += 1
        grid.Add(scan_label, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.origami_start_scan_value, (n, 1), flag=wx.EXPAND)
        n += 1
        grid.Add(start_voltage_label, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.origami_start_voltage_value, (n, 1), flag=wx.EXPAND)
        n += 1
        grid.Add(end_voltage_label, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.origami_end_voltage_value, (n, 1), flag=wx.EXPAND)
        n += 1
        grid.Add(step_voltage_label, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.origami_step_voltage_value, (n, 1), flag=wx.EXPAND)
        n += 1
        grid.Add(boltzmann_label, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.origami_boltzmann_offset_value, (n, 1), flag=wx.EXPAND)
        n += 1
        grid.Add(exponential_percentage_label, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.origami_exponential_percentage_value, (n, 1), flag=wx.EXPAND)
        n += 1
        grid.Add(exponential_increment_label, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.origami_exponential_increment_value, (n, 1), flag=wx.EXPAND)
        n += 1
        grid.Add(import_label, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.origami_load_list_btn, (n, 1), flag=wx.EXPAND)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(grid, 0, wx.ALIGN_CENTER_HORIZONTAL, 10)
        main_sizer.Add(btn_grid, 0, wx.ALIGN_CENTER_HORIZONTAL, 10)
        main_sizer.Add(horizontal_line, 0, wx.EXPAND, 10)

        # fit layout
        main_sizer.Fit(panel)
        panel.SetSizerAndFit(main_sizer)

        return panel

    def make_buttons_panel(self, split_panel):
        """Make buttons panel"""
        panel = wx.Panel(split_panel, -1, name="settings")

        # pack elements
        grid = wx.GridBagSizer(2, 2)
        n = 0
        self.origami_apply_btn = wx.Button(panel, wx.ID_OK, "Apply", size=(-1, -1))
        self.origami_apply_btn.Bind(wx.EVT_BUTTON, self.on_apply_to_document)

        self.origami_cancel_btn = wx.Button(panel, wx.ID_OK, "Close", size=(-1, -1))
        self.origami_cancel_btn.Bind(wx.EVT_BUTTON, self.on_close)

        n += 1
        grid.Add(self.origami_apply_btn, (n, 0), flag=wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.origami_cancel_btn, (n, 1), flag=wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(grid, 0, wx.ALIGN_CENTER_HORIZONTAL, 10)

        # fit layout
        main_sizer.Fit(panel)
        panel.SetSizerAndFit(main_sizer)

        return panel

    def make_spectrum_panel(self, split_panel):
        """Make spectrum panel"""
        panel = wx.Panel(split_panel, -1, name="information")

        info_label = wx.StaticText(panel, wx.ID_ANY, "Information")
        self.info_value = wx.StaticText(panel, -1, "")
        self.info_value.SetLabel("")

        self.preprocess_check = wx.CheckBox(panel, -1, "Pre-process", (3, 3))
        self.preprocess_check.SetValue(CONFIG.origami_preprocess)
        self.preprocess_check.Bind(wx.EVT_CHECKBOX, self.on_toggle_controls)

        self.process_btn = wx.Button(panel, wx.ID_ANY, "Edit MS processing settings...", size=(-1, -1))
        self.process_btn.Bind(wx.EVT_BUTTON, self.on_open_process_ms_settings)

        horizontal_line = wx.StaticLine(panel, -1, style=wx.LI_HORIZONTAL)

        self.origami_extract_btn = wx.Button(
            panel, wx.ID_ANY, "Extract mass spectrum for each collision voltage", size=(-1, -1)
        )
        self.origami_extract_btn.Bind(wx.EVT_BUTTON, self.on_extract_spectra)

        # pack elements
        grid = wx.GridBagSizer(2, 2)
        n = 0
        grid.Add(info_label, (n, 0), wx.GBSpan(1, 2), flag=wx.ALIGN_CENTER)
        n += 1
        grid.Add(self.info_value, (n, 0), wx.GBSpan(6, 2), flag=wx.EXPAND)
        n += 6
        grid.Add(self.preprocess_check, (n, 0), flag=wx.EXPAND)
        grid.Add(self.process_btn, (n, 1), flag=wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        n += 1
        grid.Add(self.origami_extract_btn, (n, 0), wx.GBSpan(1, 2), flag=wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        n += 1
        grid.Add(horizontal_line, (n, 0), wx.GBSpan(1, 2), flag=wx.EXPAND)
        n += 1

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(grid, 0, wx.ALIGN_CENTER_HORIZONTAL, 10)

        # fit layout
        main_sizer.Fit(panel)
        panel.SetSizerAndFit(main_sizer)

        return panel

    # noinspection DuplicatedCode

    def make_plot_panel(self, split_panel):
        """Make plot panel"""
        figsize = (6, 4)

        self.view_cv = ViewSpectrum(
            split_panel, figsize, x_label="Scans", y_label="Collision Voltage (V)", axes_size=(0.15, 0.25, 0.8, 0.65)
        )

        return self.view_cv.panel

    def on_apply(self, _evt):
        """Update user settings"""
        self.user_settings["method"] = self.origami_method_choice.GetStringSelection()
        self.user_settings["start_scan"] = str2int(self.origami_start_scan_value.GetValue())
        self.user_settings["scans_per_voltage"] = str2int(self.origami_scansPerVoltage_value.GetValue())
        self.user_settings["start_voltage"] = str2num(self.origami_start_voltage_value.GetValue())
        self.user_settings["end_voltage"] = str2num(self.origami_end_voltage_value.GetValue())
        self.user_settings["step_voltage"] = str2num(self.origami_step_voltage_value.GetValue())
        self.user_settings["boltzmann_offset"] = str2num(self.origami_boltzmann_offset_value.GetValue())
        self.user_settings["exponential_percentage"] = str2num(self.origami_exponential_percentage_value.GetValue())
        self.user_settings["exponential_increment"] = str2num(self.origami_exponential_increment_value.GetValue())

        self.user_settings_changed = True

        self.on_update_info()

    def on_apply_to_document(self, _evt):
        """Apply settings to document"""
        # update settings
        self.on_update_info()

        start_end_cv_list = self.calculate_origami_parameters()
        document, n_scans = self.get_scans()
        if document is None:
            raise MessageError("Error", "Document does not exist")

        calculated_n_scans = start_end_cv_list[-1][1]
        if calculated_n_scans > n_scans:
            raise MessageError(
                "Incorrect input settings",
                f"Your current settings indicate there is {calculated_n_scans} scans in the dataset, whereas"
                + f" there is only {n_scans}.",
            )

        self.user_settings["start_scan_end_scan_cv_list"] = start_end_cv_list
        document.add_config("origami_ms", self.user_settings)
        self.user_settings_changed = False

        self.on_plot()

    def get_scans(self):
        """Retrieve the number of scans found in a dataset"""
        document = ENV.on_get_document(self.document_title)
        path = document.get_file_path("main")
        if not os.path.exists(path):
            msg = (
                "The path to the raw file stored in the document no longer exist - please locate the directory and "
                " try again."
            )
            dlg = DialogBox(title="Error", msg=msg, kind="Question")
            if dlg == wx.ID_NO:
                return None, None

            path = self.data_handling.on_get_directory_path("Choose a Waters (.raw) directory")
            if path is None:
                return None, None
            document.add_file_path("main", path)

        info = self.data_handling.get_waters_info(path)
        n_scans = info["n_scans"]

        return document, n_scans

    def on_update_info(self):
        """Update processing information"""
        try:
            start_end_cv_list = self.calculate_origami_parameters()
        except (TypeError, IndexError, ValueError):
            self.info_value.SetLabel("")
            return

        if len(start_end_cv_list) == 0:
            self.info_value.SetLabel("")
            return

        # document = ENV.on_get_document(self.document_title)
        # reader = self.data_handling._get_waters_api_reader(document)
        # mz_x = reader.mz_x
        # # mz_x, mz_spacing = self.data_handling._get_waters_api_spacing(reader)
        # n_spectra = len(start_end_cv_list)
        # n_bins = len(mz_x)
        #
        # first_scan = start_end_cv_list[0][0]
        # last_scan = start_end_cv_list[-1][1]
        # approx_ram = (n_spectra * n_bins * 8) / (1024 ** 2)
        # info = (
        #     f"\n" + f"Number of iterations: {n_spectra}\n" + f"First scan {first_scan} | Last scan: {last_scan}\n"
        #     f"Number of points in each spectrum: {n_bins}\n"
        #     # + f"m/z spacing: {mz_spacing}\n"
        #     + f"Approx. amount of RAM: {approx_ram:.0f} MB"
        # )
        # self.info_value.SetLabel(info)

    def on_toggle_controls(self, evt):
        """Update controls"""
        CONFIG.origami_method = self.origami_method_choice.GetStringSelection()
        if CONFIG.origami_method == "Linear":
            enable_list = [
                self.origami_start_scan_value,
                self.origami_start_voltage_value,
                self.origami_end_voltage_value,
                self.origami_step_voltage_value,
                self.origami_scansPerVoltage_value,
            ]
            disable_list = [
                self.origami_boltzmann_offset_value,
                self.origami_exponential_increment_value,
                self.origami_exponential_percentage_value,
                self.origami_load_list_btn,
            ]
        elif CONFIG.origami_method == "Exponential":
            enable_list = [
                self.origami_start_scan_value,
                self.origami_start_voltage_value,
                self.origami_end_voltage_value,
                self.origami_step_voltage_value,
                self.origami_scansPerVoltage_value,
                self.origami_exponential_increment_value,
                self.origami_exponential_percentage_value,
            ]
            disable_list = [self.origami_boltzmann_offset_value, self.origami_load_list_btn]
        elif CONFIG.origami_method == "Boltzmann":
            enable_list = [
                self.origami_start_scan_value,
                self.origami_start_voltage_value,
                self.origami_end_voltage_value,
                self.origami_step_voltage_value,
                self.origami_scansPerVoltage_value,
                self.origami_boltzmann_offset_value,
            ]
            disable_list = [
                self.origami_exponential_increment_value,
                self.origami_exponential_percentage_value,
                self.origami_load_list_btn,
            ]
        elif CONFIG.origami_method == "User-defined":
            disable_list = [
                self.origami_start_voltage_value,
                self.origami_end_voltage_value,
                self.origami_step_voltage_value,
                self.origami_exponential_increment_value,
                self.origami_exponential_percentage_value,
                self.origami_scansPerVoltage_value,
                self.origami_boltzmann_offset_value,
            ]
            enable_list = [self.origami_load_list_btn, self.origami_start_scan_value]
        else:
            disable_list = [
                self.origami_start_scan_value,
                self.origami_start_voltage_value,
                self.origami_end_voltage_value,
                self.origami_step_voltage_value,
                self.origami_exponential_increment_value,
                self.origami_exponential_percentage_value,
                self.origami_scansPerVoltage_value,
                self.origami_boltzmann_offset_value,
                self.origami_load_list_btn,
            ]
            enable_list = []

        # iterate
        for item in enable_list:
            item.Enable()
        for item in disable_list:
            item.Disable()

        CONFIG.origami_preprocess = self.preprocess_check.GetValue()
        self.process_btn.Enable(enable=CONFIG.origami_preprocess)

        if evt is not None:
            evt.Skip()

    def on_open_process_ms_settings(self, _evt):
        """Open MS parameters window"""
        self.document_tree.on_open_process_ms_settings(disable_plot=True, disable_process=True)

    @staticmethod
    def _load_origami_list(path):
        """Load ORIGAMI-MS CV/SPV list"""
        origami_list = np.genfromtxt(path, delimiter=",", skip_header=True)
        return origami_list

    def on_load_origami_list(self, _evt):
        """Load a csv file with CV/SPV values for the List/User-defined method"""
        dlg = wx.FileDialog(self, "Choose a text file:", wildcard="*.csv", style=wx.FD_DEFAULT_STYLE | wx.FD_CHANGE_DIR)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            origami_list = self._load_origami_list(path)
            self.user_settings["start_scan_end_scan_cv_list"] = origami_list

        dlg.Destroy()

    def on_plot(self, _evt=None):
        """Update plot with ORIGAMI-MS parameters"""
        start_end_cv_list = self.calculate_origami_parameters()
        scans, voltages = pr_origami.generate_extraction_windows(start_end_cv_list)

        self.view_cv.plot(scans, voltages)

    def on_extract_spectra(self, _evt):
        """Submit spectra extraction"""
        from origami.gui_elements.dialog_batch_data_extract import DialogBatchDataExtract
        from origami.utils.converters import convert_scans_to_mins

        # get extraction parameters
        start_end_cv_list = self.calculate_origami_parameters()

        document = ENV.on_get_document(self.document_title)
        scan_time = document.parameters.get("scan_time", None)
        if scan_time is None:
            raise ValueError("Cannot extract mass spectral data")

        # generate list of items to be inserted into the table
        item_list = []
        for start_scan, end_scan, cv in start_end_cv_list:
            rt_start, rt_end = convert_scans_to_mins([start_scan, end_scan], scan_time)
            item_list.append(
                [DocumentGroups.MS, f"CV_{cv}_RT_{rt_start:.2f}-{rt_end:.2f}", dict(rt_start=rt_start, rt_end=rt_end)]
            )

        dlg = DialogBatchDataExtract(
            self.parent, item_list, document_tree=self.document_tree, document_title=self.document_title
        )
        dlg.ShowModal()

    def calculate_origami_parameters(self):
        """Calculate ORIGAMI-MS parameters"""
        method = self.user_settings["method"]

        if method not in ["Linear", "Exponential", "Boltzmann", "User-defined"]:
            raise ValueError("Could not identify method")

        start_end_cv_list, _, _ = pr_origami.calculate_origami_ms(**self.user_settings)

        return start_end_cv_list


def _main():

    app = wx.App()
    ex = DialogOrigamiMsSettings(None, None, debug=True)

    ex.Show()
    app.MainLoop()


if __name__ == "__main__":
    _main()