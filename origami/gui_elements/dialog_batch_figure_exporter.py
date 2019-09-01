# -*- coding: utf-8 -*-
# __author__ lukasz.g.migas
from __future__ import division

import logging

import wx
from styles import Dialog
from styles import makeCheckbox
from utils.path import check_path_exists

logger = logging.getLogger("origami")


class DialogExportFigures(Dialog):
    """Batch export images"""

    def __init__(self, parent, presenter, config, icons, **kwargs):
        Dialog.__init__(self, parent, title="Export figures....")
        self.view = parent
        self.presenter = presenter
        self.documentTree = self.view.panelDocuments.documents
        self.data_handling = presenter.data_handling
        self.config = config
        self.icons = icons

        self.data_processing = presenter.data_processing
        self.data_handling = presenter.data_handling
        self.panel_plot = self.view.panelPlots

        # get screen dpi
        self.screen_dpi = wx.ScreenDC().GetPPI()

        self.make_gui()
        self.on_toggle_controls(None)

        # setup plot sizes
        self.on_setup_plot_parameters(**kwargs)
        self.on_apply_size_inch(None)

        # setup layout
        self.CentreOnScreen()
        self.Show(True)
        self.SetFocus()

    def on_close(self, evt):
        """Destroy this frame"""
        self.EndModal(wx.ID_NO)

    def make_panel(self):
        panel = wx.Panel(self, -1, size=(-1, -1))

        folder_path = wx.StaticText(panel, -1, "Folder path:")
        self.folder_path = wx.TextCtrl(panel, -1, "", style=wx.TE_READONLY | wx.TE_MULTILINE | wx.TE_CHARWRAP)
        self.folder_path.SetLabel(str(self.config.image_folder_path))
        self.folder_path.Disable()

        self.folder_path_btn = wx.Button(panel, wx.ID_ANY, "...", size=(25, 22))
        self.folder_path_btn.Bind(wx.EVT_BUTTON, self.on_get_path)

        file_format_choice = wx.StaticText(panel, wx.ID_ANY, "File format:")
        self.file_format_choice = wx.Choice(panel, -1, choices=self.config.imageFormatType, size=(-1, -1))
        self.file_format_choice.SetStringSelection(self.config.imageFormat)
        self.file_format_choice.Bind(wx.EVT_CHOICE, self.on_apply)

        resolution_label = wx.StaticText(panel, wx.ID_ANY, "Resolution (DPI):")
        self.image_resolution = wx.SpinCtrlDouble(
            panel, -1, value=str(0), min=50, max=600, initial=0, inc=50, size=(73, -1)
        )
        self.image_resolution.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_apply)
        self.image_resolution.SetValue(self.config.dpi)

        transparency_label = wx.StaticText(panel, wx.ID_ANY, "Transparent:")
        self.image_transparency_check = makeCheckbox(panel, "")
        self.image_transparency_check.SetValue(self.config.transparent)
        self.image_transparency_check.Bind(wx.EVT_CHECKBOX, self.on_apply)

        tight_label = wx.StaticText(panel, wx.ID_ANY, "Tight margins:")
        self.image_tight_check = makeCheckbox(panel, "")
        self.image_tight_check.SetValue(self.config.image_tight)
        self.image_tight_check.Bind(wx.EVT_CHECKBOX, self.on_apply)

        resize_label = wx.StaticText(panel, wx.ID_ANY, "Resize:")
        self.image_resize_check = makeCheckbox(panel, "")
        self.image_resize_check.SetValue(self.config.resize)
        self.image_resize_check.Bind(wx.EVT_CHECKBOX, self.on_apply)
        self.image_resize_check.Bind(wx.EVT_CHECKBOX, self.on_toggle_controls)

        plotSize_export_label = wx.StaticText(panel, -1, "Export plot size (proportion)")
        left_export_label = wx.StaticText(panel, -1, "Left")
        self.left_export_value = wx.SpinCtrlDouble(
            panel, -1, value=str(0), min=0.0, max=1, initial=0, inc=0.01, size=(73, -1)
        )
        self.left_export_value.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_apply)

        bottom_export_label = wx.StaticText(panel, -1, "Bottom")
        self.bottom_export_value = wx.SpinCtrlDouble(
            panel, -1, value=str(0), min=0.0, max=1, initial=0, inc=0.01, size=(73, -1)
        )
        self.bottom_export_value.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_apply)

        width_export_label = wx.StaticText(panel, -1, "Width")
        self.width_export_value = wx.SpinCtrlDouble(
            panel, -1, value=str(0), min=0.0, max=1, initial=0, inc=0.05, size=(73, -1)
        )
        self.width_export_value.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_apply)

        height_export_label = wx.StaticText(panel, -1, "Height")
        self.height_export_value = wx.SpinCtrlDouble(
            panel, -1, value=str(0), min=0.0, max=1, initial=0, inc=0.05, size=(73, -1)
        )
        self.height_export_value.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_apply)

        plotSize_inch_label = wx.StaticText(panel, -1, "Plot size (inch)")
        width_inch_label = wx.StaticText(panel, -1, "Width")
        self.width_inch_value = wx.SpinCtrlDouble(
            panel, -1, value=str(0), min=0.0, max=20, initial=0, inc=1, size=(73, -1)
        )
        self.width_inch_value.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_apply_size_inch)

        height_inch_label = wx.StaticText(panel, -1, "Height")
        self.height_inch_value = wx.SpinCtrlDouble(
            panel, -1, value=str(0), min=0.0, max=20, initial=0, inc=1, size=(73, -1)
        )
        self.height_inch_value.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_apply_size_inch)

        plotSize_cm_label = wx.StaticText(panel, -1, "Plot size (cm)")
        self.width_cm_value = wx.SpinCtrlDouble(
            panel, -1, value=str(0), min=0.0, max=50.8, initial=0, inc=0.5, size=(73, -1)
        )
        self.width_cm_value.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_apply_size_cm)

        self.height_cm_value = wx.SpinCtrlDouble(
            panel, -1, value=str(0), min=0.0, max=50.8, initial=0, inc=0.5, size=(73, -1)
        )
        self.height_cm_value.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_apply_size_cm)

        horizontal_line_0 = wx.StaticLine(panel, -1, style=wx.LI_HORIZONTAL)

        self.save_btn = wx.Button(panel, wx.ID_OK, "Save figures", size=(-1, 22))
        self.save_btn.Bind(wx.EVT_BUTTON, self.on_save)

        self.cancel_btn = wx.Button(panel, wx.ID_OK, "Cancel", size=(-1, 22))
        self.cancel_btn.Bind(wx.EVT_BUTTON, self.on_close)

        btn_grid = wx.GridBagSizer(2, 2)
        n = 0
        btn_grid.Add(self.save_btn, (n, 0), flag=wx.EXPAND)
        btn_grid.Add(self.cancel_btn, (n, 1), flag=wx.EXPAND)

        # pack elements
        grid = wx.GridBagSizer(2, 2)
        n = 0
        grid.Add(folder_path, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.folder_path, (n, 1), wx.GBSpan(1, 4), flag=wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)
        grid.Add(self.folder_path_btn, (n, 5), flag=wx.ALIGN_CENTER_VERTICAL)
        n += 1
        grid.Add(file_format_choice, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.file_format_choice, (n, 1), flag=wx.EXPAND)
        n += 1
        grid.Add(resolution_label, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.image_resolution, (n, 1), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT)
        n += 1
        grid.Add(transparency_label, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.image_transparency_check, (n, 1), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT)
        n += 1
        grid.Add(tight_label, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.image_tight_check, (n, 1), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT)
        n += 1
        grid.Add(resize_label, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(self.image_resize_check, (n, 1), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT)

        n += 1
        grid.Add(left_export_label, (n, 1), flag=wx.ALIGN_CENTER)
        grid.Add(bottom_export_label, (n, 2), flag=wx.ALIGN_CENTER)
        grid.Add(width_export_label, (n, 3), flag=wx.ALIGN_CENTER)
        grid.Add(height_export_label, (n, 4), flag=wx.ALIGN_CENTER)
        n += 1
        grid.Add(plotSize_export_label, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)
        grid.Add(self.left_export_value, (n, 1), flag=wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)
        grid.Add(self.bottom_export_value, (n, 2), flag=wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)
        grid.Add(self.width_export_value, (n, 3), flag=wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)
        grid.Add(self.height_export_value, (n, 4), flag=wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)
        n += 1
        grid.Add(width_inch_label, (n, 1), flag=wx.ALIGN_CENTER)
        grid.Add(height_inch_label, (n, 2), flag=wx.ALIGN_CENTER)
        n += 1
        grid.Add(plotSize_inch_label, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)
        grid.Add(self.width_inch_value, (n, 1), flag=wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)
        grid.Add(self.height_inch_value, (n, 2), flag=wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)
        n += 1
        grid.Add(plotSize_cm_label, (n, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)
        grid.Add(self.width_cm_value, (n, 1), flag=wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)
        grid.Add(self.height_cm_value, (n, 2), flag=wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)
        n += 1
        grid.Add(horizontal_line_0, (n, 0), wx.GBSpan(1, 6), flag=wx.EXPAND)
        n = n + 1
        grid.Add(btn_grid, (n, 0), wx.GBSpan(1, 6), flag=wx.ALIGN_CENTER)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(grid, 0, wx.ALIGN_CENTER_HORIZONTAL, 10)

        # fit layout
        main_sizer.Fit(panel)
        panel.SetSizerAndFit(main_sizer)

        return panel

    def on_setup_plot_parameters(self, **kwargs):
        image_axes_size = kwargs.get("image_axes_size", self.config.image_axes_size)

        self.left_export_value.SetValue(str(image_axes_size[0]))
        self.bottom_export_value.SetValue(str(image_axes_size[1]))
        self.width_export_value.SetValue(str(image_axes_size[2]))
        self.height_export_value.SetValue(str(image_axes_size[3]))

        image_size_inch = kwargs.get("image_size_inch", self.config.image_size_inch)

        self.width_inch_value.SetValue(str(image_size_inch[0]))
        self.height_inch_value.SetValue(str(image_size_inch[1]))

    def on_save(self, evt):
        if not check_path_exists(self.config.image_folder_path):
            from gui_elements.misc_dialogs import DialogBox

            dlg = DialogBox(
                "Incorrect input path",
                f"The folder path is set to `{self.config.image_folder_path}` or does not exist."
                + " Are you sure you would like to continue?",
                type="Question",
            )
            if dlg == wx.ID_NO:
                return

        self.EndModal(wx.OK)

    def on_get_path(self, evt):
        dlg = wx.DirDialog(
            self.view, "Choose a folder where to save images", style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST
        )
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self.folder_path.SetLabel(path)
            self.config.image_folder_path = path

    def on_apply(self, evt):
        self.config.dpi = self.image_resolution.GetValue()
        self.config.imageFormat = self.file_format_choice.GetStringSelection()
        self.config.transparent = self.image_transparency_check.GetValue()
        self.config.resize = self.image_resize_check.GetValue()

        plot_axes_size = [
            self.left_export_value.GetValue(),
            self.bottom_export_value.GetValue(),
            self.width_export_value.GetValue(),
            self.height_export_value.GetValue(),
        ]

        self.config.image_axes_size = plot_axes_size

        if evt is not None:
            evt.Skip()

    def on_apply_size_inch(self, evt):
        plot_inch_size = [self.width_inch_value.GetValue(), self.height_inch_value.GetValue()]
        plot_cm_size = [plot_inch_size[0] * 2.54, plot_inch_size[1] * 2.54]

        self.width_cm_value.SetValue(f"{plot_cm_size[0]:.4f}")
        self.height_cm_value.SetValue(f"{plot_cm_size[1]:.4f}")

        self.config.image_size_inch = plot_inch_size
        self.config.image_size_cm = plot_cm_size
        self.config.image_size_px = [
            int(plot_inch_size[0] * self.screen_dpi[0]),
            int(plot_inch_size[1] * self.screen_dpi[1]),
        ]

    def on_apply_size_cm(self, evt):
        plot_cm_size = [self.width_cm_value.GetValue(), self.height_cm_value.GetValue()]

        plot_inch_size = [plot_cm_size[0] / 2.54, plot_cm_size[1] / 2.54]

        self.config.image_size_inch = plot_inch_size
        self.config.image_size_cm = plot_cm_size
        self.config.image_size_px = [
            int(plot_inch_size[0] * self.screen_dpi[0]),
            int(plot_inch_size[1] * self.screen_dpi[1]),
        ]

        self.width_inch_value.SetValue(f"{plot_inch_size[0]:.4f}")
        self.height_inch_value.SetValue(f"{plot_inch_size[1]:.4f}")

    def on_toggle_controls(self, evt):
        self.config.resize = self.image_resize_check.GetValue()
        for item in [
            self.left_export_value,
            self.bottom_export_value,
            self.width_export_value,
            self.height_export_value,
            self.width_inch_value,
            self.height_inch_value,
            self.width_cm_value,
            self.height_cm_value,
        ]:
            item.Enable(self.config.resize)