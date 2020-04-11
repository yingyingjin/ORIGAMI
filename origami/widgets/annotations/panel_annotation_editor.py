"""Annotations editor"""
# Standard library imports
import copy
import logging

# Third-party imports
import wx
import numpy as np
from pubsub import pub

# Local imports
import origami.processing.utils as pr_utils
from origami.styles import ListCtrl
from origami.styles import validator
from origami.styles import make_checkbox
from origami.styles import make_menu_item
from origami.utils.check import check_value_order
from origami.utils.color import round_rgb
from origami.utils.color import get_font_color
from origami.utils.color import get_all_color_types
from origami.utils.color import convert_rgb_1_to_255
from origami.utils.color import convert_rgb_255_to_1
from origami.utils.labels import sanitize_string
from origami.utils.screen import calculate_window_size
from origami.utils.converters import rounder
from origami.utils.converters import str2int
from origami.utils.converters import str2num
from origami.utils.exceptions import MessageError
from origami.objects.annotations import check_annotation_input
from origami.gui_elements.misc_dialogs import DialogSimpleAsk
from origami.visuals.mpl.plot_spectrum import PlotSpectrum

# Module globals
logger = logging.getLogger(__name__)


class PanelAnnotationEditorUI(wx.MiniFrame):
    """UI component of the Annotation Editor"""

    TABLE_COLUMNS = {
        "check": 0,
        "name": 1,
        "label": 2,
        "label_position": 3,
        "arrow": 4,
        "arrow_show": 4,
        "charge": 5,
        "patch": 6,
        "patch_show": 6,
        "patch_position": 7,
        "patch_color": 8,
        "color": 8,
    }

    TABLE_PROPERTIES = {
        0: {"name": "", "tag": "check", "type": "bool", "width": 20, "show": True},
        1: {"name": "name", "tag": "name", "type": "str", "width": 70, "show": True},
        2: {"name": "label", "tag": "label", "type": "str", "width": 100, "show": True},
        3: {"name": "label position", "tag": "label_position", "type": "list", "width": 100, "show": True},
        4: {"name": "arrow", "tag": "arrow", "type": "str", "width": 45, "show": True},
        5: {"name": "z", "tag": "charge", "type": "int", "width": 30, "show": True},
        6: {"name": "patch", "tag": "patch", "type": "str", "width": 45, "show": True},
        7: {"name": "patch position", "tag": "patch_position", "type": "list", "width": 100, "show": True},
        8: {"name": "patch color", "tag": "color", "type": "color", "width": 75, "show": True},
    }

    # pre-allocate ui controls
    peaklist = None
    name_value = None
    label_value = None
    position_x = None
    position_y = None
    label_position_x = None
    label_position_y = None
    charge_value = None
    label_color_btn = None
    add_arrow_to_peak = None
    patch_min_x = None
    patch_min_y = None
    patch_width = None
    patch_height = None
    patch_color_btn = None
    add_patch_to_peak = None
    highlight_on_selection = None
    zoom_on_selection = None
    auto_add_to_table = None
    zoom_window_size = None

    # buttons
    add_btn = None
    remove_btn = None
    show_btn = None
    cancel_btn = None
    action_btn = None

    # plot
    plot_view = None
    plot_panel = None
    plot_window = None

    # menu
    _menu_show_all_check = None
    _menu_pin_label_to_intensity_check = None
    _menu_autofix_label_position_check = None

    # misc
    _settings_panel_size = None
    main_sizer = None
    _plot_types_1d = ["mass_spectrum", "chromatogram", "mobilogram"]
    _plot_types_2d = ["heatmap"]
    _plot_types_misc = ["annotated"]
    PLOT_TYPES = _plot_types_1d + _plot_types_2d + _plot_types_misc

    def __init__(self, parent, config, icons, plot_type):
        wx.MiniFrame.__init__(
            self, parent, -1, "Annotation...", size=(-1, -1), style=wx.DEFAULT_FRAME_STYLE | wx.RESIZE_BORDER
        )
        self.parent = parent
        self.config = config
        self.icons = icons
        self.plot_type = plot_type

        # presets
        self._menu_show_all = True
        self._menu_pin_label_to_intensity = True
        self._menu_autofix_label_position = False
        self._auto_add_to_table = True
        self._allow_data_check = True
        self.item_loading_lock = False

        # view
        self._display_size = self.parent.GetSize()
        self._display_resolution = wx.ScreenDC().GetPPI()
        self._window_size = calculate_window_size(self._display_size, 0.9)

        # perform sanity check
        self.sanity_check()
        self.make_gui()

    def sanity_check(self):
        """Perform self-check"""
        if self.plot_type not in self.PLOT_TYPES:
            raise ValueError(f"`{self.plot_type}` is not yet supported")

    # noinspection DuplicatedCode
    def menu_column_right_click(self, _):
        """Right-click event on the table"""
        menu = self.get_menu_column_right_click()

        self.PopupMenu(menu)
        menu.Destroy()
        self.SetFocus()

    # noinspection DuplicatedCode
    def get_menu_column_right_click(self):
        """Get right-click menu"""
        menu = wx.Menu()
        menu_table_toggle_name = menu.AppendCheckItem(wx.ID_ANY, "Show/hide name column")
        menu_table_toggle_name.Check(self.TABLE_PROPERTIES[self.TABLE_COLUMNS["name"]]["show"])
        menu_table_toggle_label = menu.AppendCheckItem(wx.ID_ANY, "Show/hide label column")
        menu_table_toggle_label.Check(self.TABLE_PROPERTIES[self.TABLE_COLUMNS["label"]]["show"])
        menu_table_toggle_label_pos = menu.AppendCheckItem(wx.ID_ANY, "Show/hide label position column")
        menu_table_toggle_label_pos.Check(self.TABLE_PROPERTIES[self.TABLE_COLUMNS["label_position"]]["show"])
        menu_table_toggle_arrow = menu.AppendCheckItem(wx.ID_ANY, "Show/hide arrow column")
        menu_table_toggle_arrow.Check(self.TABLE_PROPERTIES[self.TABLE_COLUMNS["arrow"]]["show"])
        menu_table_toggle_charge = menu.AppendCheckItem(wx.ID_ANY, "Show/hide charge column")
        menu_table_toggle_charge.Check(self.TABLE_PROPERTIES[self.TABLE_COLUMNS["charge"]]["show"])
        menu_table_toggle_patch = menu.AppendCheckItem(wx.ID_ANY, "Show/hide patch column")
        menu_table_toggle_patch.Check(self.TABLE_PROPERTIES[self.TABLE_COLUMNS["patch_show"]]["show"])
        menu_table_toggle_patch_pos = menu.AppendCheckItem(wx.ID_ANY, "Show/hide patch position column")
        menu_table_toggle_patch_pos.Check(self.TABLE_PROPERTIES[self.TABLE_COLUMNS["patch_position"]]["show"])
        menu_table_toggle_patch_color = menu.AppendCheckItem(wx.ID_ANY, "Show/hide patch color column")
        menu_table_toggle_patch_color.Check(self.TABLE_PROPERTIES[self.TABLE_COLUMNS["patch_color"]]["show"])
        menu.AppendSeparator()
        menu_table_toggle_all = menu.Append(wx.ID_ANY, "Show all columns")

        # bind
        self.Bind(wx.EVT_MENU, self.on_update_peaklist_table, menu_table_toggle_name)
        self.Bind(wx.EVT_MENU, self.on_update_peaklist_table, menu_table_toggle_label)
        self.Bind(wx.EVT_MENU, self.on_update_peaklist_table, menu_table_toggle_label_pos)
        self.Bind(wx.EVT_MENU, self.on_update_peaklist_table, menu_table_toggle_arrow)
        self.Bind(wx.EVT_MENU, self.on_update_peaklist_table, menu_table_toggle_charge)
        self.Bind(wx.EVT_MENU, self.on_update_peaklist_table, menu_table_toggle_patch)
        self.Bind(wx.EVT_MENU, self.on_update_peaklist_table, menu_table_toggle_patch_pos)
        self.Bind(wx.EVT_MENU, self.on_update_peaklist_table, menu_table_toggle_patch_color)
        self.Bind(wx.EVT_MENU, self.on_update_peaklist_table, menu_table_toggle_all)
        return menu

    def on_update_peaklist_table(self, evt):
        """Update peaklist"""
        name = evt.GetEventObject().FindItemById(evt.GetId()).GetLabel()

        name_dict = {
            "Show/hide name column": self.TABLE_COLUMNS["name"],
            "Show/hide label column": self.TABLE_COLUMNS["label"],
            "Show/hide label position column": self.TABLE_COLUMNS["label_position"],
            "Show/hide arrow column": self.TABLE_COLUMNS["arrow"],
            "Show/hide charge column": self.TABLE_COLUMNS["charge"],
            "Show/hide patch column": self.TABLE_COLUMNS["patch"],
            "Show/hide patch position column": self.TABLE_COLUMNS["patch_position"],
            "Show/hide patch color column": self.TABLE_COLUMNS["patch_color"],
            "Restore all columns": -1,
        }

        col_index = name_dict[name]
        if col_index >= 0:
            col_width_new = self.TABLE_PROPERTIES[col_index]["width"]
            col_width_now = self.peaklist.GetColumnWidth(col_index)
            if col_width_now > 0:
                col_width_new = 0

            self.TABLE_PROPERTIES[col_index]["show"] = True if col_width_new > 0 else False
            self.peaklist.SetColumnWidth(col_index, col_width_new)
        else:
            for col_index in self.TABLE_PROPERTIES:
                self.TABLE_PROPERTIES[col_index]["show"] = True
                if self.peaklist.GetColumnWidth(col_index) == 0:
                    self.peaklist.SetColumnWidth(col_index, self.TABLE_PROPERTIES[col_index]["width"])

    def make_gui(self):
        """Make user-interface"""

        # make panel
        settings_panel = self.make_settings_panel(self)
        self._settings_panel_size = settings_panel.GetSize()

        plot_panel = self.make_plot_panel(self)

        # pack elements
        self.main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.main_sizer.Add(settings_panel, 0, wx.EXPAND, 0)
        self.main_sizer.Add(plot_panel, 1, wx.EXPAND, 0)

        # fit layout
        self.main_sizer.Fit(self)
        self.SetSizer(self.main_sizer)
        self.SetSize(self._window_size)
        self.Layout()
        self.Show(True)
        self.CentreOnScreen()
        self.SetFocus()

    def make_peaklist(self, panel):
        """Make table"""

        peaklist = ListCtrl(panel, style=wx.LC_REPORT | wx.LC_VRULES, column_info=self.TABLE_PROPERTIES)
        for order, item in self.TABLE_PROPERTIES.items():
            name = item["name"]
            width = 0
            if item["show"]:
                width = item["width"]
            peaklist.InsertColumn(order, name, width=width, format=wx.LIST_FORMAT_CENTER)

        max_size = (int(self._window_size[0] * 0.3), -1)
        peaklist.SetMaxClientSize(max_size)

        return peaklist

    def make_plot_panel(self, split_panel):
        """Make plot panel"""

        pixel_size = [(self._window_size[0] - self._settings_panel_size[0]), (self._window_size[1] - 50)]
        figsize = [pixel_size[0] / self._display_resolution[0], pixel_size[1] / self._display_resolution[1]]

        panel = wx.Panel(split_panel, -1, size=(-1, -1), name="plot")
        if self.plot_type in self._plot_types_1d:
            if self.plot_type == "mass_spectrum":
                from origami.gui_elements.views.view_spectrum import ViewMassSpectrum

                self.plot_view = ViewMassSpectrum(panel, figsize, self.config)
            elif self.plot_type == "chromatogram":
                from origami.gui_elements.views.view_spectrum import ViewChromatogram

                self.plot_view = ViewChromatogram(panel, figsize, self.config)
            elif self.plot_type == "mobilogram":
                from origami.gui_elements.views.view_spectrum import ViewMobilogram

                self.plot_view = ViewMobilogram(panel, figsize, self.config)

            self.plot_panel = self.plot_view.panel
            self.plot_window = self.plot_view.figure
        else:
            self.plot_panel = wx.Panel(panel, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
            self.plot_window = PlotSpectrum(self.plot_panel, figsize=figsize, config=self.config)

        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(self.plot_window, 1, wx.EXPAND)
        box.Fit(self.plot_panel)
        self.plot_panel.SetSizer(box)
        self.plot_panel.Layout()

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(self.plot_panel, 1, wx.EXPAND, 2)
        # fit layout
        panel.SetSizer(main_sizer)
        main_sizer.Fit(panel)

        return panel

    # noinspection DuplicatedCode
    def make_settings_panel(self, split_panel):
        """Make settings panel"""

        panel = wx.Panel(split_panel, -1, size=(-1, -1), name="settings")

        # make peaklist
        self.peaklist = self.make_peaklist(panel)

        name_value = wx.StaticText(panel, -1, "name:")
        self.name_value = wx.TextCtrl(panel, -1, "", style=wx.TE_RICH2)
        self.name_value.Disable()

        label_value = wx.StaticText(panel, -1, "annotation:")
        self.label_value = wx.TextCtrl(panel, -1, "", style=wx.TE_RICH2 | wx.TE_MULTILINE)
        self.label_value.SetToolTip(wx.ToolTip("Label associated with the marked region in the plot area"))

        position_x = wx.StaticText(panel, -1, "marker position (x):")
        self.position_x = wx.TextCtrl(panel, -1, "", validator=validator("float"))
        self.position_x.SetBackgroundColour((255, 230, 239))

        position_y = wx.StaticText(panel, -1, "marker position (y):")
        self.position_y = wx.TextCtrl(panel, -1, "", validator=validator("float"))
        self.position_y.SetBackgroundColour((255, 230, 239))

        label_position_x = wx.StaticText(panel, -1, "label position (x):")
        self.label_position_x = wx.TextCtrl(panel, -1, "", validator=validator("float"))
        self.label_position_x.SetBackgroundColour((255, 230, 239))

        label_position_y = wx.StaticText(panel, -1, "label position (y):")
        self.label_position_y = wx.TextCtrl(panel, -1, "", validator=validator("float"))
        self.label_position_y.SetBackgroundColour((255, 230, 239))

        charge_value = wx.StaticText(panel, -1, "charge:")
        self.charge_value = wx.TextCtrl(panel, -1, "", validator=validator("int"))

        label_color = wx.StaticText(panel, -1, "label color:")
        self.label_color_btn = wx.Button(panel, wx.ID_ANY, "", size=wx.Size(26, 26), name="color.label")
        self.label_color_btn.SetBackgroundColour([0, 0, 0])

        add_arrow_to_peak = wx.StaticText(panel, -1, "show arrow:")
        self.add_arrow_to_peak = make_checkbox(panel, "")
        self.add_arrow_to_peak.SetValue(False)

        patch_general = wx.StaticText(panel, -1, "patch:")

        patch_min_x = wx.StaticText(panel, -1, "patch position (x):")
        self.patch_min_x = wx.TextCtrl(panel, -1, "", validator=validator("float"))
        self.patch_min_x.SetBackgroundColour((255, 230, 239))

        patch_min_y = wx.StaticText(panel, -1, "patch position (y):")
        self.patch_min_y = wx.TextCtrl(panel, -1, "", validator=validator("float"))
        self.patch_min_y.SetBackgroundColour((255, 230, 239))

        patch_width = wx.StaticText(panel, -1, "width:")
        self.patch_width = wx.TextCtrl(panel, -1, "", validator=validator("float"))

        patch_height = wx.StaticText(panel, -1, "height:")
        self.patch_height = wx.TextCtrl(panel, -1, "", validator=validator("float"))

        patch_color = wx.StaticText(panel, -1, "patch color:")
        self.patch_color_btn = wx.Button(panel, wx.ID_ANY, "", size=wx.Size(26, 26), name="color.patch")
        self.patch_color_btn.SetBackgroundColour(convert_rgb_1_to_255(self.config.interactive_ms_annotations_color))

        add_patch_to_peak = wx.StaticText(panel, -1, "show patch:")
        self.add_patch_to_peak = make_checkbox(panel, "")
        self.add_patch_to_peak.SetValue(False)

        horizontal_line_1 = wx.StaticLine(panel, -1, style=wx.LI_HORIZONTAL)
        horizontal_line_2 = wx.StaticLine(panel, -1, style=wx.LI_HORIZONTAL)
        horizontal_line_3 = wx.StaticLine(panel, -1, style=wx.LI_HORIZONTAL)

        # make buttons
        self.add_btn = wx.Button(panel, wx.ID_OK, "Add", size=(-1, 22))
        self.remove_btn = wx.Button(panel, wx.ID_OK, "Remove", size=(-1, 22))
        self.cancel_btn = wx.Button(panel, wx.ID_OK, "Cancel", size=(-1, 22))
        self.show_btn = wx.Button(panel, wx.ID_OK, "Show ▼", size=(-1, 22))
        self.action_btn = wx.Button(panel, wx.ID_OK, "Action ▼", size=(-1, 22))

        self.highlight_on_selection = make_checkbox(panel, "highlight")
        self.highlight_on_selection.SetValue(True)

        self.zoom_on_selection = make_checkbox(panel, "zoom-in")
        self.zoom_on_selection.SetValue(False)

        window_size = wx.StaticText(panel, wx.ID_ANY, "window size:")
        self.zoom_window_size = wx.SpinCtrlDouble(
            panel, -1, value=str(5), min=0.0001, max=250, initial=5, inc=25, size=(90, -1)
        )

        self.auto_add_to_table = make_checkbox(panel, "automatically add to table")
        self.auto_add_to_table.SetValue(self._auto_add_to_table)

        # button grid
        btn_grid = wx.GridBagSizer(5, 5)
        y = 0
        btn_grid.Add(self.add_btn, (y, 0), flag=wx.ALIGN_CENTER)
        btn_grid.Add(self.remove_btn, (y, 1), flag=wx.ALIGN_CENTER)
        btn_grid.Add(self.show_btn, (y, 2), flag=wx.ALIGN_CENTER)
        btn_grid.Add(self.action_btn, (y, 3), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT)
        btn_grid.Add(self.cancel_btn, (y, 4), flag=wx.ALIGN_CENTER)

        # pack elements
        grid = wx.GridBagSizer(5, 5)
        y = 0
        grid.Add(name_value, (y, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.name_value, (y, 1), wx.GBSpan(1, 4), flag=wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        y += 1
        grid.Add(label_value, (y, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.label_value, (y, 1), wx.GBSpan(4, 4), flag=wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        y += 4
        grid.Add(position_x, (y, 1), flag=wx.ALIGN_CENTER)
        grid.Add(position_y, (y, 2), flag=wx.ALIGN_CENTER)
        y += 1
        grid.Add(self.position_x, (y, 1), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.position_y, (y, 2), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        y += 1
        grid.Add(label_position_x, (y, 1), flag=wx.ALIGN_CENTER)
        grid.Add(label_position_y, (y, 2), flag=wx.ALIGN_CENTER)
        y += 1
        grid.Add(self.label_position_x, (y, 1), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.label_position_y, (y, 2), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        y += 1
        grid.Add(charge_value, (y, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.charge_value, (y, 1), wx.GBSpan(1, 1), flag=wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        y += 1
        grid.Add(label_color, (y, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.label_color_btn, (y, 1), wx.GBSpan(1, 1), flag=wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        y += 1
        grid.Add(add_arrow_to_peak, (y, 0), flag=wx.ALIGN_CENTER)
        grid.Add(self.add_arrow_to_peak, (y, 1), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT)
        y += 1
        grid.Add(horizontal_line_1, (y, 0), wx.GBSpan(1, 5), flag=wx.EXPAND)
        y += 1
        grid.Add(patch_min_x, (y, 1), flag=wx.ALIGN_CENTER)
        grid.Add(patch_min_y, (y, 2), flag=wx.ALIGN_CENTER)
        grid.Add(patch_width, (y, 3), flag=wx.ALIGN_CENTER)
        grid.Add(patch_height, (y, 4), flag=wx.ALIGN_CENTER)
        y += 1
        grid.Add(patch_general, (y, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.patch_min_x, (y, 1), flag=wx.ALIGN_CENTER)
        grid.Add(self.patch_min_y, (y, 2), flag=wx.ALIGN_CENTER)
        grid.Add(self.patch_width, (y, 3), flag=wx.ALIGN_CENTER)
        grid.Add(self.patch_height, (y, 4), flag=wx.ALIGN_CENTER)
        y += 1
        grid.Add(patch_color, (y, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.patch_color_btn, (y, 1), wx.GBSpan(1, 1), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT)
        y += 1
        grid.Add(add_patch_to_peak, (y, 0), flag=wx.ALIGN_CENTER)
        grid.Add(self.add_patch_to_peak, (y, 1), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT)
        y += 1
        grid.Add(horizontal_line_2, (y, 0), wx.GBSpan(1, 5), flag=wx.EXPAND)
        y += 1
        grid.Add(btn_grid, (y, 0), wx.GBSpan(1, 5), flag=wx.ALIGN_CENTER)
        y += 1
        grid.Add(horizontal_line_3, (y, 0), wx.GBSpan(1, 5), flag=wx.EXPAND)
        y += 1
        grid.Add(self.highlight_on_selection, (y, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT)
        grid.Add(self.zoom_on_selection, (y, 1), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT)
        grid.Add(window_size, (y, 2), flag=wx.ALIGN_CENTER)
        grid.Add(self.zoom_window_size, (y, 3), flag=wx.ALIGN_CENTER)
        y += 1
        grid.Add(self.auto_add_to_table, (y, 0), (1, 2), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT)

        # setup growable column
        grid.AddGrowableCol(4)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(grid, 0, wx.EXPAND, 0)
        main_sizer.Add(self.peaklist, 1, wx.EXPAND, 2)

        # fit layout
        main_sizer.Fit(panel)
        panel.SetSizerAndFit(main_sizer)

        return panel

    def on_double_click_on_item(self, _):
        if self.peaklist.item_id not in [-1, None]:
            check = not self.peaklist.IsChecked(self.peaklist.item_id)
            self.peaklist.CheckItem(self.peaklist.item_id, check)


class PanelAnnotationEditor(PanelAnnotationEditorUI):
    """Simple GUI to view and annotate plots"""

    def __init__(self, parent, document_tree, config, icons, **kwargs):
        PanelAnnotationEditorUI.__init__(self, parent, config, icons, kwargs["plot_type"])

        # reference to other objects
        self.document_tree = document_tree
        self.panel_plot = document_tree.presenter.view.panelPlots
        self.data_processing = self.parent.presenter.data_processing
        self.data_handling = self.parent.presenter.data_handling

        # data
        self.query = kwargs["query"]
        self.document_title = kwargs["document_title"]
        self.dataset_type = kwargs["dataset_type"]
        self.dataset_name = kwargs["dataset_name"]
        self.annotations_obj = kwargs.pop("annotations")
        self.data = kwargs["data"]
        self.kwargs = kwargs

        # hard code few parameters
        self.config.annotation_patch_transparency = 0.2
        self.config.annotation_patch_width = 3

        # make gui items
        self.plot = self.plot_window

        # initialize correct view
        self.update_title()
        self.on_populate_table()
        self.on_toggle_controls(None)
        wx.CallAfter(self.on_setup_plot_on_startup)

        # bind
        self.bind_events()

    # noinspection DuplicatedCode
    def bind_events(self):
        """Bind events"""

        # add listeners
        pub.subscribe(self.add_annotation_from_mouse_evt, "editor.mark.annotation")
        pub.subscribe(self.edit_annotation_from_mouse_evt, "editor.edit.annotation")

        # bind buttons
        self.patch_color_btn.Bind(wx.EVT_BUTTON, self.on_assign_color)
        self.label_color_btn.Bind(wx.EVT_BUTTON, self.on_assign_color)
        self.add_btn.Bind(wx.EVT_BUTTON, self.on_add_annotation)
        self.remove_btn.Bind(wx.EVT_BUTTON, self.on_delete_annotation)
        self.cancel_btn.Bind(wx.EVT_BUTTON, self.on_close)
        self.show_btn.Bind(wx.EVT_BUTTON, self.on_menu_plot_tools)
        self.action_btn.Bind(wx.EVT_BUTTON, self.on_menu_action_tools)

        # bind checkboxes
        self.add_patch_to_peak.Bind(wx.EVT_CHECKBOX, self.on_add_annotation)
        self.auto_add_to_table.Bind(wx.EVT_CHECKBOX, self.on_apply)
        self.highlight_on_selection.Bind(wx.EVT_CHECKBOX, self.on_toggle_controls)

        # bind table
        self.peaklist.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_select_item)
        self.peaklist.Bind(wx.EVT_LEFT_DCLICK, self.on_double_click_on_item)
        self.peaklist.Bind(wx.EVT_LIST_COL_RIGHT_CLICK, self.menu_column_right_click)

        # window events
        self.Bind(wx.EVT_CONTEXT_MENU, self.on_right_click)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key_event)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        # wx.EVT_CLOSE(self, self.on_close)

    def _check_active(self, query):
        """Check whether the currently open editor should be closed"""
        return all([self.document_title == query[0], self.dataset_type == query[1], self.dataset_name == query[2]])

    def on_clear_table(self):
        """Clear annotation table"""
        self.peaklist.DeleteAllItems()
        self.on_clear_from_plot(None)

    def on_setup_plot_on_startup(self):
        """Setup plot on startup of the window"""
        if self.plot_type in self._plot_types_1d:
            self.on_plot_1d()
        elif self.plot_type == "annotated":
            self.on_plot_annotated()
            self._allow_data_check = False
        elif self.plot_type == "heatmap":
            self.on_plot_heatmap()
            self._allow_data_check = False

        self.plot_window.on_mark_annotation(True)
        self.on_show_on_plot(None)

    def edit_annotation_from_mouse_evt(self, annotation_obj):
        # update label position in the plot - must be carried out to update arrow
        self.on_add_label_to_plot(annotation_obj)

        # if item is already selected, make sure values in the GUI reflect any changes
        if self.name_value.GetValue() == annotation_obj.name:
            self.set_annotation_in_gui(None, annotation_obj)

        # if item is in the table, make sure to update the values
        in_table, item_id = self.check_for_duplicate(annotation_obj.name)

        if in_table:
            self.on_update_value_in_peaklist(
                item_id, ["label_position"], dict(label_position=annotation_obj.label_position)
            )

    def on_right_click(self, evt):
        # ensure that user clicked inside the plot area
        if hasattr(evt.EventObject, "figure"):

            menu = wx.Menu()
            save_figure_menu_item = make_menu_item(
                menu, id=wx.ID_ANY, text="Save figure as...", bitmap=self.icons.iconsLib["save16"]
            )
            menu.AppendItem(save_figure_menu_item)

            menu_action_copy_to_clipboard = make_menu_item(
                parent=menu, id=wx.ID_ANY, text="Copy plot to clipboard", bitmap=self.icons.iconsLib["filelist_16"]
            )
            menu.AppendItem(menu_action_copy_to_clipboard)
            menu.AppendSeparator()
            menu_plot_clear_labels = menu.Append(wx.ID_ANY, "Clear annotations")

            # bind events
            self.Bind(wx.EVT_MENU, self.on_save_figure, save_figure_menu_item)
            self.Bind(wx.EVT_MENU, self.on_copy_to_clipboard, menu_action_copy_to_clipboard)
            self.Bind(wx.EVT_MENU, self.on_clear_from_plot, menu_plot_clear_labels)

            self.PopupMenu(menu)
            menu.Destroy()
            self.SetFocus()

    def update_title(self):
        """Update widget title"""
        self.SetTitle(f"Annotating: {self.document_title} :: {self.dataset_type} :: {self.dataset_name}")

    def get_annotation_data(self):
        """Quickly retrieve annotations object"""
        return self.data_handling.get_annotations_data(self.query)

    def set_annotation_data(self):
        """Set annotations object"""
        raise NotImplementedError("Error")

    def on_key_event(self, evt):
        key_code = evt.GetKeyCode()

        if key_code == wx.WXK_ESCAPE:
            self.on_close(None)
        elif key_code == 127 and self.FindFocus() == self.peaklist:
            self.on_delete_item()
        evt.Skip()

    def on_close(self, _):
        """Destroy this frame."""

        # # reset state
        # try:
        #     self.plot.plot_remove_temporary(repaint=True)
        # except (AttributeError, TypeError):
        #     logger.warning("Failed to remove temporary marker")

        try:
            self.plot.on_mark_annotation(state=False)
        except AttributeError:
            logger.warning("Failed to unmark annotation state")

        # unsubscribe
        try:
            pub.unsubscribe(self.add_annotation_from_mouse_evt, "editor.mark.annotation")
            pub.unsubscribe(self.edit_annotation_from_mouse_evt, "editor.edit.annotation")
        except Exception as err:
            logger.warning(f"Failed to unsubscribe from `editor.mark.annotation`or `editor.edit.annotation`: {err}")

        self.document_tree._annotate_panel = None
        self.Destroy()

    def on_apply(self, _):
        self._auto_add_to_table = self.auto_add_to_table.GetValue()

    def on_toggle_controls(self, evt):
        """Toggle various items in the UI based on event triggers"""

        if not self.highlight_on_selection.GetValue():
            self.plot_window.plot_remove_temporary(True)

        if evt is not None:
            evt.Skip()

    def on_copy_annotations(self, _):
        rows = self.peaklist.GetItemCount()
        checked = []

        for row in range(rows):
            if self.peaklist.IsChecked(row):
                checked.append(row)

        if len(checked) == 0:
            print("Please check at least one annotation the table...")
            return

        annotations_obj = self.get_annotation_data()

        n_duplicates = DialogSimpleAsk(
            "How many times would you like to duplicate this annotations?", defaultValue="1", value_type="intPos"
        )
        n_duplicates = int(n_duplicates)
        for row in checked:
            __, annotation_obj = self.on_get_annotation_obj(row)

            for n_duplicate in range(1, n_duplicates + 1):
                annotation_obj_copy = copy.deepcopy(annotation_obj)
                annotation_obj_copy.name = annotation_obj_copy.name + f" ({n_duplicate})"
                annotations_obj.append_annotation(annotation_obj_copy)
                self.on_add_to_table(annotation_obj_copy)

        self.annotations_obj = annotations_obj
        self.document_tree.on_update_annotation(
            self.annotations_obj, self.document_title, self.dataset_type, self.dataset_name
        )

    def on_menu_action_tools(self, _):
        """Create action menu"""
        menu = wx.Menu()

        menu_action_customise = make_menu_item(
            parent=menu, text="Customise other settings...", bitmap=self.icons.iconsLib["settings16_2"], help_text=""
        )
        menu.Append(menu_action_customise)
        menu.AppendSeparator()
        self.Bind(wx.EVT_MENU, self.on_customise_parameters, menu_action_customise)

        menu_action_multiply = make_menu_item(
            parent=menu, text="Create (similar) copies of selected annotations", bitmap=None
        )
        menu.Append(menu_action_multiply)
        menu.AppendSeparator()
        self.Bind(wx.EVT_MENU, self.on_copy_annotations, menu_action_multiply)

        menu_action_edit_charge = make_menu_item(
            parent=menu, text="Set charge state (selected)", bitmap=self.icons.iconsLib["assign_charge_16"]
        )
        menu.Append(menu_action_edit_charge)
        self.Bind(wx.EVT_MENU, self.on_change_item_parameter, menu_action_edit_charge)

        if self._allow_data_check:
            menu_action_fix_label_intensity = make_menu_item(
                parent=menu, text="Fix intensity / label position (selected)"
            )
            menu.Append(menu_action_fix_label_intensity)
            self.Bind(wx.EVT_MENU, self.on_fix_intensity, menu_action_fix_label_intensity)

            menu_action_fix_patch_height = make_menu_item(
                parent=menu,
                text="Fix patch height (selected)",
                help_text="Pins the height of a patch to the maximum intensity at a particular position (x)",
            )
            menu.Append(menu_action_fix_patch_height)
            self.Bind(wx.EVT_MENU, self.on_fix_patch_height, menu_action_fix_patch_height)
            menu.AppendSeparator()

        menu_action_edit_text_color = make_menu_item(parent=menu, text="Set label color (selected)")
        menu.Append(menu_action_edit_text_color)
        self.Bind(wx.EVT_MENU, self.on_assign_color, menu_action_edit_text_color)

        menu_action_edit_patch_color = make_menu_item(parent=menu, text="Set patch color (selected)")
        menu.Append(menu_action_edit_patch_color)
        self.Bind(wx.EVT_MENU, self.on_assign_color, menu_action_edit_patch_color)

        arrow_submenu = wx.Menu()
        menu_action_edit_arrow_true = arrow_submenu.Append(wx.ID_ANY, "True")
        self.Bind(wx.EVT_MENU, self.on_assign_arrow, menu_action_edit_arrow_true)
        menu_action_edit_arrow_false = arrow_submenu.Append(wx.ID_ANY, "False")
        self.Bind(wx.EVT_MENU, self.on_assign_arrow, menu_action_edit_arrow_false)
        menu.AppendMenu(wx.ID_ANY, "Set `show arrow` to... (selected)", arrow_submenu)

        patch_submenu = wx.Menu()
        menu_action_edit_patch_true = patch_submenu.Append(wx.ID_ANY, "True")
        self.Bind(wx.EVT_MENU, self.on_assign_patch, menu_action_edit_patch_true)
        menu_action_edit_patch_false = patch_submenu.Append(wx.ID_ANY, "False")
        self.Bind(wx.EVT_MENU, self.on_assign_patch, menu_action_edit_patch_false)
        menu.AppendMenu(wx.ID_ANY, "Set `show patch` to... (selected)", patch_submenu)

        menu_action_delete = make_menu_item(parent=menu, text="Delete (selected)", bitmap=self.icons.iconsLib["bin16"])
        menu.AppendSeparator()
        menu.Append(menu_action_delete)
        self.Bind(wx.EVT_MENU, self.on_delete_items, menu_action_delete)

        self.PopupMenu(menu)
        menu.Destroy()
        self.SetFocus()

    def on_menu_plot_tools(self, _):
        menu = wx.Menu()
        self._menu_show_all_check = menu.AppendCheckItem(
            wx.ID_ANY,
            "Always show all annotation(s)",
            help="If checked, all annotations will be shown regardless of their checked status in the table",
        )
        self._menu_show_all_check.Check(self._menu_show_all)

        self._menu_pin_label_to_intensity_check = menu.AppendCheckItem(
            wx.ID_ANY, "Show labels at intensity value", help="If checked, labels will 'stick' to the intensity values"
        )
        self._menu_pin_label_to_intensity_check.Check(self._menu_pin_label_to_intensity)

        self._menu_autofix_label_position_check = menu.AppendCheckItem(
            wx.ID_ANY,
            "Auto-adjust positions to prevent overlap",
            help="If checked, labels will be repositioned to prevent overlap.",
        )
        self._menu_autofix_label_position_check.Check(self._menu_autofix_label_position)
        menu.AppendSeparator()
        menu_plot_show_patch = menu.Append(wx.ID_ANY, "Show patch")
        menu_plot_show_mz_int_charge = menu.Append(wx.ID_ANY, "Show annotation: m/z, intensity, charge")
        menu_plot_show_charge = menu.Append(wx.ID_ANY, "Show annotation: charge")
        menu_plot_show_label = menu.Append(wx.ID_ANY, "Show annotation: label")
        menu.AppendSeparator()
        menu_plot_clear_labels = menu.Append(wx.ID_ANY, "Clear annotations")

        # bind events
        self.Bind(wx.EVT_MENU, self.on_show_on_plot, menu_plot_show_charge)
        self.Bind(wx.EVT_MENU, self.on_show_on_plot, menu_plot_show_label)
        self.Bind(wx.EVT_MENU, self.on_show_on_plot, menu_plot_show_mz_int_charge)
        self.Bind(wx.EVT_MENU, self.on_show_on_plot, menu_plot_show_patch)
        self.Bind(wx.EVT_MENU, self.on_clear_from_plot, menu_plot_clear_labels)

        self.Bind(wx.EVT_TOOL, self.on_check_tools, self._menu_show_all_check)
        self.Bind(wx.EVT_TOOL, self.on_check_tools, self._menu_pin_label_to_intensity_check)
        self.Bind(wx.EVT_TOOL, self.on_check_tools, self._menu_autofix_label_position_check)

        self.PopupMenu(menu)
        menu.Destroy()
        self.SetFocus()

    def on_check_tools(self, evt):
        """ Check/uncheck menu item """
        name = evt.GetEventObject().FindItemById(evt.GetId()).GetLabel()

        # check which event was triggered
        if "at intensity value" in name:
            check_value = not self._menu_pin_label_to_intensity
            self._menu_pin_label_to_intensity = check_value
        elif "Auto-adjust" in name:
            check_value = not self._menu_autofix_label_position
            self._menu_autofix_label_position = check_value
        elif "Always " in name:
            check_value = not self._menu_show_all
            self._menu_show_all = check_value

    def on_assign_arrow(self, evt):
        value = evt.GetEventObject().FindItemById(evt.GetId()).GetLabel()
        value = True if value == "True" else False

        for row in range(self.peaklist.GetItemCount()):
            if self.peaklist.IsChecked(index=row):
                self.on_update_annotation(row, ["arrow_show"], **{"arrow_show": value})

                # replot annotation after its been altered
                __, annotation_obj = self.on_get_annotation_obj(row)
                self.on_add_label_to_plot(annotation_obj)

    def on_assign_patch(self, evt):
        value = evt.GetEventObject().FindItemById(evt.GetId()).GetLabel()
        value = True if value == "True" else False

        for row in range(self.peaklist.GetItemCount()):
            if self.peaklist.IsChecked(index=row):
                self.on_update_annotation(row, ["patch_show"], **{"patch_show": value})

                # replot annotation after its been altered
                __, annotation_obj = self.on_get_annotation_obj(row)
                self.on_add_label_to_plot(annotation_obj)

    def on_customise_parameters(self, _):
        from origami.gui_elements.dialog_customise_user_annotations import DialogCustomiseUserAnnotations

        dlg = DialogCustomiseUserAnnotations(self, config=self.config)
        dlg.ShowModal()

    def on_fix_intensity(self, _, fix_type="label"):

        for row in range(self.peaklist.GetItemCount()):
            if self.peaklist.IsChecked(index=row):

                __, annotation_obj = self.on_get_annotation_obj(row)

                mz_narrow = pr_utils.get_narrow_data_range(
                    data=self.data, mzRange=[annotation_obj.span_min, annotation_obj.span_max]
                )
                intensity = pr_utils.find_peak_maximum(mz_narrow)
                max_index = np.where(mz_narrow[:, 1] == intensity)[0]
                intensity = np.round(intensity, 2)
                try:
                    position = mz_narrow[max_index, 0][0]
                except (IndexError, TypeError) as err:
                    logger.warning(err)
                    position = annotation_obj.label_position_x

                if fix_type == "label":
                    self.on_update_annotation(
                        row,
                        ["label_position"],
                        **{"label_position": [position, intensity], "position_x": position, "position_y": intensity},
                    )
                elif fix_type == "patch":
                    patch_position = annotation_obj.patch_position
                    patch_position[1] = 0
                    patch_position[3] = intensity
                    self.on_update_annotation(row, ["patch_position"], **{"patch_position": patch_position})

                # replot annotation after its been altered
                __, annotation_obj = self.on_get_annotation_obj(row)
                self.on_add_label_to_plot(annotation_obj)

    def on_fix_patch_height(self, _):
        self.on_fix_intensity(None, "patch")

    def on_change_item_parameter(self, evt):
        """ Iterate over list to assign charge state """

        rows = self.peaklist.GetItemCount()
        if rows == 0:
            return

        if evt == "label":
            value = DialogSimpleAsk("Assign label for selected item(s)", defaultValue="")
            update_dict = {"label": value}
            update_item = ["label"]
        else:
            value = DialogSimpleAsk("Assign charge state for selected item(s)", defaultValue="1", value_type="int")
            update_dict = {"charge": value}
            update_item = ["charge"]

        if value is None:
            raise MessageError("Incorrect value", "Please type-in appropriate value next time")

        for row in range(rows):
            if self.peaklist.IsChecked(index=row):
                self.on_update_annotation(row, update_item, **update_dict)

                # replot annotation after its been altered
                __, annotation_obj = self.on_get_annotation_obj(row)
                self.on_add_label_to_plot(annotation_obj)

    def on_delete_item(self):
        item_information = self.on_get_item_information(None)
        self.on_delete_annotation(None, item_information["name"])
        self.on_show_on_plot(None)

    def on_delete_items(self, _):
        rows = self.peaklist.GetItemCount() - 1

        while rows >= 0:
            if self.peaklist.IsChecked(index=rows):
                information = self.on_get_item_information(rows)
                self.on_delete_annotation(None, information["name"])
            rows -= 1

        # replot
        self.on_show_on_plot(None)

    def on_assign_color(self, evt):
        from origami.gui_elements.dialog_color_picker import DialogColorPicker

        dlg = DialogColorPicker(self, self.config.customColors)
        if dlg.ShowModal() == "ok":
            color_255, color_1, __ = dlg.GetChosenColour()
            self.config.customColors = dlg.GetCustomColours()
        else:
            return

        try:
            name = evt.GetEventObject().GetName()
            if name == "color.patch":
                self.patch_color_btn.SetBackgroundColour(color_255)
            elif name == "color.label":
                self.label_color_btn.SetBackgroundColour(color_255)
        except AttributeError:
            name = evt.GetEventObject().FindItemById(evt.GetId()).GetLabel()
            if "label" in name:
                update_item = ["label_color"]
                update_dict = {"label_color": color_1}
            else:
                update_item = ["patch_color"]
                update_dict = {"patch_color": color_1}

            rows = self.peaklist.GetItemCount()
            for row in range(rows):
                if self.peaklist.IsChecked(index=row):
                    self.on_update_annotation(row, update_item, **update_dict)

                # replot annotation after its been altered
                __, annotation_obj = self.on_get_annotation_obj(row)
                self.on_add_label_to_plot(annotation_obj)

    def on_get_item_information(self, item_id=None):
        if item_id is None:
            item_id = self.peaklist.item_id

        information = self.peaklist.on_get_item_information(item_id)
        information["color_255to1"] = convert_rgb_255_to_1(information["color"], decimals=3)

        return information

    def on_get_annotation_obj(self, item_id=None):
        if item_id is None:
            item_id = self.peaklist.item_id

        information = self.on_get_item_information(item_id)
        annotations_obj = self.get_annotation_data()
        annotation_obj = annotations_obj[information["name"]]

        return information, annotation_obj

    def on_select_item(self, evt):

        # disable automatic addition
        self.item_loading_lock = True

        self.peaklist.item_id = evt.GetIndex()
        # get data
        __, annotation_obj = self.on_get_annotation_obj(evt.GetIndex())

        # set data in GUI
        self.set_annotation_in_gui(None, annotation_obj)
        self.item_loading_lock = False

        # put a red patch around the peak of interest and zoom-in on the peak
        intensity = annotation_obj.position_y * 10

        if self.highlight_on_selection.GetValue():
            self.plot.plot_add_patch(
                annotation_obj.span_min,
                0,
                annotation_obj.width,
                999999999,
                color="r",
                alpha=self.config.annotation_patch_transparency,
                add_temporary=True,
            )
            self.plot.repaint()

        if self.zoom_on_selection.GetValue():
            window_size = self.zoom_window_size.GetValue()
            self.plot.on_zoom(annotation_obj.span_min - window_size, annotation_obj.span_max + window_size, intensity)

    def on_populate_table(self):
        """Populate table with current annotations"""
        annotations = self.get_annotation_data()
        if annotations is None:
            return

        for annot_obj in annotations.values():
            self.on_add_to_table(annot_obj)

    def on_update_annotation(self, index, update_item, **annotation_dict):
        if not isinstance(update_item, list):
            update_item = list(update_item)

        information = self.on_get_item_information(index)

        annotations_obj = self.get_annotation_data()
        annotations_obj.update_annotation(information["name"], annotation_dict)
        self.annotations_obj = annotations_obj
        self.document_tree.on_update_annotation(
            self.annotations_obj, self.document_title, self.dataset_type, self.dataset_name, set_data_only=True
        )

        try:
            self.on_update_value_in_peaklist(index, update_item, annotation_dict)
        except KeyError as err:
            logger.info(err)

    def set_annotation_in_gui(self, info_dict=None, annotation_obj=None):
        if info_dict is None and annotation_obj is None:
            raise MessageError(
                "Error", "You must provide either `info_dict` or `annotation_obj` to complete this action"
            )

        if info_dict is None:
            name = annotation_obj.name
            label = annotation_obj.label
            label_position_x = annotation_obj.label_position_x
            label_position_y = annotation_obj.label_position_y
            charge = annotation_obj.charge
            arrow_show = annotation_obj.arrow_show
            color = annotation_obj.patch_color
            label_color = annotation_obj.label_color
            patch_position = annotation_obj.patch_position
            patch_show = annotation_obj.patch_show
            position_x = annotation_obj.position_x
            position_y = annotation_obj.position_y
        else:
            name = info_dict["name"]
            label = info_dict["label"]
            label_position_x = info_dict["label_position_x"]
            label_position_y = info_dict["label_position_y"]
            charge = info_dict["charge"]
            arrow_show = info_dict["arrow"]
            label_color = info_dict["label_color"]
            color = info_dict["patch_color"]
            patch_position = info_dict["patch_position"]
            patch_show = info_dict["patch"]
            position_x = info_dict["position_x"]
            position_y = info_dict["position_y"]

        # set values in GUI
        self.name_value.SetValue(name)
        self.label_value.SetValue(label)
        self.label_position_x.SetValue(rounder(label_position_x, 4))
        self.label_position_y.SetValue(rounder(label_position_y, 4))
        self.charge_value.SetValue(str(charge))
        self.add_arrow_to_peak.SetValue(arrow_show)
        self.add_patch_to_peak.SetValue(patch_show)
        self.patch_color_btn.SetBackgroundColour(convert_rgb_1_to_255(color))
        self.label_color_btn.SetBackgroundColour(convert_rgb_1_to_255(label_color))
        self.patch_min_x.SetValue(rounder(patch_position[0], 4))
        self.patch_min_y.SetValue(rounder(patch_position[1], 4))
        self.patch_width.SetValue(rounder(patch_position[2], 4))
        self.patch_height.SetValue(rounder(patch_position[3], 4))

        self.position_x.SetValue(rounder(position_x, 4))
        self.position_y.SetValue(rounder(position_y, 4))

    def get_annotation_from_gui(self):
        info_dict = {
            "name": self.name_value.GetValue(),
            "position_x": str2num(self.position_x.GetValue()),
            "position_y": str2num(self.position_y.GetValue()),
            "label": self.label_value.GetValue(),
            "label_position": [str2num(self.label_position_x.GetValue()), str2num(self.label_position_y.GetValue())],
            "charge": str2int(self.charge_value.GetValue()),
            "label_color": convert_rgb_255_to_1(self.label_color_btn.GetBackgroundColour()),
            "arrow_show": self.add_arrow_to_peak.GetValue(),
            "patch_show": self.add_patch_to_peak.GetValue(),
            "patch_position": [
                str2num(self.patch_min_x.GetValue()),
                str2num(self.patch_min_y.GetValue()),
                str2num(self.patch_width.GetValue()),
                str2num(self.patch_height.GetValue()),
            ],
            "patch_color": convert_rgb_255_to_1(self.patch_color_btn.GetBackgroundColour()),
        }

        return info_dict

    def check_for_duplicate(self, name):
        """Check for duplicate items with the same name"""
        count = self.peaklist.GetItemCount()
        for i in range(count):
            information = self.on_get_item_information(i)

            if information["name"] == name:
                return True, i

        return False, -1

    def get_values_from_data(self, xmin, xmax, ymin, ymax):

        intensity = ymax
        position = xmax - ((xmax - xmin) / 2)
        charge = 1

        # check if the annotation is a point annotation
        if np.abs(np.diff([xmin, xmax])) < 0.2:
            xmin = xmin - 0.2
            xmax = xmax + 0.2

        if self._allow_data_check:
            # try to get position and intensity from data
            try:
                # get narrow data values
                mz_narrow = pr_utils.get_narrow_data_range(data=self.data, mzRange=[xmin, xmax])
                # get maximum intensity from the sub-selected data
                intensity = pr_utils.find_peak_maximum(mz_narrow)
                # retrieve index value
                max_index = np.where(mz_narrow[:, 1] == intensity)[0]
                position = mz_narrow[max_index, 0][0]
            except IndexError:
                position = xmax - ((xmax - xmin) / 2)
                intensity = self.data[:, 1][pr_utils.find_nearest_index(self.data[:, 0], position)]
            except TypeError:
                logger.warning(f"Failed to get annotation intensity / position", exc_info=True)

            charge = self.data_processing.predict_charge_state(
                self.data[:, 0], self.data[:, 1], [xmin - 2, xmax + 2], std_dev=self.config.annotation_charge_std_dev
            )

        label = f"x={position:.4f}\ny={intensity:.2f}"
        name = f"x={position:.4f}; y={intensity:.2f}"
        width = xmax - xmin
        height = ymax - ymin
        if self.plot_type in self._plot_types_1d:
            height = ymax
            ymin = 0

        if self.plot_type in ["mass_spectrum", "1D"]:
            height = intensity

        return xmin, xmax, ymin, ymax, intensity, position, charge, height, width, label, name

    def add_annotation_from_mouse_evt(self, xmin, xmax, ymin, ymax):
        """Add annotations from mouse event"""

        xmin, xmax = check_value_order(xmin, xmax)
        ymin, ymax = check_value_order(ymin, ymax)

        # calculate some presets
        xmin, xmax, ymin, ymax, intensity, position, charge, height, width, label, name = self.get_values_from_data(
            xmin, xmax, ymin, ymax
        )

        info_dict = {
            "name": name,
            "position_x": position,
            "position_y": intensity,
            "label": label,
            "label_position_x": position,
            "label_position_y": intensity,
            "label_position": [position, intensity],
            "arrow": True,
            "width": width,
            "height": height,
            "charge": charge,
            "patch_color": self.config.interactive_ms_annotations_color,
            "label_color": (0.0, 0.0, 0.0),
            "patch_position": [xmin, ymin, width, height],
            "patch": True if self.plot_type == "heatmap" else False,
        }

        self.set_annotation_in_gui(info_dict)
        if self._auto_add_to_table:
            self.on_add_annotation(None)
        self.add_btn.SetFocus()

    def on_add_annotation(self, _):
        if self.item_loading_lock:
            return

        # trigger events
        self.on_toggle_controls(None)

        annotation_dict = self.get_annotation_from_gui()
        name = sanitize_string(annotation_dict["name"])
        annotation_dict["name"] = name

        try:
            annotation_dict = check_annotation_input(annotation_dict)
        except ValueError as err:
            logger.error(err, exc_info=True)
            raise MessageError("Incorrect input", str(err))

        in_table, item_id = self.check_for_duplicate(name)
        annotations_obj = self.get_annotation_data()

        set_data_only = False
        if in_table:
            annotations_obj.update_annotation(name, annotation_dict)
            self.on_update_value_in_peaklist(
                item_id,
                ["patch_color", "charge", "label_position", "patch_position", "label", "arrow_show", "patch_show"],
                annotation_dict,
            )
            set_data_only = True
        else:
            annotations_obj.add_annotation(name, annotation_dict)
            self.on_add_to_table(annotations_obj[name])

        self.annotations_obj = annotations_obj
        self.document_tree.on_update_annotation(
            self.annotations_obj, self.document_title, self.dataset_type, self.dataset_name, set_data_only=set_data_only
        )
        self.on_add_label_to_plot(annotations_obj[name])

    def on_delete_annotation(self, _, name=None):

        # get name if one is not provided
        if name is None:
            name = self.name_value.GetValue()

        # get item index
        __, index = self.check_for_duplicate(name)

        if index != -1:
            annotations_obj = self.get_annotation_data()
            annotations_obj.remove_annotation(name)
            self.peaklist.DeleteItem(index)

            self.annotations_obj = annotations_obj
            self.document_tree.on_update_annotation(
                self.annotations_obj, self.document_title, self.dataset_type, self.dataset_name
            )

    def on_add_to_table(self, annotation_obj):
        """Add data to table"""
        color = convert_rgb_1_to_255(annotation_obj.patch_color)
        self.peaklist.Append(
            [
                "",
                annotation_obj.name,
                annotation_obj.label,
                annotation_obj.label_position,
                str(annotation_obj.arrow_show),
                annotation_obj.charge,
                str(annotation_obj.patch_show),
                annotation_obj.patch_position,
                str(round_rgb(convert_rgb_255_to_1(color))),
            ]
        )
        self.peaklist.SetItemBackgroundColour(self.peaklist.GetItemCount() - 1, color)
        self.peaklist.SetItemTextColour(self.peaklist.GetItemCount() - 1, get_font_color(color, return_rgb=True))

    def on_update_value_in_peaklist(self, item_id, value_types, values):

        if not isinstance(value_types, list):
            value_types = [value_types]

        for value_type in value_types:
            value = values[value_type]
            if value_type in ["color", "patch_color"]:
                color_255, color_1, font_color = get_all_color_types(value)
                self.peaklist.SetItemBackgroundColour(item_id, color_255)
                self.peaklist.SetStringItem(item_id, self.TABLE_COLUMNS["patch_color"], str(color_1))
                self.peaklist.SetItemTextColour(item_id, font_color)
            else:
                column_id = self.TABLE_COLUMNS[value_type]
                self.peaklist.SetStringItem(item_id, column_id, str(value))

    def on_add_label_to_plot(self, annotation_obj):

        annotations_obj = {annotation_obj.name: annotation_obj}

        self.panel_plot.on_plot_1D_annotations(
            annotations_obj,
            plot=None,
            plot_obj=self.plot,
            label_fmt="all",
            pin_to_intensity=self._menu_pin_label_to_intensity,
            document_title=self.document_title,
            dataset_type=self.dataset_type,
            dataset_name=self.dataset_name,
        )

    def on_show_on_plot(self, evt):

        menu_name = ""
        if evt is not None:
            menu_name = evt.GetEventObject().FindItemById(evt.GetId()).GetLabel()

        label_fmt = "label"
        if "Show annotation: charge" in menu_name:
            label_fmt = "charge"
        elif "Show annotation: label" in menu_name:
            label_fmt = "label"
        elif "Show annotation: m/z" in menu_name:
            label_fmt = "all"
        elif "Show patch" in menu_name:
            label_fmt = "patch"

        show_names = self._get_show_list()

        annotations_obj = self.get_annotation_data()
        if not annotations_obj:
            self.on_clear_from_plot(None)

        self.panel_plot.on_plot_1D_annotations(
            annotations_obj,
            plot=None,
            plot_obj=self.plot,
            label_fmt=label_fmt,
            pin_to_intensity=self._menu_pin_label_to_intensity,
            document_title=self.document_title,
            dataset_type=self.dataset_type,
            dataset_name=self.dataset_name,
            show_names=show_names,
        )

    def on_clear_from_plot(self, _):
        self.plot.plot_remove_arrows()
        self.plot.plot_remove_text_and_lines()
        self.plot.plot_remove_patches()

    def _get_show_list(self):

        show_names = []
        for row in range(self.peaklist.GetItemCount()):
            if self.peaklist.IsChecked(index=row) or self._menu_show_all:
                information = self.on_get_item_information(row)
                show_names.append(information["name"])

        return show_names

    def on_save_peaklist(self, _):
        from pandas import DataFrame

        peaklist = []
        for key in self.kwargs["annotations"]:
            annotation = self.kwargs["annotations"][key]
            intensity = str2num(annotation["intensity"])
            charge = annotation["charge"]
            label = annotation["label"]
            min_value = annotation["min"]
            max_value = annotation["max"]
            isotopic_x = annotation.get("isotopic_x", "")
            peaklist.append([min_value, max_value, isotopic_x, intensity, charge, label])

        # make dataframe
        columns = ["min", "max", "position", "intensity", "charge", "label"]
        df = DataFrame(data=peaklist, columns=columns)

        # save
        wildcard = (
            "CSV (Comma delimited) (*.csv)|*.csv|"
            + "Text (Tab delimited) (*.txt)|*.txt|"
            + "Text (Space delimited (*.txt)|*.txt"
        )

        wildcard_dict = {",": 0, "\t": 1, " ": 2}
        dlg = wx.FileDialog(
            self,
            "Please select a name for the file",
            "",
            "",
            wildcard=wildcard,
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        )
        dlg.CentreOnParent()
        if dlg.ShowModal() == wx.ID_OK:
            filename = dlg.GetPath()
            separator = list(wildcard_dict.keys())[list(wildcard_dict.values()).index(dlg.GetFilterIndex())]
            try:
                df.to_csv(path_or_buf=filename, sep=separator)
                print("Saved peaklist to {}".format(filename))
            except IOError:
                print("Could not save file as it is currently open in another program")

    def on_plot_annotated(self):
        """Plot annotated data"""
        self.document_tree.on_show_plot_annotated_data(self.data, plot_obj=self.plot_window)

    def on_plot_1d(self):
        """Plot spectrum"""
        kwargs = self.config.get_mpl_parameters("1D")
        self.plot_view.plot(self.data[:, 0], self.data[:, 1], allow_extraction=False, **kwargs)

    # def on_plot_chromatogram(self):
    #     """Plot chromatogram"""
    #     self.plot_view.plot(self.data[:, 0], self.data[:, 1], allow_extraction=False, **kwargs)
    #
    #     # self.panel_plot.on_plot_RT(
    #     #     self.data[:, 0], self.data[:, 1], plot_obj=self.plot_window, allow_extraction=False, override=False
    #     # )
    #
    # def on_plot_mobilogram(self):
    #     """Plot mobilogram"""
    #     self.panel_plot.on_plot_1D(
    #         self.data[:, 0], self.data[:, 1], plot_obj=self.plot_window, allow_extraction=False, override=False
    #     )

    def on_plot_heatmap(self):
        """Plot heatmap"""
        self.panel_plot.on_plot_2D(
            self.data["zvals"],
            self.data["xvals"],
            self.data["yvals"],
            self.data["xlabels"],
            self.data["ylabels"],
            plot_obj=self.plot_window,
            allow_extraction=False,
            override=False,
        )

    def on_clear_plot(self, _):
        self.plot_window.clear()

    def on_save_figure(self, _):
        plot_title = f"{self.document_title}_{self.dataset_name}".replace(" ", "-").replace(":", "")
        self.panel_plot.save_images(None, None, plot_obj=self.plot_window, image_name=plot_title)

    def on_copy_to_clipboard(self, _):
        self.plot_window.copy_to_clipboard()