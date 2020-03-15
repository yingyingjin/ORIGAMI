# -*- coding: utf-8 -*-
# __author__ lukasz.g.migas
# Standard library imports
# Standard library imports
# Standard library imports
import gc
import os
import re
import time
import logging
from copy import deepcopy
from operator import itemgetter
from functools import partial

# Third-party imports
import wx
import numpy as np
import pandas as pd
from natsort import natsorted

# Local imports
import origami.utils.labels as ut_labels
from origami.ids import ID_renameItem
from origami.ids import ID_openDocInfo
from origami.ids import ID_saveData_csv
from origami.ids import ID_saveData_hdf
from origami.ids import ID_saveDocument
from origami.ids import ID_xlabel_1D_ms
from origami.ids import ID_xlabel_2D_mz
from origami.ids import ID_ylabel_2D_ms
from origami.ids import ID_duplicateItem
from origami.ids import ID_goToDirectory
from origami.ids import ID_xlabel_1D_ccs
from origami.ids import ID_xlabel_2D_ccs
from origami.ids import ID_ylabel_2D_ccs
from origami.ids import ID_docTree_UniDec
from origami.ids import ID_removeDocument
from origami.ids import ID_save1DImageDoc
from origami.ids import ID_save2DImageDoc
from origami.ids import ID_save3DImageDoc
from origami.ids import ID_saveData_excel
from origami.ids import ID_saveRTImageDoc
from origami.ids import ID_showSampleInfo
from origami.ids import ID_xlabel_1D_bins
from origami.ids import ID_ylabel_2D_bins
from origami.ids import ID_ylabel_DTMS_ms
from origami.ids import ID_saveData_pickle
from origami.ids import ID_window_textList
from origami.ids import ID_xlabel_2D_scans
from origami.ids import ID_xlabel_RT_scans
from origami.ids import ID_saveAllDocuments
from origami.ids import ID_showPlotDocument
from origami.ids import ID_xlabel_2D_charge
from origami.ids import ID_xlabel_2D_custom
from origami.ids import ID_ylabel_2D_custom
from origami.ids import ID_ylabel_DTMS_bins
from origami.ids import ID_docTree_compareMS
from origami.ids import ID_process2DDocument
from origami.ids import ID_saveAsInteractive
from origami.ids import ID_xlabel_1D_restore
from origami.ids import ID_xlabel_2D_actVolt
from origami.ids import ID_xlabel_2D_colVolt
from origami.ids import ID_xlabel_2D_restore
from origami.ids import ID_xlabel_RT_restore
from origami.ids import ID_ylabel_2D_restore
from origami.ids import ID_removeAllDocuments
from origami.ids import ID_showPlot1DDocument
from origami.ids import ID_showPlotMSDocument
from origami.ids import ID_showPlotRTDocument
from origami.ids import ID_xlabel_2D_labFrame
from origami.ids import ID_xlabel_2D_time_min
from origami.ids import ID_xlabel_RT_time_min
from origami.ids import ID_docTree_plugin_UVPD
from origami.ids import ID_docTree_save_unidec
from origami.ids import ID_docTree_show_unidec
from origami.ids import ID_getSelectedDocument
from origami.ids import ID_saveDataCSVDocument
from origami.ids import ID_ylabel_DTMS_restore
from origami.ids import ID_xlabel_1D_ms_arrival
from origami.ids import ID_xlabel_2D_wavenumber
from origami.ids import ID_ylabel_2D_ms_arrival
from origami.ids import ID_docTree_add_mzIdentML
from origami.ids import ID_docTree_addToMMLTable
from origami.ids import ID_saveAsDataCSVDocument
from origami.ids import ID_saveDataCSVDocument1D
from origami.ids import ID_saveWaterfallImageDoc
from origami.ids import ID_window_multipleMLList
from origami.ids import ID_xlabel_2D_actLabFrame
from origami.ids import ID_xlabel_2D_retTime_min
from origami.ids import ID_xlabel_RT_retTime_min
from origami.ids import ID_docTree_addToTextTable
from origami.ids import ID_xlabel_2D_massToCharge
from origami.ids import ID_ylabel_DTMS_ms_arrival
from origami.ids import ID_docTree_showMassSpectra
from origami.ids import ID_saveAsDataCSVDocument1D
from origami.ids import ID_showPlotDocument_violin
from origami.ids import ID_docTree_addOneToMMLTable
from origami.ids import ID_docTree_addOneToTextTable
from origami.ids import ID_docTree_duplicate_document
from origami.ids import ID_showPlotDocument_waterfall
from origami.ids import ID_docTree_action_open_extract
from origami.ids import ID_docTree_show_refresh_document
from origami.ids import ID_docTree_action_open_origami_ms
from origami.ids import ID_docTree_action_open_extractDTMS
from origami.ids import ID_docTree_action_open_peak_picker
from origami.ids import ID_docTree_addInteractiveToTextTable
from origami.ids import ID_docTree_addOneInteractiveToTextTable
from origami.styles import make_menu_item
from origami.utils.path import clean_filename
from origami.utils.color import get_font_color
from origami.utils.color import convert_rgb_1_to_255
from origami.utils.color import convert_rgb_255_to_1
from origami.utils.converters import str2int
from origami.utils.converters import str2num
from origami.utils.converters import byte2str
from origami.utils.exceptions import MessageError
from origami.readers.io_text_files import saveAsText
from origami.gui_elements.misc_dialogs import DialogBox
from origami.gui_elements.misc_dialogs import DialogSimpleAsk
from origami.gui_elements.panel_document_information import PanelDocumentInformation

logger = logging.getLogger(__name__)


class PanelDocumentTree(wx.Panel):
    """Make documents panel to store all information about open files"""

    def __init__(self, parent, config, icons, presenter):
        wx.Panel.__init__(
            self, parent, id=wx.ID_ANY, pos=wx.DefaultPosition, size=wx.Size(250, -1), style=wx.TAB_TRAVERSAL
        )

        self.parent = parent
        self.config = config
        self.presenter = presenter
        self.icons = icons

        self.makeTreeCtrl()

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.documents, 1, wx.EXPAND, 0)
        self.sizer.Fit(self)
        self.SetSizer(self.sizer)

    def __del__(self):
        pass

    def makeTreeCtrl(self):
        self.documents = DocumentTree(self, self.parent, self.presenter, self.icons, self.config, size=(-1, -1))


class DocumentTree(wx.TreeCtrl):
    """Documents tree"""

    def __init__(
        self,
        parent,
        mainParent,
        presenter,
        icons,
        config,
        size=(-1, -1),
        style=wx.TR_TWIST_BUTTONS | wx.TR_HAS_BUTTONS | wx.TR_FULL_ROW_HIGHLIGHT,
    ):
        wx.TreeCtrl.__init__(self, parent, size=size, style=style)

        self.parent = parent
        self.view = mainParent
        self.presenter = presenter
        self.icons = icons
        self.config = config

        self._document_data = None  # itemData
        self._item_id = None  # currentItem
        self._indent = None  # indent
        self._document_type = None  # itemType
        self._item_leaf = None  # extractData
        self._item_branch = None  # extractParent
        self._item_root = None  # extractGrandparent

        self._indent_items = ["Annotations", "UniDec"]

        # widgets
        self._bokeh_panel = None
        self._annotate_panel = None
        self._compare_panel = None
        self._overlay_panel = None
        self._picker_panel = None
        self._lesa_panel = None
        self._import_panel = None

        # set font and colour
        self.SetFont(wx.SMALL_FONT)

        # init bullets
        self.bullets = wx.ImageList(13, 12)
        self.SetImageList(self.bullets)
        self.reset_document_tree_bullets()

        # add root
        root = self.AddRoot("Documents")
        self.SetItemImage(root, 0, wx.TreeItemIcon_Normal)

        # Add bindings
        self.Bind(wx.EVT_TREE_KEY_DOWN, self.on_keyboard_event, id=wx.ID_ANY)
        self.Bind(wx.EVT_TREE_ITEM_MENU, self.on_right_click, id=wx.ID_ANY)
        self.Bind(wx.EVT_LEFT_DCLICK, self.on_double_click)

        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.on_enable_document, id=wx.ID_ANY)
        self.Bind(wx.EVT_TREE_SEL_CHANGING, self.on_item_selecting, id=wx.ID_ANY)
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_enable_document, id=wx.ID_ANY)
        self.Bind(wx.EVT_TREE_DELETE_ITEM, self.on_item_deleted, id=wx.ID_ANY)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_keyboard_event, id=wx.ID_ANY)

    def reset_document_tree_bullets(self):
        """Erase all bullets and make defaults."""
        self.bullets.RemoveAll()
        self.bullets.Add(self.icons.bulletsLib["bulletsDoc"])
        self.bullets.Add(self.icons.bulletsLib["bulletsMS"])
        self.bullets.Add(self.icons.bulletsLib["bulletsDT"])
        self.bullets.Add(self.icons.bulletsLib["bulletsRT"])
        self.bullets.Add(self.icons.bulletsLib["bulletsDot"])
        self.bullets.Add(self.icons.bulletsLib["bulletsAnnot"])
        self.bullets.Add(self.icons.bulletsLib["bullets2DT"])
        self.bullets.Add(self.icons.bulletsLib["bulletsCalibration"])
        self.bullets.Add(self.icons.bulletsLib["bulletsOverlay"])

        self.bullets.Add(self.icons.bulletsLib["bulletsDocOn"])
        self.bullets.Add(self.icons.bulletsLib["bulletsMSIon"])
        self.bullets.Add(self.icons.bulletsLib["bulletsDTIon"])
        self.bullets.Add(self.icons.bulletsLib["bulletsRTIon"])
        self.bullets.Add(self.icons.bulletsLib["bulletsDotOn"])
        self.bullets.Add(self.icons.bulletsLib["bulletsAnnotIon"])
        self.bullets.Add(self.icons.bulletsLib["bullets2DTIon"])
        self.bullets.Add(self.icons.bulletsLib["bulletsCalibrationIon"])
        self.bullets.Add(self.icons.bulletsLib["bulletsOverlayIon"])

        self.bullets_dict = {
            "document": 0,
            "mass_spec": 1,
            "drift_time": 2,
            "rt": 3,
            "dots": 4,
            "annot": 5,
            "heatmap": 6,
            "calibration": 7,
            "overlay": 8,
            "document_on": 9,
            "mass_spec_on": 10,
            "drift_time_on": 11,
            "rt_on": 12,
            "dots_on": 13,
            "annot_on": 14,
            "heatmap_on": 15,
            "calibration_on": 16,
            "overlay_on": 17,
        }

    def setup_handling_and_processing(self):
        self.data_processing = self.view.data_processing
        self.data_handling = self.view.data_handling
        self.data_visualisation = self.view.data_visualisation

        self.panel_plot = self.view.panelPlots

        self.ionPanel = self.view.panelMultipleIons
        self.ionList = self.ionPanel.peaklist

        self.textPanel = self.view.panelMultipleText
        self.textList = self.textPanel.peaklist

        self.filesPanel = self.view.panelMML
        self.filesList = self.filesPanel.peaklist

    def on_item_deleted(self, evt):
        pass

    def on_item_selecting(self, evt):

        # Get selected item
        self._item_id = evt.GetItem()

        # Get indent level for selected item
        self._indent = self.get_item_indent(self._item_id)
        if self._indent > 1:
            parent = self.getParentItem(self._item_id, 1)
            item = self.getParentItem(self._item_id, 2)

            self._item_branch = self.GetItemText(self.GetItemParent(self._item_id))
            self._item_leaf = self.GetItemText(self._item_id)
            self._item_root = self.GetItemText(self.GetItemParent(self.GetItemParent(self._item_id)))

            # split
            try:
                self.splitText = re.split("-|,|:|__", self._item_leaf)
            except Exception:
                self.splitText = []

            # Check item
            if not item:
                return

            # Get item data for specified item
            self._document_data = self.GetPyData(parent)
            self._document_type = self.GetItemText(item)
            try:
                self._current_data = self.GetPyData(self._item_id)
            except Exception:
                self._current_data = None

            if self.config.debug:
                msg = (
                    f"_document_type: {self._document_type} | _item_leaf: {self._item_leaf} | "
                    + f"_item_branch: {self._item_branch} | _item_root: {self._item_root} | _indent: {self._indent}"
                )
                logger.debug(msg)
        else:
            self._item_leaf = None
            self._item_branch = None
            self._item_root = None

    def getItemIDbyName(self, root, title):
        item, cookie = self.GetFirstChild(root)

        while item.IsOk():
            text = self.GetItemText(item)
            if text == title:
                return item
            if self.ItemHasChildren(item):
                match = self.getItemIDbyName(item, title)
                if match.IsOk():
                    return match
            item, cookie = self.GetNextChild(root, cookie)

        return wx.TreeItemId()

    def on_enable_document(
        self,
        getSelected=False,
        loadingData=False,
        highlightSelected=False,
        expandAll=False,
        expandSelected=None,
        evt=None,
    ):
        """
        Highlights and returns currently selected document
        ---
        Parameters
        ----------
        getSelected
        loadingData: booleat, flag to tell the function that we are loading data
        highlightSelected
        expandAll : boolean, flag to expand or not of the tree
        expandSelected : string, name of item to expand
        """

        root = self.GetRootItem()
        selected = self.GetSelection()
        item, cookie = self.GetFirstChild(root)

        if evt is None:
            evtID = None
        else:
            try:
                evtID = evt.GetId()
            except AttributeError:
                evtID = None

        while item.IsOk():
            self.SetItemBold(item, False)
            if loadingData:
                self.CollapseAllChildren(item)
            item, cookie = self.GetNextChild(root, cookie)

        # Select parent document
        if selected is not None:
            item = self.getParentItem(selected, 1)
            try:
                self.SetItemBold(item, True)
            except wx._core.PyAssertionError:
                pass
            if loadingData or evtID == ID_getSelectedDocument:
                self.Expand(item)  # Parent item
                if expandAll:
                    self.ExpandAllChildren(item)

            # window label
            try:
                text = self.GetItemText(item)
                if text != "Documents":
                    self.presenter.currentDoc = text
                    self.view.SetTitle(
                        "ORIGAMI - v{} - {} ({})".format(self.config.version, text, self._document_data.dataType)
                    )
            except Exception:
                self.view.SetTitle("ORIGAMI - v{}".format(self.config.version))

            # status text
            if self._document_data is not None:
                try:
                    parameters = self._document_data.parameters
                    msg = "{}-{}".format(parameters.get("startMS", ""), parameters.get("endMS", ""))
                    if msg == "-":
                        msg = ""
                    self.presenter.view.SetStatusText(msg, 1)
                    msg = "MSMS: {}".format(parameters.get("setMS", ""))
                    if msg == "MSMS: ":
                        msg = ""
                    self.presenter.view.SetStatusText(msg, 2)
                except Exception:
                    pass

            # In case we also interested in selected item
            if getSelected:
                selectedText = self.GetItemText(selected)
                if highlightSelected:
                    self.SetItemBold(selected, True)
                return text, selected, selectedText
            else:
                return text

        if evt is not None:
            evt.Skip()

    def get_item_indent(self, item):
        # Check item first
        if not item.IsOk():
            return False

        # Get Indent
        indent = 0
        root = self.GetRootItem()
        while item.IsOk():
            if item == root:
                return indent
            else:
                item = self.GetItemParent(item)
                indent += 1
        return indent

    def getParentItem(self, item, level, getSelected=False):
        """ Get parent item for selected item and level"""
        # Get item
        for x in range(level, self.get_item_indent(item)):
            item = self.GetItemParent(item)

        if getSelected:
            itemText = self.GetItemText(item)
            return item, itemText

        return item

    def get_item_by_data(self, data, root=None, cookie=0):
        """Get item by its data."""

        # get root
        if root is None:
            root = self.GetRootItem()

        # check children
        if self.ItemHasChildren(root):
            firstchild, cookie = self.GetFirstChild(root)
            if self.GetPyData(firstchild) is data:
                return firstchild
            matchedItem = self.get_item_by_data(data, firstchild, cookie)
            if matchedItem:
                return matchedItem

        # check siblings
        child = self.GetNextSibling(root)
        if child and child.IsOk():
            if self.GetPyData(child) is data:
                return child

            matchedItem = self.get_item_by_data(data, child, cookie)
            if matchedItem:
                return matchedItem

        # no such item found
        return False

    def on_keyboard_event(self, evt):
        """ Shortcut to navigate through Document Tree """
        key = evt.GetKeyCode()

        # detelete item
        if key == wx.WXK_DELETE:
            item = self.GetSelection()
            indent = self.get_item_indent(item)
            if indent == 0:
                self.on_delete_all_documents(evt=None)
            else:
                self.on_delete_item(evt=None)
        elif key == 80:
            if self._document_type in ["Drift time (2D)", "Drift time (2D, processed)"]:
                self.on_process_2D(evt=None)
            elif self._document_type in [
                "Drift time (2D, EIC)",
                "Drift time (2D, combined voltages, EIC)",
                "Drift time (2D, processed, EIC)",
                "Input data",
                "Statistical",
            ] and self._item_leaf not in [
                "Drift time (2D, EIC)",
                "Drift time (2D, combined voltages, EIC)",
                "Drift time (2D, processed, EIC)",
                "Input data",
                "Statistical",
            ]:
                self.on_process_2D(evt=None)
            elif (
                self._document_type in ["Mass Spectrum", "Mass Spectrum (processed)", "Mass Spectra"]
                and self._item_leaf != "Mass Spectra"
            ):
                self.on_process_MS(evt=None)
        elif key == 341:  # F2
            self.onRenameItem(None)

        if evt and key not in [wx.WXK_DELETE]:
            evt.Skip()

    def on_update_gui(self, query, subkey, dataset_name):
        """Update various elements of the UI based on changes made to the document"""
        # TODO: add trigger to update overlay item window when something is deleted
        # TODO: add trigger to update annotations window when something is deleted
        # TODO: add trigger to update interactive window when something is deleted

        document_title, dataset_type, __ = query
        document = self.data_handling.on_get_document(document_title)
        document_type = document.dataType

        _subkey_check = all([el == "" for el in subkey])

        #         print(query, subkey, dataset_name)

        if not dataset_name:
            dataset_name = None

        if (
            dataset_type in ["Drift time (2D, EIC)"]
            or dataset_type in ["Drift time (2D, combined voltages, EIC)"]
            and document_type == "Type: MANUAL"
        ):
            self.ionPanel.delete_row_from_table(dataset_name, document_title)
            self.on_update_extracted_patches(document_title, None, dataset_name)

        if dataset_type in ["Drift time (2D)"] and document_type == "Type: 2D IM-MS":
            self.textPanel.delete_row_from_table(document_title)

        if dataset_type in ["Mass Spectra"]:
            self.filesPanel.delete_row_from_table(dataset_name, document_title)

        # update comparison viewer
        if self._compare_panel:
            document_spectrum_list = self.data_handling.generate_item_list_mass_spectra("comparison")
            document_list = list(document_spectrum_list.keys())
            count = sum([len(document_spectrum_list[_title]) for _title in document_spectrum_list])
            if count >= 2:
                self._compare_panel._set_item_lists(
                    document_list=document_list, document_spectrum_list=document_spectrum_list, refresh=True
                )
            else:
                DialogBox(
                    exceptionTitle="Warning",
                    exceptionMsg="The MS comparison window requires at least 2 items to compare."
                    + f" There are only {count} items in the list. The window will be closed",
                    type="Error",
                    exceptionPrint=True,
                )
                self._compare_panel.on_close(None)

        if self._picker_panel and self._picker_panel._check_active([document_title, dataset_type, dataset_name]):
            DialogBox(
                exceptionTitle="Warning",
                exceptionMsg="The peak picking panel is operating on the same item that was just deleted."
                + " The window will be closed",
                type="Error",
                exceptionPrint=True,
            )
            self._picker_panel.on_close(None)

        if self._annotate_panel and self._annotate_panel._check_active([document_title, dataset_type, dataset_name]):
            if not _subkey_check:
                self._annotate_panel.on_clear_table()
            else:
                DialogBox(
                    exceptionTitle="Warning",
                    exceptionMsg="The annotation panel is operating on the same item that was just deleted."
                    + " The window will be closed",
                    type="Error",
                    exceptionPrint=True,
                )
                self._annotate_panel.on_close(None)

        # delete annotation links
        if not _subkey_check:
            subkey_parent, __ = subkey

            if subkey_parent == "Annotations":
                print("delete annotations")
            elif subkey_parent == "UniDec":
                print("delete unidec")

    def on_delete_item(self, evt):
        """Delete selected item from the document tree and the presenter dictionary"""

        # delete document
        if self._indent == 1:
            self.removeDocument(None)
            return

        # get current item by examining the ident stack
        query, subkey, dataset_name = self._get_delete_info_based_on_indent()
        _subkey_check = all([el == "" for el in subkey])

        # get data
        __, data = self.data_handling.get_mobility_chromatographic_data(query, as_copy=False)
        item_parent = self.GetNextSibling(self._item_id)
        if item_parent:
            self.SelectItem(item_parent)

        # check whether subkey exist and if so, get item
        if subkey and not _subkey_check:
            item_child = self.get_item_by_data(self.GetPyData(self._item_id))
            subkey_parent, subkey_child = subkey
            if dataset_name:
                if subkey_child != "":
                    del data[dataset_name][subkey_parent.lower()][subkey_child]
                else:
                    data[dataset_name].pop(subkey_parent.lower(), None)
            else:
                if subkey_child != "":
                    del data[subkey_parent.lower()][subkey_child]
                else:
                    data.pop(subkey_parent.lower(), None)
            if item_child:
                self.Delete(item_child)

            self.data_handling.set_parent_mobility_chromatographic_data(query, data)

        # delete only one item from dataset
        if dataset_name and _subkey_check:
            item_child = self.get_item_by_data(data.get(dataset_name, False))
            item_parent = self.get_item_by_data(data)
            if not item_child:
                raise MessageError(
                    "Error",
                    "Could not identify which item should be deleted. Please right-click on an item and"
                    + " select `Delete item` to delete the item from the document.",
                )
            if data:
                self.data_handling.set_parent_mobility_chromatographic_data([query[0], query[1], dataset_name], dict())
                self.Delete(item_child)
                self.SelectItem(item_parent)
            else:
                self.data_handling.set_parent_mobility_chromatographic_data(query, dict())
                self.Delete(item_parent)
            # delete parent if its empty
            __, data = self.data_handling.get_mobility_chromatographic_data(query, as_copy=False)

            if not data:
                self.Delete(item_parent)

            logger.info(f"Deleted {query[0]} : {query[1]} : {dataset_name}")

        # delete entire dataset
        if not dataset_name and _subkey_check:
            item = self.get_item_by_data(data)
            if not item:
                raise MessageError(
                    "Error",
                    "Could not identify which item should be deleted. Please right-click on an item and"
                    + " select `Delete item` to delete the item from the document.",
                )
            self.data_handling.set_parent_mobility_chromatographic_data(query, dict())
            self.Delete(item)
            logger.info(f"Deleted {query[0]} : {query[1]}")

        self.on_update_gui(query, subkey, dataset_name)

    def set_document(self, document_old, document_new):
        """Replace old document data with new

        Parameters
        ----------
        document_old: py object
            old document (before any data changes)
        document_new: py object
            new document (after any data changes)
        """

        # try to get dataset object
        try:
            docItem = self.get_item_by_data(document_old)
        except Exception:
            docItem = False

        if docItem is not False:
            try:
                self.SetPyData(docItem, document_new)
            except Exception:
                self.data_handling.on_update_document(document_new, "document")
        else:
            self.data_handling.on_update_document(document_new, "document")

    def on_double_click(self, evt):

        tstart = time.clock()
        # Get selected item
        item = self.GetSelection()
        self._item_id = item

        # Get the current text value for selected item
        itemType = self.GetItemText(item)
        if itemType == "Documents":
            menu = wx.Menu()
            menu.AppendItem(
                make_menu_item(
                    parent=menu,
                    id=ID_saveAllDocuments,
                    text="Save all documents",
                    bitmap=self.icons.iconsLib["save_multiple_16"],
                )
            )
            menu.AppendItem(
                make_menu_item(
                    parent=menu,
                    id=ID_removeAllDocuments,
                    text="Delete all documents",
                    bitmap=self.icons.iconsLib["bin16"],
                )
            )
            self.PopupMenu(menu)
            menu.Destroy()
            self.SetFocus()
            return

        # Get indent level for selected item
        self._indent = self.get_item_indent(item)
        if self._indent > 1:
            extract = item  # Specific Ion/file name
            item = self.getParentItem(item, 2)  # Item type
            itemType = self.GetItemText(item)
        else:
            extract = None

        # split
        try:
            self.splitText = re.split(r"-|,|:|__| \(", self._item_leaf)
        except Exception:
            self.splitText = []
        # Get the ion/file name from deeper indent
        if extract is None:
            self._item_leaf = None
            self._item_branch = None
            self._item_root = None
        else:
            self._item_leaf = self.GetItemText(extract)
            self._item_branch = self.GetItemText(self.GetItemParent(extract))
            self._item_root = self.GetItemText(self.GetItemParent(self.GetItemParent(extract)))

        if self._document_data is None:
            return
        self.title = self._document_data.title

        if self._indent == 1 and self._item_leaf is None:
            self.on_refresh_document()
        elif self._document_type == "Mass Spectra" and self._item_leaf == "Mass Spectra":
            self.on_open_spectrum_comparison_viewer(evt=None)
        elif self._document_type in ["Mass Spectrum", "Mass Spectrum (processed)", "Mass Spectra"]:
            if (
                self._item_leaf in ["Mass Spectrum", "Mass Spectrum (processed)", "Mass Spectra"]
                or self._item_branch == "Mass Spectra"
            ):
                self.on_show_plot(evt=ID_showPlotDocument)
            elif self._item_leaf == "UniDec":
                self.on_open_UniDec(None)
            elif self._item_branch == "UniDec":
                self.on_open_UniDec(None)
            elif self._item_leaf == "Annotations":
                self.on_open_annotation_editor(None)
        elif self._document_type in [
            "Chromatogram",
            "Chromatograms (EIC)",
            "Annotated data",
            "Drift time (1D)",
            "Drift time (1D, EIC, DT-IMS)",
            "Drift time (1D, EIC)",
            "Chromatograms (combined voltages, EIC)",
            "Drift time (2D)",
            "Drift time (2D, processed)",
            "Drift time (2D, EIC)",
            "Drift time (2D, combined voltages, EIC)",
            "Drift time (2D, processed, EIC)",
            "Input data",
            "Statistical",
            "Overlay",
            "DT/MS",
            "Tandem Mass Spectra",
        ]:
            if self._item_leaf == "Annotations":
                self.on_open_annotation_editor(None)
            else:
                self.on_show_plot(None)
        elif self._document_type == "Sample information":
            self.onShowSampleInfo(evt=None)
        elif self._indent == 1:
            self.onOpenDocInfo(evt=None)

        tend = time.clock()
        print("It took: %s seconds to process double-click." % str(np.round((tend - tstart), 4)))

    def on_save_document_as(self, evt):
        """
        Save current document. With asking for path.
        """
        document_title = self._document_data.title
        self.data_handling.on_save_document_fcn(document_title)

    def on_save_document(self, evt):
        """
        Save current document. Without asking for path.
        """
        if self._document_data is not None:
            document_title = self._document_data.title
            wx.CallAfter(self.data_handling.on_save_document_fcn, document_title, save_as=False)

    def on_refresh_document(self, evt=None):
        document = self.presenter.documentsDict.get(self.title, None)
        if document is None:
            return

        # set what to plot
        mass_spectrum, chromatogram, mobilogram, heatmap = False, False, False, False
        # check document
        if document.dataType == "Type: ORIGAMI":
            mass_spectrum, chromatogram, mobilogram, heatmap = True, True, True, True
            go_to_page = self.config.panelNames["MS"]
        elif document.dataType == "Type: MANUAL":
            mass_spectrum = True
            go_to_page = self.config.panelNames["MS"]
        elif document.dataType == "Type: Multifield Linear DT":
            mass_spectrum, chromatogram, mobilogram, heatmap = True, True, True, True
            go_to_page = self.config.panelNames["MS"]
        elif document.dataType == "Type: 2D IM-MS":
            heatmap = True
            go_to_page = self.config.panelNames["2D"]
        else:
            return

        # clear all plots
        self.panel_plot.on_clear_all_plots()

        if mass_spectrum:
            try:
                msX = document.massSpectrum["xvals"]
                msY = document.massSpectrum["yvals"]
                try:
                    xlimits = document.massSpectrum["xlimits"]
                except KeyError:
                    xlimits = [document.parameters["startMS"], document.parameters["endMS"]]
                name_kwargs = {"document": document.title, "dataset": "Mass Spectrum"}
                self.panel_plot.on_plot_MS(msX, msY, xlimits=xlimits, set_page=False, **name_kwargs)
            except Exception:
                pass

        if chromatogram:
            try:
                rtX = document.RT["xvals"]
                rtY = document.RT["yvals"]
                xlabel = document.RT["xlabels"]
                self.panel_plot.on_plot_RT(rtX, rtY, xlabel, set_page=False)
            except Exception:
                pass

        if mobilogram:
            try:
                dtX = document.DT["xvals"]
                dtY = document.DT["yvals"]
                if len(dtY) >= 1:
                    try:
                        dtY = document.DT["yvalsSum"]
                    except KeyError:
                        pass
                xlabel = document.DT["xlabels"]
                self.panel_plot.on_plot_1D(dtX, dtY, xlabel, set_page=False)
            except Exception:
                pass

        if heatmap:
            try:
                zvals = document.IMS2D["zvals"]
                xvals = document.IMS2D["xvals"]
                yvals = document.IMS2D["yvals"]
                xlabel = document.IMS2D["xlabels"]
                ylabel = document.IMS2D["ylabels"]
                self.panel_plot.on_plot_2D(zvals, xvals, yvals, xlabel, ylabel, override=True)
            except Exception:
                pass

        # go to page
        self.panel_plot._set_page(go_to_page)

    def on_check_xlabels_RT(self):
        """Check label of the chromatogram dataset"""

        data = self.GetPyData(self._item_id)
        xlabel = data["xlabels"]

        xlabel_evt_dict = {
            "Scans": ID_xlabel_RT_scans,
            "Time (min)": ID_xlabel_RT_time_min,
            "Retention time (min)": ID_xlabel_RT_retTime_min,
        }

        return xlabel_evt_dict.get(xlabel, None)

    def on_check_xylabels_2D(self):
        """Check label of the 2D datasets"""

        xlabel_evt_dict = {
            "Scans": ID_xlabel_2D_scans,
            "Time (min)": ID_xlabel_2D_time_min,
            "Retention time (min)": ID_xlabel_2D_retTime_min,
            "Collision Voltage (V)": ID_xlabel_2D_colVolt,
            "Activation Voltage (V)": ID_xlabel_2D_actVolt,
            "Lab Frame Energy (eV)": ID_xlabel_2D_labFrame,
            "Activation Energy (eV)": ID_xlabel_2D_actLabFrame,
            "Mass-to-charge (Da)": ID_xlabel_2D_massToCharge,
            "m/z (Da)": ID_xlabel_2D_mz,
            "Wavenumber (cm⁻¹)": ID_xlabel_2D_wavenumber,
            "Charge": ID_xlabel_2D_charge,
            "Collision Cross Section (Å²)": ID_xlabel_2D_ccs,
        }

        ylabel_evt_dict = {
            "Drift time (bins)": ID_ylabel_2D_bins,
            "Drift time (ms)": ID_ylabel_2D_ms,
            "Arrival time (ms)": ID_ylabel_2D_ms_arrival,
            "Collision Cross Section (Å²)": ID_ylabel_2D_ccs,
        }

        # Select dataset
        if self._document_type == "Drift time (2D)":
            data = self._document_data.IMS2D
        elif self._document_type == "Drift time (2D, processed)":
            data = self._document_data.IMS2Dprocess
        elif self._document_type == "Drift time (2D, EIC)":
            if self._item_leaf == "Drift time (2D, EIC)":
                return None, None
            data = self._document_data.IMS2Dions[self._item_leaf]
        elif self._document_type == "Drift time (2D, combined voltages, EIC)":
            if self._item_leaf == "Drift time (2D, combined voltages, EIC)":
                return None, None
            data = self._document_data.IMS2DCombIons[self._item_leaf]
        elif self._document_type == "Drift time (2D, processed, EIC)":
            if self._item_leaf == "Drift time (2D, processed, EIC)":
                return None, None
            data = self._document_data.IMS2DionsProcess[self._item_leaf]
        elif self._document_type == "Input data":
            if self._item_leaf == "Input data":
                return None, None
            data = self._document_data.IMS2DcompData[self._item_leaf]

        # Get labels
        xlabel = data.get("xlabels", None)
        ylabel = data.get("ylabels", None)

        return xlabel_evt_dict.get(xlabel, ID_xlabel_2D_custom), ylabel_evt_dict.get(ylabel, ID_ylabel_2D_custom)

    def on_check_xlabels_1D(self):
        """Check labels of the mobilogram dataset"""
        data = self.GetPyData(self._item_id)

        # Get labels
        xlabel = data["xlabels"]

        xlabel_evt_dict = {
            "Drift time (bins)": ID_xlabel_1D_bins,
            "Drift time (ms)": ID_xlabel_1D_ms,
            "Arrival time (ms)": ID_xlabel_1D_ms_arrival,
            "Collision Cross Section (Å²)": ID_xlabel_1D_ccs,
        }

        return xlabel_evt_dict.get(xlabel, ID_ylabel_2D_bins)

    def on_check_xlabels_DTMS(self):
        """Check labels of the DT/MS dataset"""
        if self._document_type == "DT/MS":
            data = self._document_data.DTMZ

        # Get labels
        ylabel = data["ylabels"]

        ylabel_evt_dict = {
            "Drift time (bins)": ID_ylabel_DTMS_bins,
            "Drift time (ms)": ID_ylabel_DTMS_ms,
            "Arrival time (ms)": ID_ylabel_DTMS_ms_arrival,
        }

        return ylabel_evt_dict.get(ylabel, ID_ylabel_DTMS_bins)

    def on_change_charge_state(self, evt):
        """Change charge state for item in the document tree

        TODO: this will not update the ionPanel when assigning charge to Drift time (1D, EIC, DT-IMS)
        """

        # Check that the user hasn't selected the header
        if self._document_type in [
            "Drift time (2D, EIC)",
            "Drift time (2D, combined voltages, EIC)",
            "Drift time (2D, processed, EIC)",
            "Input data",
        ] and self._item_leaf in [
            "Drift time (2D, EIC)",
            "Drift time (2D, combined voltages, EIC)",
            "Drift time (2D, processed, EIC)",
            "Input data",
        ]:
            raise MessageError("Incorrect data type", "Please select a single ion in the Document panel.\n\n\n")

        __, data, __ = self._on_event_get_mobility_chromatogram_data()
        current_charge = data.get("charge", None)

        charge = DialogSimpleAsk("Type in new charge state", defaultValue=str(current_charge))

        charge = str2int(charge)

        if charge in ["", "None", None]:
            logger.warning(f"The defined value `{charge}` is not correct")
            return

        query_info = self._on_event_get_mobility_chromatogram_query()
        document = self.data_handling.set_mobility_chromatographic_keyword_data(query_info, charge=charge)

        # update data in side panel
        self.ionPanel.on_find_and_update_values(query_info[2], charge=charge)

        # update document
        self.data_handling.on_update_document(document, "no_refresh")

    def _on_event_get_mass_spectrum(self, **kwargs):

        query = self._get_query_info_based_on_indent()
        document, data = self.data_handling.get_mobility_chromatographic_data(query)

        return document, data, query[2]

    def _on_event_get_mobility_chromatogram_query(self, **kwargs):
        if not all([item in kwargs for item in ["document_title", "dataset_type", "dataset_name"]]):
            query = self._get_query_info_based_on_indent()
        else:
            document_title = kwargs.pop("document_name")
            dataset_type = kwargs.pop("dataset_type")
            dataset_name = kwargs.pop("dataset_name")
            query = [document_title, dataset_type, dataset_name]

        return query

    def _on_event_get_mobility_chromatogram_data(self, **kwargs):
        query = self._on_event_get_mobility_chromatogram_query(**kwargs)

        document, data = self.data_handling.get_mobility_chromatographic_data(query)

        return document, data, query

    def onChangePlot(self, evt):

        # Get selected item
        item = self.GetSelection()
        self._item_id = item
        # Get the current text value for selected item
        itemType = self.GetItemText(item)
        if itemType == "Documents":
            return

        # Get indent level for selected item
        indent = self.get_item_indent(item)
        if indent > 1:
            parent = self.getParentItem(item, 1)  # File name
            extract = item  # Specific Ion/file name
            item = self.getParentItem(item, 2)  # Item type
            itemType = self.GetItemText(item)
        else:
            extract = None
            parent = item

        # Get the ion/file name from deeper indent
        if extract is None:
            pass
        else:
            self._item_leaf = self.GetItemText(extract)

        # Check item
        if not item:
            return
        # Get item data for specified item
        self._document_data = self.GetPyData(parent)
        self._document_type = itemType

        self.on_show_plot(evt=None)

        if evt is not None:
            evt.Skip()

    def on_delete_all_documents(self, evt):
        """ Alternative function to delete documents """

        doc_keys = list(self.presenter.documentsDict.keys())
        n_docs = len(doc_keys)

        if not doc_keys:
            logger.warning("Document list is empty")
            return

        dlg = DialogBox(
            exceptionTitle="Are you sure?",
            exceptionMsg=f"Are you sure you would like to delete ALL ({n_docs}) documents?",
            type="Question",
        )

        if dlg == wx.ID_NO:
            self.presenter.onThreading(None, ("Cancelled operation", 4, 5), action="updateStatusbar")
            return

        # clear all plots
        self.panel_plot.on_clear_all_plots()

        # iterate over the list
        for document in doc_keys:
            try:
                self.removeDocument(evt=None, deleteItem=document, ask_permission=False)
            except Exception:
                logger.error(f"Encountered an error when deleting document: '{document}'.", exc_info=True)

    def _get_query_info_based_on_indent(self, return_subkey=False, evt=None):
        """Generate query_info keywords that are implied from the indentation of the selected item

        Parameters
        ----------
        return_subkey : bool, optional
            if True, returns the query_info item and associated subkey elements when indent is 4 and 5

        Returns
        -------
        query_info : list
            list of [document_title, dataset_type, dataset_name]

        """
        if self._document_data is None and evt is not None:
            self.on_item_selecting(evt)

        if self._document_data is not None:
            document_title = self._document_data.title

        item_type = self._document_type
        item_root = self._item_root
        item_branch = self._item_branch
        item_leaf = self._item_leaf

        subkey = ["", ""]

        if self._indent == 0:
            query = ["Documents", "", ""]
        elif self._indent == 1:
            query = [item_branch, item_leaf, item_leaf]
        elif self._indent == 2:
            query = [item_branch, item_leaf, item_leaf]
        elif self._indent == 3:
            # these are only valid when attached to `main` components of the document
            if item_leaf in ["Annotations", "UniDec"]:
                subkey = [item_leaf, ""]
                item_leaf = item_branch
            query = [item_root, item_branch, item_leaf]
        elif self._indent == 4:
            if item_leaf in ["Annotations", "UniDec"]:
                subkey = [item_leaf, ""]
            if item_branch in ["Annotations", "UniDec"]:
                subkey = [item_branch, item_leaf]
                item_branch = item_root
            query = [document_title, item_root, item_branch]
        elif self._indent == 5:
            query = [document_title, item_type, item_root]
            subkey = [item_branch, item_leaf]

        if return_subkey:
            return query, subkey

        return query

    def _get_delete_info_based_on_indent(self):
        """Generate query_info keywords that are implied from the indentation of the selected item and modify it to
        enable eaesier determination which items need to be fully deleted (eg. parent) or partial)

        Returns
        query_info : list
            list of [document_title, dataset_type, dataset_type]
        subkey : list
            list of [subkey_type, subkey_name]
        dataset_name : str
            dataset_name
        """
        query, subkey = self._get_query_info_based_on_indent(return_subkey=True)

        dataset_name = ""
        if self._indent in [3, 4, 5]:
            if query[1] != query[2]:
                dataset_name = query[2]
                query[2] = query[1]

        return query, subkey, dataset_name

    def _match_plot_type_to_dataset_type(self, dataset_type, dataset_name):
        _plot_match = {
            "mass_spectrum": ["Mass Spectrum", "Mass Spectrum (processed)", "Mass Spectra"],
            "chromatogram": ["Chromatogram", "Chromatograms (EIC)", "Chromatograms (combined voltages, EIC)"],
            "mobilogram": ["Drift time (1D)", "Drift time (1D, EIC)", "Drift time (1D, EIC, DT-IMS)"],
            "heatmap": ["Drift time (2D)", "Drift time (2D, EIC)", "Drift time (2D, combined voltages, EIC)"],
            "annotated": ["Multi-line:", "Line:", "H-bar:", "V-bar:", "Scatter:", "Waterfall:"],
        }
        for key, items in _plot_match.items():
            if dataset_type in items:
                return key
            elif any(ok_item in dataset_name for ok_item in items):
                return key
        raise MessageError("Failed to find appropriate method", "Failed to find appropriate method")

    def on_open_annotation_editor(self, evt):
        """Open annotations panel"""
        from origami.gui_elements.panel_peak_annotation_editor import PanelPeakAnnotationEditor

        if self._annotate_panel is not None:
            raise MessageError(
                "Window already open",
                "An instance of annotation window is already open. Please close it first before"
                + " opening another one.",
            )

        document_title, dataset_type, dataset_name = self._get_query_info_based_on_indent()
        # get data
        __, data = self.data_handling.get_mobility_chromatographic_data([document_title, dataset_type, dataset_name])
        plot_type = self._match_plot_type_to_dataset_type(dataset_type, dataset_name)

        # check plot_type has been specified
        if plot_type is None:
            raise MessageError("Not implemented yet", "Function not implemented for this dataset type")

        # reshape data
        if plot_type in ["mass_spectrum", "mobilogram", "chromatogram"]:
            data = np.transpose([data["xvals"], data["yvals"]])

        query = [document_title, dataset_type, dataset_name]
        kwargs = {
            "document_title": document_title,
            "dataset_type": dataset_type,
            "dataset_name": dataset_name,
            "data": data,
            "plot_type": plot_type,
            "annotations": self.data_handling.get_annotations_data(query),
            "query": query,
        }

        self._annotate_panel = PanelPeakAnnotationEditor(self.view, self, self.config, self.icons, **kwargs)
        self._annotate_panel.Show()

    def on_update_annotation(self, annotations, document_title, dataset_type, dataset_name, set_data_only=False):
        """
        Update annotations in specified document/dataset

        Parameters
        ----------
        annotations : dict
            dictionary with annotations
        document : str
            name of the document
        dataset_type : str
            type of the dataset
        dataset_name : str
            name of the dataset
        set_data_only : bool
            specify whether all annotations should be removed and readded or if
            we it should simply set data
        """
        # get dataset
        query_info = [document_title, dataset_type, dataset_name]
        __, dataset = self.data_handling.get_mobility_chromatographic_data(query_info, as_copy=False)

        # get pointer to dataset
        item = self.get_item_by_data(dataset)

        # update dataset with new annotations
        document = self.data_handling.set_mobility_chromatographic_keyword_data(query_info, annotations=annotations)

        # update elements in the document tree
        if item is not False and not set_data_only:
            self.add_one_to_group(item, annotations, "Annotations", image="annotation")
            self.data_handling.on_update_document(document, "no_refresh")
        else:
            self.data_handling.on_update_document(document, "no_refresh")

    def on_duplicate_annotations(self, evt):
        """Duplicate annotations from one object to another

        Parameters
        ----------
        evt : wxPython event
            unused
        """
        from origami.gui_elements.dialog_select_dataset import DialogSelectDataset

        # get data
        document_title, dataset_type, dataset_name = self._get_query_info_based_on_indent()
        __, data = self.data_handling.get_mobility_chromatographic_data([document_title, dataset_type, dataset_name])
        annotations = deepcopy(data.get("annotations", None))

        if annotations is None or len(annotations) == 0:
            raise MessageError("Annotations were not found", "This item has no annotations to duplicate")

        plot_type = self._match_plot_type_to_dataset_type(dataset_type, dataset_name)
        if plot_type == "annotated":
            raise MessageError(
                "Not supported yet", "Duplication of annotations from this data type is not yet supported"
            )

        document_spectrum_list = self.data_handling.generate_annotation_list(plot_type)
        document_list = list(document_spectrum_list.keys())

        document_spectrum_list[document_title].pop(
            document_spectrum_list[document_title].index(f"{dataset_type} :: {dataset_name}")
        )

        duplicateDlg = DialogSelectDataset(
            self.presenter.view, self, document_list, document_spectrum_list, set_document=document_title
        )
        duplicateDlg.ShowModal()
        duplicate_document = duplicateDlg.document
        duplicate_type = duplicateDlg.dataset

        if any(item is None for item in [duplicate_type, duplicate_document]):
            logger.warning("Duplicating annotations was cancelled")
            return

        # split dataset name
        duplicate_name = duplicate_type
        if "::" in duplicate_type:
            duplicate_type, duplicate_name = re.split(" :: ", duplicate_type)

        __, data = self.data_handling.get_mobility_chromatographic_data(
            [duplicate_document, duplicate_type, duplicate_name]
        )

        if data.get("annotations", dict()):
            dlg = DialogBox(
                exceptionTitle="Dataset already contains annotations",
                exceptionMsg="The selected dataset already contains annotations. Would you like"
                + " to continue and override present annotations?",
                type="Question",
            )
            if dlg == wx.ID_NO:
                logger.info("Cancelled adding annotations to a dataset")
                return

        # get dataset
        self.on_update_annotation(annotations, duplicate_document, duplicate_type, duplicate_name)

    def on_show_annotations(self, evt):
        """Show annotations in the currently shown mass spectrum

        Parameters
        ----------
        evt : wxPython event
            unused
        """
        # get data
        document_title, dataset_type, dataset_name = self._get_query_info_based_on_indent()
        __, data = self.data_handling.get_mobility_chromatographic_data([document_title, dataset_type, dataset_name])

        plot_type = self._match_plot_type_to_dataset_type(dataset_type, dataset_name)
        annotations_obj = data.get("annotations", {})
        if not annotations_obj:
            raise MessageError("Error", "This item has no annotations to display")

        self.panel_plot.on_plot_1D_annotations(
            annotations_obj,
            plot=plot_type,
            label_fmt="all",
            pin_to_intensity=True,
            document_title=document_title,
            dataset_type=dataset_type,
            dataset_name=dataset_name,
        )

    def on_action_ORIGAMI_MS(self, evt, document_title=None):
        from origami.gui_elements.dialog_customise_origami import DialogCustomiseORIGAMI

        # get document
        document = self.data_handling.on_get_document(document_title)
        if document.dataType != "Type: ORIGAMI":
            raise MessageError(
                "Incorrect document type", f"Cannot setup ORIGAMI-MS parameters for {document.dataType} document."
            )

        dlg = DialogCustomiseORIGAMI(self, self.presenter, self.config, document_title=document_title)
        dlg.ShowModal()

    #     def on_open_interactive_viewer(self, evt):
    #         from origami.gui_elements.panel_plot_viewer import PanelPlotViewer
    #
    #         # get data
    #         document_title, dataset_type, dataset_name = self._get_query_info_based_on_indent()
    #         __, data = self.data_handling.get_mobility_chromatographic_data([document_title, dataset_type,
    # dataset_name])
    #
    #         # initilize peak picker
    #         self._bokeh_panel = PanelPlotViewer(
    #             self.presenter.view,
    #             self.presenter,
    #             self.config,
    #             self.icons,
    #             mz_data=data,
    #             document_title=document_title,
    #             dataset_type=dataset_type,
    #             dataset_name=dataset_name,
    #         )
    #         self._bokeh_panel.Show()

    def on_open_overlay_viewer(self, evt):
        from origami.widgets.overlay.panel_overlay_viewer import PanelOverlayViewer

        self._overlay_panel = PanelOverlayViewer(self.view, self.presenter, self.config, self.icons)
        self._overlay_panel.Show()

    def on_open_lesa_viewer(self, evt):
        from origami.widgets.lesa.panel_imaging_lesa import PanelImagingLESAViewer

        self._lesa_panel = PanelImagingLESAViewer(self.view, self.presenter, self.config, self.icons)
        self._lesa_panel.Show()

    def on_import_lesa_dataset(self, evt):
        from origami.widgets.lesa.panel_imaging_lesa_import import PanelImagingImportDataset

        self._import_panel = PanelImagingImportDataset(self.view, self.presenter, self.config, self.icons)
        self._import_panel.Show()

    def _bind_change_label_events(self):
        for xID in [
            ID_xlabel_2D_scans,
            ID_xlabel_2D_colVolt,
            ID_xlabel_2D_actVolt,
            ID_xlabel_2D_labFrame,
            ID_xlabel_2D_actLabFrame,
            ID_xlabel_2D_massToCharge,
            ID_xlabel_2D_mz,
            ID_xlabel_2D_wavenumber,
            ID_xlabel_2D_restore,
            ID_xlabel_2D_ccs,
            ID_xlabel_2D_charge,
            ID_xlabel_2D_custom,
            ID_xlabel_2D_time_min,
            ID_xlabel_2D_retTime_min,
        ]:
            self.Bind(wx.EVT_MENU, self.on_change_xy_values_and_labels, id=xID)

        for yID in [
            ID_ylabel_2D_bins,
            ID_ylabel_2D_ms,
            ID_ylabel_2D_ms_arrival,
            ID_ylabel_2D_ccs,
            ID_ylabel_2D_restore,
            ID_ylabel_2D_custom,
        ]:
            self.Bind(wx.EVT_MENU, self.on_change_xy_values_and_labels, id=yID)

        # 1D
        for yID in [
            ID_xlabel_1D_bins,
            ID_xlabel_1D_ms,
            ID_xlabel_1D_ms_arrival,
            ID_xlabel_1D_ccs,
            ID_xlabel_1D_restore,
        ]:
            self.Bind(wx.EVT_MENU, self.on_change_xy_values_and_labels, id=yID)

        # RT
        for yID in [ID_xlabel_RT_scans, ID_xlabel_RT_time_min, ID_xlabel_RT_retTime_min, ID_xlabel_RT_restore]:
            self.Bind(wx.EVT_MENU, self.on_change_xy_values_and_labels, id=yID)

        # DT/MS
        for yID in [ID_ylabel_DTMS_bins, ID_ylabel_DTMS_ms, ID_ylabel_DTMS_ms_arrival, ID_ylabel_DTMS_restore]:
            self.Bind(wx.EVT_MENU, self.on_change_xy_values_and_labels, id=yID)

    def on_right_click_short(self):
        """Right-click menu when clicked on the `Documents` item in the documents tree"""

        # bind few events first
        self.Bind(wx.EVT_MENU, self.data_handling.on_save_all_documents_fcn, id=ID_saveAllDocuments)
        self.Bind(wx.EVT_MENU, self.on_delete_all_documents, id=ID_removeAllDocuments)

        menu = wx.Menu()
        menu.AppendItem(
            make_menu_item(
                parent=menu,
                id=ID_saveAllDocuments,
                text="Save all documents",
                bitmap=self.icons.iconsLib["save_multiple_16"],
            )
        )
        menu.AppendItem(
            make_menu_item(
                parent=menu, id=ID_removeAllDocuments, text="Delete all documents", bitmap=self.icons.iconsLib["bin16"]
            )
        )
        self.PopupMenu(menu)
        menu.Destroy()
        self.SetFocus()

    def on_update_ui(self, value, evt):
        if value == "menu.load.override":
            self.config.import_duplicate_ask = not self.config.import_duplicate_ask

    def on_right_click(self, evt):
        """ Create and show up popup menu"""

        # Get the current text value for selected item
        itemType = self.GetItemText(evt.GetItem())

        try:
            query, subkey = self._get_query_info_based_on_indent(return_subkey=True, evt=evt)
        except AttributeError:
            logger.debug(
                "Could not obtain right-click query key. Please first left-click on an item in " " the document tree"
            )
            return

        dataset_type = query[1]
        dataset_name = query[2]
        subkey_parent = subkey[0]
        subkey_child = subkey[1]

        if itemType == "Documents":
            self.on_right_click_short()
            return

        # Change x-axis label (2D)
        xlabel_2D_menu = wx.Menu()
        xlabel_2D_menu.Append(ID_xlabel_2D_scans, "Scans", "", wx.ITEM_RADIO)
        xlabel_2D_menu.Append(ID_xlabel_2D_time_min, "Time (min)", "", wx.ITEM_RADIO)
        xlabel_2D_menu.Append(ID_xlabel_2D_retTime_min, "Retention time (min)", "", wx.ITEM_RADIO)
        xlabel_2D_menu.Append(ID_xlabel_2D_colVolt, "Collision Voltage (V)", "", wx.ITEM_RADIO)
        xlabel_2D_menu.Append(ID_xlabel_2D_actVolt, "Activation Energy (V)", "", wx.ITEM_RADIO)
        xlabel_2D_menu.Append(ID_xlabel_2D_labFrame, "Lab Frame Energy (eV)", "", wx.ITEM_RADIO)
        xlabel_2D_menu.Append(ID_xlabel_2D_actLabFrame, "Activation Energy (eV)", "", wx.ITEM_RADIO)
        xlabel_2D_menu.Append(ID_xlabel_2D_massToCharge, "Mass-to-charge (Da)", "", wx.ITEM_RADIO)
        xlabel_2D_menu.Append(ID_xlabel_2D_mz, "m/z (Da)", "", wx.ITEM_RADIO)
        xlabel_2D_menu.Append(ID_xlabel_2D_wavenumber, "Wavenumber (cm⁻¹)", "", wx.ITEM_RADIO)
        xlabel_2D_menu.Append(ID_xlabel_2D_charge, "Charge", "", wx.ITEM_RADIO)
        xlabel_2D_menu.Append(ID_xlabel_2D_ccs, "Collision Cross Section (Å²)", "", wx.ITEM_RADIO)
        xlabel_2D_menu.Append(ID_xlabel_2D_custom, "Custom label...", "", wx.ITEM_RADIO)
        xlabel_2D_menu.AppendSeparator()
        xlabel_2D_menu.Append(ID_xlabel_2D_restore, "Restore default", "")

        # Change y-axis label (2D)
        ylabel_2D_menu = wx.Menu()
        ylabel_2D_menu.Append(ID_ylabel_2D_bins, "Drift time (bins)", "", wx.ITEM_RADIO)
        ylabel_2D_menu.Append(ID_ylabel_2D_ms, "Drift time (ms)", "", wx.ITEM_RADIO)
        ylabel_2D_menu.Append(ID_ylabel_2D_ms_arrival, "Arrival time (ms)", "", wx.ITEM_RADIO)
        ylabel_2D_menu.Append(ID_ylabel_2D_ccs, "Collision Cross Section (Å²)", "", wx.ITEM_RADIO)
        ylabel_2D_menu.Append(ID_ylabel_2D_custom, "Custom label...", "", wx.ITEM_RADIO)
        ylabel_2D_menu.AppendSeparator()
        ylabel_2D_menu.Append(ID_ylabel_2D_restore, "Restore default", "")

        # Check xy axis labels
        if self._document_type in [
            "Drift time (2D)",
            "Drift time (2D, processed)",
            "Drift time (2D, EIC)",
            "Drift time (2D, combined voltages, EIC)",
            "Drift time (2D, processed, EIC)",
            "Input data",
        ]:

            # Check what is the current label for this particular dataset
            try:
                idX, idY = self.on_check_xylabels_2D()
                xlabel_2D_menu.FindItemById(idX).Check(True)
                ylabel_2D_menu.FindItemById(idY).Check(True)
            except (UnboundLocalError, TypeError, KeyError):
                logger.warning(f"Failed to setup x/y labels for `{self._document_type}` item`")

        # Change x-axis label (1D)
        xlabel_1D_menu = wx.Menu()
        xlabel_1D_menu.Append(ID_xlabel_1D_bins, "Drift time (bins)", "", wx.ITEM_RADIO)
        xlabel_1D_menu.Append(ID_xlabel_1D_ms, "Drift time (ms)", "", wx.ITEM_RADIO)
        xlabel_1D_menu.Append(ID_xlabel_1D_ms_arrival, "Arrival time (ms)", "", wx.ITEM_RADIO)
        xlabel_1D_menu.Append(ID_xlabel_1D_ccs, "Collision Cross Section (Å²)", "", wx.ITEM_RADIO)
        xlabel_1D_menu.AppendSeparator()
        xlabel_1D_menu.Append(ID_xlabel_1D_restore, "Restore default", "")

        if self._document_type in ["Drift time (1D)", "Drift time (1D, EIC)"]:
            try:
                idX = self.on_check_xlabels_1D()
                xlabel_1D_menu.FindItemById(idX).Check(True)
            except (UnboundLocalError, TypeError, KeyError):
                logger.warning(f"Failed to setup labels for `{self._document_type}` item`")

        # Change x-axis label (RT)
        xlabel_RT_menu = wx.Menu()
        xlabel_RT_menu.Append(ID_xlabel_RT_scans, "Scans", "", wx.ITEM_RADIO)
        xlabel_RT_menu.Append(ID_xlabel_RT_time_min, "Time (min)", "", wx.ITEM_RADIO)
        xlabel_RT_menu.Append(ID_xlabel_RT_retTime_min, "Retention time (min)", "", wx.ITEM_RADIO)
        xlabel_RT_menu.AppendSeparator()
        xlabel_RT_menu.Append(ID_xlabel_RT_restore, "Restore default", "")

        if (self._document_type in ["Chromatogram"] and self._indent == 2) or (
            self._document_type in ["Chromatograms (EIC)", "Chromatograms (combined voltages, EIC)"]
            and self._indent > 2
        ):
            try:
                idX = self.on_check_xlabels_RT()
                xlabel_RT_menu.FindItemById(idX).Check(True)
            except (UnboundLocalError, TypeError, KeyError):
                logger.warning(f"Failed to setup labels for `{self._document_type}` item`")

        # change y-axis label (DT/MS)
        ylabel_DTMS_menu = wx.Menu()
        ylabel_DTMS_menu.Append(ID_ylabel_DTMS_bins, "Drift time (bins)", "", wx.ITEM_RADIO)
        ylabel_DTMS_menu.Append(ID_ylabel_DTMS_ms, "Drift time (ms)", "", wx.ITEM_RADIO)
        ylabel_DTMS_menu.Append(ID_ylabel_DTMS_ms_arrival, "Arrival time (ms)", "", wx.ITEM_RADIO)
        ylabel_DTMS_menu.AppendSeparator()
        ylabel_DTMS_menu.Append(ID_ylabel_DTMS_restore, "Restore default", "")

        if self._document_type == "DT/MS":
            try:
                idX = self.on_check_xlabels_DTMS()
                ylabel_DTMS_menu.FindItemById(idX).Check(True)
            except (UnboundLocalError, TypeError, KeyError):
                logger.warning(f"Failed to setup labels for `{self._document_type}` item`")

        action_menu = wx.Menu()
        action_menu.Append(ID_docTree_action_open_origami_ms, "Setup ORIGAMI-MS parameters...")
        action_menu.Append(ID_docTree_action_open_extract, "Open data extraction panel...")
        action_menu.Append(ID_docTree_action_open_extractDTMS, "Open DT/MS dataset settings...")

        # save dataframe
        save_data_submenu = wx.Menu()
        save_data_submenu.Append(ID_saveData_csv, "Save to .csv file")
        save_data_submenu.Append(ID_saveData_pickle, "Save to .pickle file")
        save_data_submenu.Append(ID_saveData_hdf, "Save to .hdf file (slow)")
        save_data_submenu.Append(ID_saveData_excel, "Save to .excel file (v. slow)")

        # Bind events
        self._bind_change_label_events()

        self.Bind(wx.EVT_MENU, self.on_show_plot, id=ID_showPlotDocument)
        self.Bind(wx.EVT_MENU, self.on_show_plot, id=ID_showPlotDocument_violin)
        self.Bind(wx.EVT_MENU, self.on_show_plot, id=ID_showPlotDocument_waterfall)
        self.Bind(wx.EVT_MENU, self.on_show_plot, id=ID_showPlot1DDocument)
        self.Bind(wx.EVT_MENU, self.on_show_plot, id=ID_showPlotRTDocument)
        self.Bind(wx.EVT_MENU, self.on_show_plot, id=ID_showPlotMSDocument)
        self.Bind(wx.EVT_MENU, self.onProcess, id=ID_process2DDocument)
        self.Bind(wx.EVT_MENU, self.onGoToDirectory, id=ID_goToDirectory)
        self.Bind(wx.EVT_MENU, self.onSaveCSV, id=ID_saveDataCSVDocument)
        self.Bind(wx.EVT_MENU, self.onSaveCSV, id=ID_saveDataCSVDocument1D)
        self.Bind(wx.EVT_MENU, self.onSaveCSV, id=ID_saveAsDataCSVDocument)
        self.Bind(wx.EVT_MENU, self.onSaveCSV, id=ID_saveAsDataCSVDocument1D)
        self.Bind(wx.EVT_MENU, self.onRenameItem, id=ID_renameItem)
        self.Bind(wx.EVT_MENU, self.onDuplicateItem, id=ID_duplicateItem)
        self.Bind(wx.EVT_MENU, self.on_save_document, id=ID_saveDocument)
        self.Bind(wx.EVT_MENU, self.onShowSampleInfo, id=ID_showSampleInfo)
        self.Bind(wx.EVT_MENU, self.view.on_open_interactive_output_panel, id=ID_saveAsInteractive)
        self.Bind(wx.EVT_MENU, self.on_open_spectrum_comparison_viewer, id=ID_docTree_compareMS)
        self.Bind(wx.EVT_MENU, self.onShowMassSpectra, id=ID_docTree_showMassSpectra)
        self.Bind(wx.EVT_MENU, self.onAddToTable, id=ID_docTree_addToMMLTable)
        self.Bind(wx.EVT_MENU, self.onAddToTable, id=ID_docTree_addOneToMMLTable)
        self.Bind(wx.EVT_MENU, self.onAddToTable, id=ID_docTree_addToTextTable)
        self.Bind(wx.EVT_MENU, self.onAddToTable, id=ID_docTree_addOneToTextTable)
        self.Bind(wx.EVT_MENU, self.onAddToTable, id=ID_docTree_addInteractiveToTextTable)
        self.Bind(wx.EVT_MENU, self.onAddToTable, id=ID_docTree_addOneInteractiveToTextTable)
        self.Bind(wx.EVT_MENU, self.onDuplicateItem, id=ID_docTree_duplicate_document)
        self.Bind(wx.EVT_MENU, self.on_refresh_document, id=ID_docTree_show_refresh_document)
        self.Bind(wx.EVT_MENU, self.removeDocument, id=ID_removeDocument)
        self.Bind(wx.EVT_MENU, self.onOpenDocInfo, id=ID_openDocInfo)
        self.Bind(wx.EVT_MENU, self.onShow_and_SavePlot, id=ID_saveRTImageDoc)
        self.Bind(wx.EVT_MENU, self.onShow_and_SavePlot, id=ID_save1DImageDoc)
        self.Bind(wx.EVT_MENU, self.onShow_and_SavePlot, id=ID_save2DImageDoc)
        self.Bind(wx.EVT_MENU, self.onShow_and_SavePlot, id=ID_save3DImageDoc)
        self.Bind(wx.EVT_MENU, self.on_process_UVPD, id=ID_docTree_plugin_UVPD)
        self.Bind(wx.EVT_MENU, self.onSaveDF, id=ID_saveData_csv)
        self.Bind(wx.EVT_MENU, self.onSaveDF, id=ID_saveData_pickle)
        self.Bind(wx.EVT_MENU, self.onSaveDF, id=ID_saveData_excel)
        self.Bind(wx.EVT_MENU, self.onSaveDF, id=ID_saveData_hdf)
        self.Bind(wx.EVT_MENU, self.on_open_UniDec, id=ID_docTree_show_unidec)
        self.Bind(wx.EVT_MENU, self.on_save_unidec_results, id=ID_docTree_save_unidec)
        self.Bind(wx.EVT_MENU, self.data_handling.on_add_mzID_file_fcn, id=ID_docTree_add_mzIdentML)
        self.Bind(wx.EVT_MENU, self.on_action_ORIGAMI_MS, id=ID_docTree_action_open_origami_ms)
        self.Bind(wx.EVT_MENU, self.on_open_extract_DTMS, id=ID_docTree_action_open_extractDTMS)
        self.Bind(wx.EVT_MENU, self.on_open_peak_picker, id=ID_docTree_action_open_peak_picker)
        self.Bind(wx.EVT_MENU, self.on_open_extract_data, id=ID_docTree_action_open_extract)
        self.Bind(wx.EVT_MENU, self.on_open_UniDec, id=ID_docTree_UniDec)

        # load custom data sub menu
        load_data_menu = wx.Menu()
        menu_action_load_ms = load_data_menu.Append(wx.ID_ANY, "Import mass spectrum")
        menu_action_load_rt = load_data_menu.Append(wx.ID_ANY, "Import chromatogram")
        menu_action_load_dt = load_data_menu.Append(wx.ID_ANY, "Import mobilogram")
        menu_action_load_heatmap = load_data_menu.Append(wx.ID_ANY, "Import heatmap")
        menu_action_load_matrix = load_data_menu.Append(wx.ID_ANY, "Import matrix")
        load_data_menu.AppendSeparator()
        menu_action_load_other = load_data_menu.Append(wx.ID_ANY, "Import data with metadata...")
        load_data_menu.AppendSeparator()
        menu_action_load_check_existing = load_data_menu.AppendCheckItem(wx.ID_ANY, "Don't check if file exists")
        menu_action_load_check_existing.Check(self.config.import_duplicate_ask)

        self.Bind(wx.EVT_MENU, partial(self.data_handling.on_load_custom_data, "mass_spectra"), menu_action_load_ms)
        self.Bind(wx.EVT_MENU, partial(self.data_handling.on_load_custom_data, "chromatograms"), menu_action_load_rt)
        self.Bind(wx.EVT_MENU, partial(self.data_handling.on_load_custom_data, "mobilograms"), menu_action_load_dt)
        self.Bind(wx.EVT_MENU, partial(self.data_handling.on_load_custom_data, "heatmaps"), menu_action_load_heatmap)
        self.Bind(wx.EVT_MENU, partial(self.data_handling.on_load_custom_data, "matrix"), menu_action_load_matrix)
        self.Bind(wx.EVT_MENU, partial(self.data_handling.on_load_custom_data, "annotated"), menu_action_load_other)
        self.Bind(wx.EVT_MENU, partial(self.on_update_ui, "menu.load.override"), menu_action_load_check_existing)

        # annotations sub menu
        annotation_menu = wx.Menu()
        annotation_menu_show_annotations_panel = make_menu_item(
            parent=annotation_menu, text="Show annotations panel...", bitmap=self.icons.iconsLib["annotate16"]
        )
        annotation_menu_show_annotations = make_menu_item(
            parent=annotation_menu, text="Show annotations on plot", bitmap=self.icons.iconsLib["highlight_16"]
        )
        annotation_menu_duplicate_annotations = make_menu_item(
            parent=annotation_menu, text="Duplicate annotations...", bitmap=self.icons.iconsLib["duplicate_item_16"]
        )

        annotation_menu.Append(annotation_menu_show_annotations_panel)
        annotation_menu.Append(annotation_menu_show_annotations)
        annotation_menu.Append(annotation_menu_duplicate_annotations)

        menu = wx.Menu()
        menu_show_annotations_panel = make_menu_item(
            parent=menu, text="Show annotations panel...", bitmap=self.icons.iconsLib["annotate16"]
        )
        menu_action_duplicate_annotations = make_menu_item(
            parent=menu, text="Duplicate annotations...", bitmap=self.icons.iconsLib["duplicate_item_16"]
        )
        menu_action_show_annotations = make_menu_item(
            parent=menu, text="Show annotations on plot", bitmap=self.icons.iconsLib["highlight_16"]
        )
        menu_show_comparison_panel = make_menu_item(
            parent=menu,
            id=ID_docTree_compareMS,
            text="Compare mass spectra...",
            bitmap=self.icons.iconsLib["compare_mass_spectra_16"],
        )
        menu_show_peak_picker_panel = make_menu_item(
            parent=menu,
            id=ID_docTree_action_open_peak_picker,
            text="Open peak picker...",
            bitmap=self.icons.iconsLib["highlight_16"],
        )
        menu_action_delete_item = make_menu_item(
            parent=menu, text="Delete item\tDelete", bitmap=self.icons.iconsLib["clear_16"]
        )
        menu_action_show_highlights = make_menu_item(
            parent=menu,
            id=ID_showPlotMSDocument,
            text="Highlight ion in mass spectrum\tAlt+X",
            bitmap=self.icons.iconsLib["zoom_16"],
        )

        menu_action_show_plot = make_menu_item(
            parent=menu, id=ID_showPlotDocument, text="Show plot\tAlt+S", bitmap=self.icons.iconsLib["blank_16"]
        )
        menu_action_show_plot_spectrum = make_menu_item(
            parent=menu,
            id=ID_showPlotDocument,
            text="Show mass spectrum\tAlt+S",
            bitmap=self.icons.iconsLib["mass_spectrum_16"],
        )
        menu_action_show_plot_spectrum_waterfall = make_menu_item(
            parent=menu, id=ID_docTree_showMassSpectra, text="Show mass spectra (waterfall)", bitmap=None
        )
        menu_action_show_plot_mobilogram = make_menu_item(
            parent=menu,
            id=ID_showPlotDocument,
            text="Show mobilogram\tAlt+S",
            bitmap=self.icons.iconsLib["mobilogram_16"],
        )
        menu_action_show_plot_chromatogram = make_menu_item(
            parent=menu,
            id=ID_showPlotDocument,
            text="Show chromatogram\tAlt+S",
            bitmap=self.icons.iconsLib["chromatogram_16"],
        )
        menu_action_show_plot_2D = make_menu_item(
            parent=menu, id=ID_showPlotDocument, text="Show heatmap\tAlt+S", bitmap=self.icons.iconsLib["heatmap_16"]
        )
        menu_action_show_plot_violin = make_menu_item(
            parent=menu,
            id=ID_showPlotDocument_violin,
            text="Show violin plot",
            bitmap=self.icons.iconsLib["panel_violin_16"],
        )
        menu_action_show_plot_waterfall = make_menu_item(
            parent=menu,
            id=ID_showPlotDocument_waterfall,
            text="Show waterfall plot",
            bitmap=self.icons.iconsLib["panel_waterfall_16"],
        )

        menu_action_show_plot_as_mobilogram = make_menu_item(
            parent=menu, id=ID_showPlot1DDocument, text="Show mobilogram", bitmap=self.icons.iconsLib["mobilogram_16"]
        )

        menu_action_show_plot_as_chromatogram = make_menu_item(
            parent=menu,
            id=ID_showPlotRTDocument,
            text="Show chromatogram",
            bitmap=self.icons.iconsLib["chromatogram_16"],
        )

        menu_action_rename_item = make_menu_item(
            parent=menu, id=ID_renameItem, text="Rename\tF2", bitmap=self.icons.iconsLib["rename_16"]
        )

        menu_action_process_ms = make_menu_item(
            parent=menu, text="Process...\tP", bitmap=self.icons.iconsLib["process_ms_16"]
        )
        menu_action_process_ms_all = make_menu_item(
            parent=menu, text="Process all...", bitmap=self.icons.iconsLib["process_ms_16"]
        )
        menu_action_process_2D = make_menu_item(
            parent=menu, text="Process...\tP", bitmap=self.icons.iconsLib["process_2d_16"]
        )
        menu_action_process_2D_all = make_menu_item(
            parent=menu, text="Process all...\tP", bitmap=self.icons.iconsLib["process_2d_16"]
        )

        menu_action_assign_charge = make_menu_item(
            parent=menu, text="Assign charge state...\tAlt+Z", bitmap=self.icons.iconsLib["assign_charge_16"]
        )

        menu_show_unidec_panel = make_menu_item(
            parent=menu,
            id=ID_docTree_UniDec,
            text="Deconvolute using UniDec...",
            bitmap=self.icons.iconsLib["process_unidec_16"],
        )
        menu_action_add_spectrum_to_panel = make_menu_item(
            parent=menu, id=ID_docTree_addOneToMMLTable, text="Add spectrum to multiple files panel", bitmap=None
        )
        menu_action_show_unidec_results = make_menu_item(
            parent=menu, id=ID_docTree_show_unidec, text="Show UniDec results", bitmap=None
        )
        menu_action_save_mobilogram_image_as = make_menu_item(
            parent=menu, id=ID_save1DImageDoc, text="Save image as...", bitmap=self.icons.iconsLib["file_png_16"]
        )

        menu_action_save_heatmap_image_as = make_menu_item(
            parent=menu, id=ID_save2DImageDoc, text="Save image as...", bitmap=self.icons.iconsLib["file_png_16"]
        )

        menu_action_save_image_as = make_menu_item(
            parent=menu, text="Save image as...", bitmap=self.icons.iconsLib["file_png_16"]
        )

        menu_action_save_data_as = make_menu_item(
            parent=menu, id=ID_saveDataCSVDocument, text="Save data as...", bitmap=self.icons.iconsLib["file_csv_16"]
        )

        menu_action_save_1D_data_as = make_menu_item(
            parent=menu,
            id=ID_saveDataCSVDocument1D,
            text="Save 1D data as...",
            bitmap=self.icons.iconsLib["file_csv_16"],
        )

        menu_action_save_2D_data_as = make_menu_item(
            parent=menu, id=ID_saveDataCSVDocument, text="Save 2D data as...", bitmap=self.icons.iconsLib["file_csv_16"]
        )
        menu_action_save_chromatogram_image_as = make_menu_item(
            parent=menu, id=ID_saveRTImageDoc, text="Save image as...", bitmap=self.icons.iconsLib["file_png_16"]
        )

        menu_action_save_document = make_menu_item(
            parent=menu, id=ID_saveDocument, text="Save document\tCtrl+S", bitmap=self.icons.iconsLib["pickle_16"]
        )

        menu_action_save_document_as = make_menu_item(
            parent=menu, text="Save document as...", bitmap=self.icons.iconsLib["save16"]
        )

        # bind events
        self.Bind(wx.EVT_MENU, self.on_open_annotation_editor, annotation_menu_show_annotations_panel)
        self.Bind(wx.EVT_MENU, self.on_open_annotation_editor, menu_show_annotations_panel)
        self.Bind(wx.EVT_MENU, self.on_show_annotations, annotation_menu_show_annotations)
        self.Bind(wx.EVT_MENU, self.on_show_annotations, menu_action_show_annotations)
        self.Bind(wx.EVT_MENU, self.on_duplicate_annotations, annotation_menu_duplicate_annotations)
        self.Bind(wx.EVT_MENU, self.on_duplicate_annotations, menu_action_duplicate_annotations)
        self.Bind(wx.EVT_MENU, self.on_delete_item, menu_action_delete_item)
        self.Bind(wx.EVT_MENU, self.on_save_document_as, menu_action_save_document_as)
        self.Bind(wx.EVT_MENU, self.on_change_charge_state, menu_action_assign_charge)
        self.Bind(wx.EVT_MENU, self.on_process_MS, menu_action_process_ms)
        self.Bind(wx.EVT_MENU, self.on_process_MS_all, menu_action_process_ms_all)
        self.Bind(wx.EVT_MENU, self.on_process_2D, menu_action_process_2D)
        self.Bind(wx.EVT_MENU, self.on_process_all_2D, menu_action_process_2D_all)
        self.Bind(wx.EVT_MENU, self.onShow_and_SavePlot, menu_action_save_image_as)

        all_mass_spectra = ["Mass Spectrum", "Mass Spectrum (processed)", "Mass Spectra"]
        all_heatmaps = [
            "Drift time (2D)",
            "Drift time (2D, processed)",
            "Drift time (2D, EIC)",
            "Drift time (2D, combined voltages, EIC)",
            "Drift time (2D, processed, EIC)",
        ]
        heatmap_multi = [
            "Drift time (2D, EIC)",
            "Drift time (2D, combined voltages, EIC)",
            "Drift time (2D, processed, EIC)",
        ]
        accepted_annotated_items = ["Multi-line:", "Line:", "H-bar:", "V-bar:", "Scatter:", "Waterfall:"]

        # mass spectra
        if dataset_type in all_mass_spectra:
            # annotations - all
            if (self._document_type in all_mass_spectra) and subkey_parent == "Annotations":
                menu.AppendItem(menu_show_annotations_panel)
                menu.AppendItem(menu_action_show_annotations)
                menu.AppendItem(menu_action_duplicate_annotations)
                menu.AppendItem(menu_action_delete_item)
            # unidec -all
            elif dataset_type in all_mass_spectra and subkey_parent == "UniDec" and subkey_child != "":
                menu.AppendItem(
                    make_menu_item(
                        parent=menu, id=ID_docTree_show_unidec, text="Show plot - {}".format(self._item_leaf)
                    )
                )
                menu.AppendItem(
                    make_menu_item(
                        parent=menu,
                        id=ID_docTree_save_unidec,
                        text="Save results - {} ({})".format(self._item_leaf, self.config.saveExtension),
                    )
                )
                menu.AppendItem(menu_action_delete_item)
            # unidec - single
            elif dataset_type in all_mass_spectra and subkey_parent == "UniDec":
                menu.AppendItem(menu_action_show_unidec_results)
                menu.AppendItem(
                    make_menu_item(
                        parent=menu,
                        id=ID_docTree_save_unidec,
                        text="Save UniDec results ({})".format(self.config.saveExtension),
                    )
                )
                menu.AppendItem(menu_action_delete_item)
            # mass spectrum - single
            elif dataset_type in ["Mass Spectrum", "Mass Spectrum (processed)"] and self._indent == 2:
                menu.AppendItem(menu_action_show_plot_spectrum)
                menu.AppendItem(menu_show_peak_picker_panel)
                menu.AppendItem(menu_action_process_ms)
                menu.AppendItem(menu_show_comparison_panel)
                menu.AppendSubMenu(annotation_menu, "Annotations...")
                menu.AppendItem(menu_show_unidec_panel)
                menu.AppendSeparator()
                menu.AppendItem(menu_action_save_image_as)
                menu.AppendItem(menu_action_save_data_as)
                menu.AppendItem(menu_action_delete_item)
            # mass spectra
            else:
                # mass spectra - all
                if dataset_type == "Mass Spectra" and dataset_name == "Mass Spectra":
                    menu.AppendItem(menu_show_comparison_panel)
                    menu.AppendItem(menu_action_show_plot_spectrum_waterfall)
                    menu.AppendItem(
                        make_menu_item(
                            parent=menu,
                            id=ID_docTree_addToMMLTable,
                            text="Add spectra to multiple files panel",
                            bitmap=None,
                        )
                    )
                    menu.AppendItem(menu_action_process_ms_all)
                    menu.AppendSeparator()
                    menu.AppendItem(menu_action_save_data_as)
                    menu.AppendMenu(wx.ID_ANY, "Save to file...", save_data_submenu)
                # mass spectra - single
                else:
                    menu.AppendItem(menu_action_show_plot_spectrum)
                    menu.AppendItem(menu_show_peak_picker_panel)
                    menu.AppendItem(menu_action_process_ms)
                    menu.AppendSubMenu(annotation_menu, "Annotations...")
                    menu.AppendItem(menu_show_unidec_panel)
                    menu.AppendSeparator()
                    menu.AppendItem(menu_action_add_spectrum_to_panel)
                    menu.Append(ID_duplicateItem, "Duplicate item")
                    menu.AppendItem(menu_action_rename_item)
                    menu.AppendSeparator()
                    menu.AppendItem(menu_action_save_image_as)
                    menu.AppendItem(menu_action_save_data_as)
                menu.AppendItem(menu_action_delete_item)

        # tandem MS
        elif itemType == "Tandem Mass Spectra" and self._indent == 2:
            menu.AppendItem(
                make_menu_item(
                    parent=menu,
                    id=ID_docTree_add_mzIdentML,
                    text="Add identification information (.mzIdentML, .mzid, .mzid.gz)",
                    bitmap=None,
                )
            )
        # Sample information
        elif itemType == "Sample information":
            menu.Append(ID_showSampleInfo, "Show sample information")

        # chromatograms - all
        elif itemType == "Chromatogram":
            if self._indent == 2:
                menu.AppendItem(menu_action_show_plot_chromatogram)
                menu.AppendSubMenu(annotation_menu, "Annotations...")
                menu.AppendSeparator()
                menu.AppendMenu(wx.ID_ANY, "Change x-axis to...", xlabel_RT_menu)
                menu.AppendSeparator()
                menu.AppendItem(menu_action_save_chromatogram_image_as)
                menu.AppendItem(menu_action_save_data_as)
            elif self._indent == 3:
                menu.AppendItem(menu_show_annotations_panel)
                menu.AppendItem(menu_action_show_annotations)
                menu.AppendItem(menu_action_duplicate_annotations)
            menu.AppendItem(menu_action_delete_item)
        # chromatograms - eic
        elif self._document_type in ["Chromatograms (combined voltages, EIC)", "Chromatograms (EIC)"]:
            # Only if clicked on an item and not header
            if self._item_leaf not in ["Chromatograms (combined voltages, EIC)", "Chromatograms (EIC)"]:
                menu.AppendItem(menu_action_show_plot_chromatogram)
                menu.AppendSubMenu(annotation_menu, "Annotations...")
                menu.AppendSeparator()
                menu.AppendItem(menu_action_assign_charge)
                menu.AppendSeparator()
                menu.Append(ID_saveRTImageDoc, "Save image as...")
            menu.AppendItem(menu_action_save_data_as)
            menu.AppendItem(menu_action_delete_item)

        # drift time 1D - single
        elif itemType == "Drift time (1D)":
            if self._indent == 2:
                menu.AppendItem(menu_action_show_plot_mobilogram)
                menu.AppendSubMenu(annotation_menu, "Annotations...")
                menu.AppendSeparator()
                menu.AppendMenu(wx.ID_ANY, "Change x-axis to...", xlabel_1D_menu)
                menu.AppendSeparator()
                menu.AppendItem(menu_action_save_mobilogram_image_as)
                menu.AppendItem(menu_action_save_data_as)
            elif self._indent == 3:
                menu.AppendItem(menu_show_annotations_panel)
                menu.AppendItem(menu_action_show_annotations)
                menu.AppendItem(menu_action_duplicate_annotations)
            menu.AppendItem(menu_action_delete_item)
        # drift time 1D - eic
        elif self._document_type in ["Drift time (1D, EIC, DT-IMS)", "Drift time (1D, EIC)"]:
            # Only if clicked on an item and not header
            if self._item_leaf != "Drift time (1D, EIC, DT-IMS)" and itemType != "Drift time (1D, EIC)":
                menu.AppendItem(menu_action_show_highlights)

            if self._item_leaf not in ["Drift time (1D, EIC)", "Drift time (1D, EIC, DT-IMS)"]:
                menu.AppendItem(menu_action_show_plot_mobilogram)
                menu.AppendSubMenu(annotation_menu, "Annotations...")
                menu.AppendSeparator()
                menu.AppendMenu(wx.ID_ANY, "Change x-axis to...", xlabel_1D_menu)
                menu.AppendItem(menu_action_assign_charge)
                menu.AppendSeparator()
                menu.AppendItem(menu_action_save_mobilogram_image_as)
            menu.AppendItem(menu_action_save_data_as)
            menu.AppendItem(menu_action_delete_item)

        # heatmap - 2D
        elif self._document_type in all_heatmaps:
            # heatmap - single
            if (
                (self._document_type in ["Drift time (2D)", "Drift time (2D, processed)"])
                or (self._document_type in heatmap_multi and self._item_leaf != self._document_type)
                and (self._item_leaf != "Annotations" and self._item_branch != "Annotations")
            ):
                if self._item_leaf == "Annotations":
                    menu.AppendItem(menu_show_annotations_panel)
                    menu.AppendItem(menu_action_show_annotations)
                    menu.AppendItem(menu_action_duplicate_annotations)
                else:
                    menu.AppendItem(menu_action_show_plot_2D)
                    menu.AppendItem(menu_action_show_plot_violin)
                    menu.AppendItem(menu_action_show_plot_waterfall)
                    menu.AppendItem(menu_action_process_2D)
                    menu.AppendSeparator()
                    menu.AppendSubMenu(annotation_menu, "Annotations...")
                    menu.AppendItem(menu_action_assign_charge)
                    menu.AppendMenu(wx.ID_ANY, "Set X-axis label as...", xlabel_2D_menu)
                    menu.AppendMenu(wx.ID_ANY, "Set Y-axis label as...", ylabel_2D_menu)
                    menu.AppendSeparator()
                    menu.AppendItem(menu_action_save_heatmap_image_as)
                    menu.AppendItem(menu_action_save_1D_data_as)
                    menu.AppendItem(menu_action_save_2D_data_as)
                if self._document_type not in ["Drift time (2D)", "Drift time (2D, processed)"]:
                    menu.PrependItem(menu_action_show_plot_as_mobilogram)
                    menu.PrependItem(menu_action_show_plot_as_chromatogram)
                    menu.PrependItem(menu_action_show_highlights)
            elif self._item_leaf == "Annotations":
                menu.AppendItem(menu_show_annotations_panel)
                menu.AppendItem(menu_action_show_annotations)
                menu.AppendItem(menu_action_duplicate_annotations)
            # heatmap - all
            else:
                menu.AppendItem(menu_action_process_2D_all)
                menu.AppendSeparator()
                menu.AppendItem(menu_action_save_1D_data_as)
                menu.AppendItem(menu_action_save_2D_data_as)
            menu.AppendItem(menu_action_delete_item)
        # input data
        elif self._document_type == "Input data":
            # input data - all
            if self._document_type == "Input data" and self._item_leaf != self._document_type:
                menu.AppendItem(menu_action_show_plot_2D)
                menu.AppendItem(menu_action_process_2D)
                menu.AppendSeparator()
                menu.AppendMenu(wx.ID_ANY, "Set X-axis label as...", xlabel_2D_menu)
                menu.AppendMenu(wx.ID_ANY, "Set Y-axis label as...", ylabel_2D_menu)
                menu.AppendItem(menu_action_save_heatmap_image_as)
            # single and all
            menu.AppendItem(menu_action_save_data_as)
            menu.AppendItem(menu_action_delete_item)

        # statistical method
        elif self._document_type == "Statistical":
            # Only if clicked on an item and not header
            if self._item_leaf != self._document_type:
                menu.AppendItem(menu_action_show_plot_2D)
                menu.AppendSeparator()
                menu.AppendItem(menu_action_save_image_as)
                menu.AppendItem(menu_action_save_data_as)
                menu.AppendItem(menu_action_delete_item)
                menu.AppendSeparator()
                menu.AppendItem(menu_action_rename_item)
            # Only if on a header
            else:
                menu.AppendItem(menu_action_save_data_as)
                menu.AppendItem(menu_action_delete_item)

        # overlay
        elif self._document_type == "Overlay":
            plot_type = self.splitText[0]
            if self._document_type != self._item_leaf:
                if plot_type in [
                    "Waterfall (Raw)",
                    "Waterfall (Processed)",
                    "Waterfall (Fitted)",
                    "Waterfall (Deconvoluted MW)",
                    "Waterfall (Charge states)",
                ]:
                    menu.AppendItem(menu_action_show_plot)
                    if plot_type in ["Waterfall (Raw)", "Waterfall (Processed)"]:
                        menu.AppendItem(menu_show_annotations_panel)
                else:
                    menu.AppendItem(menu_action_show_plot)
                menu.AppendSeparator()
                if self.splitText[0] in [
                    "Waterfall (Raw)",
                    "Waterfall (Processed)",
                    "Waterfall (Fitted)",
                    "Waterfall (Deconvoluted MW)",
                    "Waterfall (Charge states)",
                ]:
                    menu.Append(ID_saveWaterfallImageDoc, "Save image as...")
                else:
                    menu.AppendItem(menu_action_save_image_as)
                menu.AppendItem(menu_action_delete_item)
                menu.AppendSeparator()
                menu.AppendItem(menu_action_rename_item)
            else:
                menu.AppendItem(menu_action_delete_item)
        # dt-ms
        elif itemType == "DT/MS":
            menu.AppendItem(menu_action_show_plot_2D)
            menu.AppendItem(menu_action_process_2D)
            menu.AppendSeparator()
            menu.AppendItem(
                make_menu_item(
                    parent=menu,
                    id=ID_docTree_action_open_extractDTMS,
                    text="Open DT/MS extraction panel...",
                    bitmap=None,
                )
            )
            menu.AppendSeparator()
            menu.AppendMenu(wx.ID_ANY, "Set Y-axis label as...", ylabel_DTMS_menu)
            menu.AppendSeparator()
            menu.AppendItem(menu_action_save_image_as)
            menu.AppendItem(menu_action_save_data_as)
        # annotated data
        elif dataset_type == "Annotated data":
            if dataset_type == dataset_name:
                menu.AppendMenu(wx.ID_ANY, "Import data...", load_data_menu)
            else:
                menu.AppendItem(menu_action_show_plot)
                if dataset_type != dataset_name and any(
                    [ok_item in dataset_name for ok_item in accepted_annotated_items]
                ):
                    menu.AppendSubMenu(annotation_menu, "Annotations...")
                menu.AppendSeparator()
                menu.AppendItem(menu_action_save_image_as)
                menu.AppendItem(menu_action_delete_item)
        else:
            menu.AppendMenu(wx.ID_ANY, "Import data...", load_data_menu)

        if menu.MenuItemCount > 0:
            menu.AppendSeparator()

        if self._indent == 1:
            menu.Append(ID_docTree_show_refresh_document, "Refresh document")
            menu.AppendItem(
                make_menu_item(
                    parent=menu,
                    id=ID_docTree_duplicate_document,
                    text="Duplicate document\tShift+D",
                    bitmap=self.icons.iconsLib["duplicate_16"],
                )
            )
            menu.AppendItem(menu_action_rename_item)
            menu.AppendSeparator()
        menu.AppendMenu(wx.ID_ANY, "Action...", action_menu)
        menu.AppendSeparator()
        menu.AppendItem(
            make_menu_item(
                parent=menu,
                id=ID_openDocInfo,
                text="Notes, Information, Labels...\tCtrl+I",
                bitmap=self.icons.iconsLib["info16"],
            )
        )
        menu.AppendItem(
            make_menu_item(
                parent=menu,
                id=ID_goToDirectory,
                text="Go to folder...\tCtrl+G",
                bitmap=self.icons.iconsLib["folder_path_16"],
            )
        )
        menu.AppendItem(
            make_menu_item(
                parent=menu,
                id=ID_saveAsInteractive,
                text="Open interactive output panel...\tShift+Z",
                bitmap=self.icons.iconsLib["bokehLogo_16"],
            )
        )
        menu.AppendItem(menu_action_save_document)
        menu.AppendItem(menu_action_save_document_as)

        menu.AppendSeparator()
        menu.AppendItem(
            make_menu_item(
                parent=menu, id=ID_removeDocument, text="Delete document", bitmap=self.icons.iconsLib["bin16"]
            )
        )

        self.PopupMenu(menu)
        menu.Destroy()
        self.SetFocus()

    # TODO: FIXME
    def on_change_xy_values_and_labels(self, evt):
        """Change xy-axis labels"""

        # Get current document info
        document_title, selectedItem, selectedText = self.on_enable_document(getSelected=True)
        indent = self.get_item_indent(selectedItem)
        selectedItemParentText = None
        if indent > 2:
            __, selectedItemParentText = self.getParentItem(selectedItem, 2, getSelected=True)
        else:
            pass
        document = self.presenter.documentsDict[document_title]

        # get event
        evtID = evt.GetId()

        # Determine which dataset is used
        if selectedText is None:
            data = document.IMS2D
        elif selectedText == "Drift time (2D)":
            data = document.IMS2D
        elif selectedText == "Drift time (2D, processed)":
            data = document.IMS2Dprocess
        elif selectedItemParentText == "Drift time (2D, EIC)" and selectedText is not None:
            data = document.IMS2Dions[selectedText]
        elif selectedItemParentText == "Drift time (2D, combined voltages, EIC)" and selectedText is not None:
            data = document.IMS2DCombIons[selectedText]
        elif selectedItemParentText == "Drift time (2D, processed, EIC)" and selectedText is not None:
            data = document.IMS2DionsProcess[selectedText]
        elif selectedItemParentText == "Input data" and selectedText is not None:
            data = document.IMS2DcompData[selectedText]

        # 1D data
        elif selectedText == "Drift time (1D)":
            data = document.DT
        elif selectedItemParentText == "Drift time (1D, EIC)" and selectedText is not None:
            data = document.multipleDT[selectedText]

        # chromatograms
        elif selectedText == "Chromatogram":
            data = document.RT
        elif selectedItemParentText == "Chromatograms (EIC)" and selectedText is not None:
            data = document.multipleRT[selectedText]
        elif selectedItemParentText == "Chromatograms (combined voltages, EIC)" and selectedText is not None:
            data = document.IMSRTCombIons[selectedText]

        # DTMS
        elif selectedText == "DT/MS":
            data = document.DTMZ

        # try to get dataset object
        try:
            docItem = self.get_item_by_data(data)
        except Exception:
            docItem = False

        # Add default values
        if "defaultX" not in data:
            data["defaultX"] = {"xlabels": data["xlabels"], "xvals": data["xvals"]}
        if "defaultY" not in data:
            data["defaultY"] = {"ylabels": data.get("ylabels", "Intensity"), "yvals": data["yvals"]}

        # If either label is none, then ignore it
        newXlabel, newYlabel = None, None
        restoreX, restoreY = False, False

        # Determine what the new label should be
        if evtID in [
            ID_xlabel_2D_scans,
            ID_xlabel_2D_colVolt,
            ID_xlabel_2D_actVolt,
            ID_xlabel_2D_labFrame,
            ID_xlabel_2D_massToCharge,
            ID_xlabel_2D_actLabFrame,
            ID_xlabel_2D_massToCharge,
            ID_xlabel_2D_mz,
            ID_xlabel_2D_wavenumber,
            ID_xlabel_2D_wavenumber,
            ID_xlabel_2D_custom,
            ID_xlabel_2D_charge,
            ID_xlabel_2D_ccs,
            ID_xlabel_2D_retTime_min,
            ID_xlabel_2D_time_min,
            ID_xlabel_2D_restore,
        ]:

            # If changing X-labels
            newXlabel = "Scans"
            restoreX = False
            if evtID == ID_xlabel_2D_scans:
                newXlabel = "Scans"
            elif evtID == ID_xlabel_2D_time_min:
                newXlabel = "Time (min)"
            elif evtID == ID_xlabel_2D_retTime_min:
                newXlabel = "Retention time (min)"
            elif evtID == ID_xlabel_2D_colVolt:
                newXlabel = "Collision Voltage (V)"
            elif evtID == ID_xlabel_2D_actVolt:
                newXlabel = "Activation Voltage (V)"
            elif evtID == ID_xlabel_2D_labFrame:
                newXlabel = "Lab Frame Energy (eV)"
            elif evtID == ID_xlabel_2D_actLabFrame:
                newXlabel = "Activation Energy (eV)"
            elif evtID == ID_xlabel_2D_massToCharge:
                newXlabel = "Mass-to-charge (Da)"
            elif evtID == ID_xlabel_2D_mz:
                newXlabel = "m/z (Da)"
            elif evtID == ID_xlabel_2D_wavenumber:
                newXlabel = "Wavenumber (cm⁻¹)"
            elif evtID == ID_xlabel_2D_charge:
                newXlabel = "Charge"
            elif evtID == ID_xlabel_2D_ccs:
                newXlabel = "Collision Cross Section (Å²)"
            elif evtID == ID_xlabel_2D_custom:
                newXlabel = DialogSimpleAsk("Please type in your new label...")
            elif evtID == ID_xlabel_2D_restore:
                newXlabel = data["defaultX"]["xlabels"]
                restoreX = True
            elif newXlabel == "" or newXlabel is None:
                newXlabel = "Scans"

        if evtID in [
            ID_ylabel_2D_bins,
            ID_ylabel_2D_ms,
            ID_ylabel_2D_ms_arrival,
            ID_ylabel_2D_ccs,
            ID_ylabel_2D_restore,
            ID_ylabel_2D_custom,
        ]:
            # If changing Y-labels
            newYlabel = "Drift time (bins)"
            restoreY = False
            if evtID == ID_ylabel_2D_bins:
                newYlabel = "Drift time (bins)"
            elif evtID == ID_ylabel_2D_ms:
                newYlabel = "Drift time (ms)"
            elif evtID == ID_ylabel_2D_ms_arrival:
                newYlabel = "Arrival time (ms)"
            elif evtID == ID_ylabel_2D_ccs:
                newYlabel = "Collision Cross Section (Å²)"
            elif evtID == ID_ylabel_2D_custom:
                newYlabel = DialogSimpleAsk("Please type in your new label...")
            elif evtID == ID_ylabel_2D_restore:
                newYlabel = data["defaultY"]["ylabels"]
                restoreY = True
            elif newYlabel == "" or newYlabel is None:
                newYlabel = "Drift time (bins)"

        # 1D data
        if evtID in [
            ID_xlabel_1D_bins,
            ID_xlabel_1D_ms,
            ID_xlabel_1D_ms_arrival,
            ID_xlabel_1D_ccs,
            ID_xlabel_1D_restore,
        ]:
            newXlabel = "Drift time (bins)"
            restoreX = False
            if evtID == ID_xlabel_1D_bins:
                newXlabel = "Drift time (bins)"
            elif evtID == ID_xlabel_1D_ms:
                newXlabel = "Drift time (ms)"
            elif evtID == ID_xlabel_1D_ms_arrival:
                newXlabel = "Arrival time (ms)"
            elif evtID == ID_xlabel_1D_ccs:
                newXlabel = "Collision Cross Section (Å²)"
            elif evtID == ID_xlabel_1D_restore:
                newXlabel = data["defaultX"]["xlabels"]
                restoreX = True

        # 1D data
        if evtID in [ID_xlabel_RT_scans, ID_xlabel_RT_time_min, ID_xlabel_RT_retTime_min, ID_xlabel_RT_restore]:
            newXlabel = "Drift time (bins)"
            restoreX = False
            if evtID == ID_xlabel_RT_scans:
                newXlabel = "Scans"
            elif evtID == ID_xlabel_RT_time_min:
                newXlabel = "Time (min)"
            elif evtID == ID_xlabel_RT_retTime_min:
                newXlabel = "Retention time (min)"
            elif evtID == ID_xlabel_RT_restore:
                newXlabel = data["defaultX"]["xlabels"]
                restoreX = True

        # DT/MS
        if evtID in [ID_ylabel_DTMS_bins, ID_ylabel_DTMS_ms, ID_ylabel_DTMS_ms_arrival, ID_ylabel_DTMS_restore]:
            newYlabel = "Drift time (bins)"
            restoreX = False
            if evtID == ID_ylabel_DTMS_bins:
                newYlabel = "Drift time (bins)"
            elif evtID == ID_ylabel_DTMS_ms:
                newYlabel = "Drift time (ms)"
            elif evtID == ID_ylabel_DTMS_ms_arrival:
                newYlabel = "Arrival time (ms)"
            elif evtID == ID_ylabel_DTMS_restore:
                newYlabel = data["defaultY"]["ylabels"]
                restoreY = True
            elif newYlabel == "" or newYlabel is None:
                newYlabel = "Drift time (bins)"

        if restoreX:
            newXvals = data["defaultX"]["xvals"]
            data["xvals"] = newXvals
            data["xlabels"] = newXlabel

        if restoreY:
            newYvals = data["defaultY"]["yvals"]
            data["yvals"] = newYvals
            data["ylabels"] = newYlabel

        # Change labels
        if newXlabel is not None:
            oldXLabel = data["xlabels"]
            data["xlabels"] = newXlabel  # Set new x-label
            newXvals = self.on_change_xy_axis(
                data["xvals"],
                oldXLabel,
                newXlabel,
                charge=data.get("charge", 1),
                pusherFreq=document.parameters.get("pusherFreq", 1000),
                scanTime=document.parameters.get("scanTime", 1.0),
                defaults=data["defaultX"],
            )
            data["xvals"] = newXvals  # Set new x-values

        if newYlabel is not None:
            oldYLabel = data["ylabels"]
            data["ylabels"] = newYlabel
            newYvals = self.on_change_xy_axis(
                data["yvals"],
                oldYLabel,
                newYlabel,
                pusherFreq=document.parameters.get("pusherFreq", 1000),
                scanTime=document.parameters.get("scanTime", 1.0),
                defaults=data["defaultY"],
            )
            data["yvals"] = newYvals

        expand_item = "document"
        expand_item_title = None
        replotID = evtID
        # Replace data in the dictionary
        if selectedText is None:
            document.IMS2D = data
            replotID = ID_showPlotDocument
        elif selectedText == "Drift time (2D)":
            document.IMS2D = data
            replotID = ID_showPlotDocument
        elif selectedText == "Drift time (2D, processed)":
            document.IMS2Dprocess = data
            replotID = ID_showPlotDocument
        elif selectedItemParentText == "Drift time (2D, EIC)" and selectedText is not None:
            document.IMS2Dions[selectedText] = data
            expand_item, expand_item_title = "ions", selectedText
            replotID = ID_showPlotDocument
        elif selectedItemParentText == "Drift time (2D, combined voltages, EIC)" and selectedText is not None:
            document.IMS2DCombIons[selectedText] = data
            expand_item, expand_item_title = "combined_ions", selectedText
            replotID = ID_showPlotDocument
        elif selectedItemParentText == "Drift time (2D, processed, EIC)" and selectedText is not None:
            document.IMS2DionsProcess[selectedText] = data
            expand_item, expand_item_title = "processed_ions", selectedText
            replotID = ID_showPlotDocument
        elif selectedItemParentText == "Input data" and selectedText is not None:
            document.IMS2DcompData[selectedText] = data
            expand_item_title = selectedText
            replotID = ID_showPlotDocument

        # 1D data
        elif selectedText == "Drift time (1D)":
            document.DT = data
        elif selectedItemParentText == "Drift time (1D, EIC)" and selectedText is not None:
            document.multipleDT[selectedText] = data
            expand_item, expand_item_title = "ions_1D", selectedText

        # Chromatograms
        elif selectedText == "Chromatogram":
            document.RT = data
            replotID = ID_showPlotDocument
        elif selectedItemParentText == "Chromatograms (EIC)" and selectedText is not None:
            data = document.multipleRT[selectedText] = data
        elif selectedItemParentText == "Chromatograms (combined voltages, EIC)" and selectedText is not None:
            data = document.IMSRTCombIons[selectedText] = data

        # DT/MS
        elif selectedText == "DT/MS":
            document.DTMZ = data
        else:
            document.IMS2D

        # update document
        if docItem is not False:
            try:
                self.SetPyData(docItem, data)
                self.presenter.documentsDict[document.title] = document
            except Exception:
                self.data_handling.on_update_document(document, expand_item, expand_item_title=expand_item_title)
        else:
            self.data_handling.on_update_document(document, expand_item, expand_item_title=expand_item_title)

        # Try to plot that data
        try:
            self.on_show_plot(evt=replotID)
        except Exception:
            pass

    def on_change_xy_axis(self, data, oldLabel, newLabel, charge=1, pusherFreq=1000, scanTime=1.0, defaults=None):
        """
        This function changes the X and Y axis labels
        Parameters
        ----------
        data : array/list, 1D array of old X/Y-axis labels
        oldLabel : string, old X/Y-axis labels
        newLabel : string, new X/Y-axis labels
        charge : integer, charge of the ion
        pusherFreq : float, pusher frequency
        mode : string, 1D/2D modes available
        Returns
        -------
        newVals : array/list, 1D array of new X/Y-axis labels
        """

        # Make sure we have charge and pusher values
        if charge == "None" or charge == "":
            charge = 1
        else:
            charge = str2int(charge)

        if pusherFreq == "None" or pusherFreq == "":
            pusherFreq = 1000
        else:
            pusherFreq = str2num(pusherFreq)

        msg = "Currently just changing label. Proper conversion will be coming soon"
        # Check whether labels were changed
        if oldLabel != newLabel:
            # Convert Y-axis labels
            if oldLabel == "Drift time (bins)" and newLabel in ["Drift time (ms)", "Arrival time (ms)"]:
                newVals = (data * pusherFreq) / 1000
                return newVals
            elif oldLabel in ["Drift time (ms)", "Arrival time (ms)"] and newLabel == "Drift time (bins)":
                newVals = (data / pusherFreq) * 1000
                return newVals
            elif oldLabel in ["Drift time (ms)", "Arrival time (ms)"] and newLabel == "Collision Cross Section (Å²)":
                self.presenter.onThreading(None, (msg, 4, 7), action="updateStatusbar")
                newVals = data
            elif oldLabel == "Collision Cross Section (Å²)" and newLabel in ["Drift time (ms)", "Arrival time (ms)"]:
                self.presenter.onThreading(None, (msg, 4, 7), action="updateStatusbar")
                newVals = data
            elif oldLabel == "Drift time (bins)" and newLabel == "Collision Cross Section (Å²)":
                self.presenter.onThreading(None, (msg, 4, 7), action="updateStatusbar")
                newVals = data
            elif oldLabel == "Collision Cross Section (Å²)" and newLabel == "Drift time (bins)":
                self.presenter.onThreading(None, (msg, 4, 7), action="updateStatusbar")
                newVals = data
            elif (
                oldLabel == "Drift time (ms)"
                and newLabel == "Arrival time (ms)"
                or oldLabel == "Arrival time (ms)"
                and newLabel == "Drift time (ms)"
            ):
                newVals = data
            else:
                newVals = data

            # Convert X-axis labels
            # Convert CV --> LFE
            if oldLabel in ["Collision Voltage (V)", "Activation Energy (V)"] and newLabel in [
                "Lab Frame Energy (eV)",
                "Activation Energy (eV)",
            ]:
                if isinstance(data, list):
                    newVals = [value * charge for value in data]
                else:
                    newVals = data * charge
            # If labels involve no conversion
            elif (
                (oldLabel == "Activation Energy (V)" and newLabel == "Collision Voltage (V)")
                or (oldLabel == "Collision Voltage (V)" and newLabel == "Activation Energy (V)")
                or (oldLabel == "Lab Frame Energy (eV)" and newLabel == "Activation Energy (eV)")
                or (oldLabel == "Activation Energy (eV)" and newLabel == "Lab Frame Energy (eV)")
            ):
                if isinstance(data, list):
                    newVals = [value for value in data]
                else:
                    newVals = data
            # Convert Lab frame energy --> collision voltage
            elif newLabel in ["Collision Voltage (V)", "Activation Energy (V)"] and oldLabel in [
                "Lab Frame Energy (eV)",
                "Activation Energy (eV)",
            ]:
                if isinstance(data, list):
                    newVals = [value / charge for value in data]
                else:
                    newVals = data / charge
            # Convert LFE/CV --> scans
            elif newLabel == "Scans" and oldLabel in [
                "Lab Frame Energy (eV)",
                "Collision Voltage (V)",
                "Activation Energy (eV)",
                "Activation Energy (V)",
            ]:
                newVals = 1 + np.arange(len(data))
            # Convert Scans --> LFE/CV
            elif oldLabel == "Scans" and newLabel in [
                "Lab Frame Energy (eV)",
                "Collision Voltage (V)",
                "Activation Energy (eV)",
                "Activation Energy (V)",
            ]:
                # Check if defaults were provided
                if defaults is None:
                    newVals = data
                else:
                    if defaults["xlabels"] == "Lab Frame Energy (eV)" or defaults["xlabels"] == "Collision Voltage (V)":
                        newVals = defaults["xvals"]
                    else:
                        newVals = data
            # Convert Scans -> Time
            elif newLabel in ["Retention time (min)", "Time (min)"] and oldLabel == "Scans":
                newVals = (data * scanTime) / 60
                return newVals
            elif oldLabel in ["Retention time (min)", "Time (min)"] and newLabel == "Scans":
                newVals = (data / scanTime) * 60
                return newVals
            elif oldLabel in ["Retention time (min)", "Time (min)"] and newLabel == [
                "Retention time (min)",
                "Time (min)",
            ]:
                return data

            else:
                newVals = data

            # Return new values
            return newVals
        # labels were not changed
        else:
            return data

    def onAddToTable(self, evt):
        evtID = evt.GetId()

        filelist = self.presenter.view.panelMML.peaklist
        textlist = self.presenter.view.panelMultipleText.peaklist
        if evtID == ID_docTree_addToMMLTable:
            data = self._document_data.multipleMassSpectrum
            document_title = self._document_data.title
            n_rows = len(data)
            colors = self.panel_plot.on_change_color_palette(None, n_colors=n_rows, return_colors=True)
            for i, key in enumerate(data):
                count = filelist.GetItemCount()
                label = data[key].get("label", os.path.splitext(key)[0])
                color = data[key].get("color", colors[i])
                if np.sum(color) > 4:
                    color = convert_rgb_255_to_1(color)
                filelist.Append([key, data[key].get("trap", 0), document_title, label])
                color = convert_rgb_1_to_255(color)
                filelist.SetItemBackgroundColour(count, color)
                filelist.SetItemTextColour(count, get_font_color(color, return_rgb=True))

        elif evtID == ID_docTree_addOneToMMLTable:
            data = self._document_data.multipleMassSpectrum
            count = filelist.GetItemCount()
            colors = self.panel_plot.on_change_color_palette(None, n_colors=count + 1, return_colors=True)
            key = self._item_leaf
            document_title = self._document_data.title
            label = data.get("label", key)
            color = data[key].get("color", colors[-1])
            if np.sum(color) > 4:
                color = convert_rgb_255_to_1(color)
            filelist.Append([key, data[key].get("trap", 0), document_title, label])
            color = convert_rgb_1_to_255(color)
            filelist.SetItemBackgroundColour(count, color)
            filelist.SetItemTextColour(count, get_font_color(color, return_rgb=True))

        elif evtID == ID_docTree_addToTextTable:
            data = self._document_data.IMS2DcompData
            document_title = self._document_data.title
            n_rows = len(data)
            colors = self.panel_plot.on_change_color_palette(None, n_colors=n_rows, return_colors=True)
            for i, key in enumerate(data):
                count = textlist.GetItemCount()
                label = data[key].get("label", os.path.splitext(key)[0])
                color = data[key].get("color", colors[i])
                if np.sum(color) > 4:
                    color = convert_rgb_255_to_1(color)
                minCE, maxCE = np.min(data[key]["xvals"]), np.max(data[key]["xvals"])
                document_label = "{}: {}".format(document_title, key)
                textlist.Append(
                    [
                        minCE,
                        maxCE,
                        data[key]["charge"],
                        color,
                        data[key]["cmap"],
                        data[key]["alpha"],
                        data[key]["mask"],
                        label,
                        data[key]["zvals"].shape,
                        document_label,
                    ]
                )
                color = convert_rgb_1_to_255(color)
                textlist.SetItemBackgroundColour(count, color)
                textlist.SetItemTextColour(count, get_font_color(color, return_rgb=True))

        elif evtID == ID_docTree_addInteractiveToTextTable:
            data = self._document_data.IMS2Dions
            document_title = self._document_data.title
            n_rows = len(data)
            colors = self.panel_plot.on_change_color_palette(None, n_colors=n_rows, return_colors=True)
            for i, key in enumerate(data):
                count = textlist.GetItemCount()
                label = data[key].get("label", os.path.splitext(key)[0])
                color = data[key].get("color", colors[i])
                if np.sum(color) > 4:
                    color = convert_rgb_255_to_1(color)
                minCE, maxCE = np.min(data[key]["xvals"]), np.max(data[key]["xvals"])
                document_label = "{}: {}".format(document_title, key)
                textlist.Append(
                    [
                        "",
                        minCE,
                        maxCE,
                        data[key].get("charge", ""),
                        color,
                        data[key]["cmap"],
                        data[key]["alpha"],
                        data[key]["mask"],
                        label,
                        data[key]["zvals"].shape,
                        document_label,
                    ]
                )
            color = convert_rgb_1_to_255(color)
            textlist.SetItemBackgroundColour(count, color)
            textlist.SetItemTextColour(count, get_font_color(color, return_rgb=True))

        if evtID in [ID_docTree_addToMMLTable, ID_docTree_addOneToMMLTable]:
            # sort items
            self.presenter.view.panelMML.OnSortByColumn(column=1, overrideReverse=True)
            self.presenter.view.panelMML.onRemoveDuplicates(None)
            self.presenter.view.on_toggle_panel(evt=ID_window_multipleMLList, check=True)

        elif evtID in [ID_docTree_addToTextTable, ID_docTree_addOneToTextTable, ID_docTree_addInteractiveToTextTable]:
            # sort items
            self.presenter.view.panelMultipleText.onRemoveDuplicates(None)
            self.presenter.view.on_toggle_panel(evt=ID_window_textList, check=True)

    def onShowMassSpectra(self, evt):

        data = self._document_data.multipleMassSpectrum
        spectra_count = len(list(data.keys()))
        if spectra_count > 50:
            dlg = DialogBox(
                exceptionTitle="Would you like to continue?",
                exceptionMsg="There are {} mass spectra in this document. Would you like to continue?".format(
                    spectra_count
                ),
                type="Question",
            )
            if dlg == wx.ID_NO:
                msg = "Cancelled was operation"
                self.presenter.view.SetStatusText(msg, 3)
                return

        # Check for energy
        energy_name = []
        for key in data:
            energy_name.append([key, data[key].get("trap", 0)])
        # sort
        energy_name.sort(key=itemgetter(1))

        names, xvals_list, yvals_list = [], [], []
        for row in energy_name:
            key = row[0]
            xvals_list.append(data[key]["xvals"])
            yvals_list.append(data[key]["yvals"])
            names.append(key)

        kwargs = {"show_y_labels": True, "labels": names}
        self.panel_plot.on_plot_waterfall(
            xvals_list, yvals_list, None, colors=[], xlabel="m/z", ylabel="", set_page=True, **kwargs
        )

    def on_open_spectrum_comparison_viewer(self, evt):
        """Open panel where user can select mas spectra to compare """
        from origami.widgets.panel_signal_comparison_viewer import PanelSignalComparisonViewer

        if self._item_id is None:
            return

        document_spectrum_list = self.data_handling.generate_item_list_mass_spectra("comparison")
        document_list = list(document_spectrum_list.keys())
        count = sum([len(document_spectrum_list[_title]) for _title in document_spectrum_list])

        if count < 2:
            logger.error(f"There must be at least 2 items in the list co compare. Current count: {count}")
            return

        try:
            document_title = self._document_data.title
        except AttributeError:
            document_title = document_list[0]

        kwargs = {
            "current_document": document_title,
            "document_list": document_list,
            "document_spectrum_list": document_spectrum_list,
        }

        self._compare_panel = PanelSignalComparisonViewer(self.view, self.presenter, self.config, self.icons, **kwargs)
        self._compare_panel.Show()

    def on_process_2D(self, evt):
        """Process clicked heatmap item"""

        document, data, query = self._on_event_get_mobility_chromatogram_data()

        self.on_open_process_2D_settings(
            data=data, document=document, document_title=document.title, dataset_type=query[1], dataset_name=query[2]
        )

    def on_process_2D_plot_only(self, dataset_type, data):
        self.on_open_process_2D_settings(
            data=data,
            document=None,
            document_title=None,
            dataset_type=dataset_type,
            dataset_name=None,
            disable_plot=False,
            disable_process=True,
        )

    def on_process_all_2D(self, evt):
        """Process all clicked heatmap items"""

        document, data, query = self._on_event_get_mobility_chromatogram_data()
        self.on_open_process_2D_settings(
            data=data,
            document=document,
            document_title=document.title,
            dataset_type=query[1],
            dataset_name=query[2],
            disable_plot=True,
            disable_process=False,
            process_all=True,
        )

    def on_open_process_2D_settings(self, **kwargs):
        """Open heatmap processing settings"""
        from origami.gui_elements.panel_process_heatmap import PanelProcessHeatmap

        panel = PanelProcessHeatmap(self.presenter.view, self.presenter, self.config, self.icons, **kwargs)
        panel.Show()

    def on_process_MS(self, evt, **kwargs):
        """Process clicked mass spectrum item"""
        document, data, dataset = self._on_event_get_mass_spectrum(**kwargs)
        self.on_open_process_MS_settings(
            mz_data=data,
            document=document,
            document_title=document.title,
            dataset_name=dataset,
            update_widget=kwargs.pop("update_widget", False),
        )

    def on_process_MS_plot_only(self, data):
        """Process mass spectrum data

        Parameters
        ----------
        data : dict
            dictionary containing `xvals`, `yvals`, `xlabels` and `ylabels` keys with data
        """
        self.on_open_process_MS_settings(
            mz_data=data, document=None, document_title=None, dataset_name=None, disable_process=True
        )

    def on_process_MS_all(self, evt, **kwargs):
        """Process all clicked mass spectra items"""
        document, data, dataset = self._on_event_get_mass_spectrum(**kwargs)
        self.on_open_process_MS_settings(
            mz_data=data,
            document=document,
            document_title=document.title,
            dataset_name=dataset,
            disable_plot=True,
            disable_process=False,
            process_all=True,
        )

    def on_open_process_MS_settings(self, **kwargs):
        """Open mass spectrum processing settings"""
        from origami.gui_elements.panel_process_spectrum import PanelProcessMassSpectrum

        panel = PanelProcessMassSpectrum(self.presenter.view, self.presenter, self.config, self.icons, **kwargs)
        panel.Show()

    def onProcess(self, evt=None):
        if self._document_data is None:
            return

        # TODO: This function needs to be fixed before next release

    #         if self._document_type == 'Mass Spectrum': pass
    #         elif any(self._document_type in itemType for itemType in ['Drift time (2D)', 'Drift time (2D, processed)',
    #                                                             'Drift time (2D, EIC)',
    #                                                             'Drift time (2D, combined voltages, EIC)',
    #                                                             'Drift time (2D, processed, EIC)',
    #                                                             'Input data', 'Statistical']):
    #             self.presenter.process2Ddata2()
    #             self_set_pageSetSelection(self.config.panelNames['2D'])
    #
    #         elif self._document_type == 'DT/MS':
    #             self.presenter.process2Ddata2(mode='MSDT')
    #             self.panel_plot._set_page(self.config.panelNames['MZDT'])

    def onShow_and_SavePlot(self, evt):
        """Replot and save image"""

        # Show plot first
        self.on_show_plot(evt=None, save_image=True)

    def onDuplicateItem(self, evt):
        evtID = evt.GetId()
        if evtID == ID_duplicateItem:
            if self._document_type == "Mass Spectra" and self._item_leaf != "Mass Spectra":
                # Change document tree
                title = self._document_data.title
                docItem = self.get_item_by_data(
                    self.presenter.documentsDict[title].multipleMassSpectrum[self._item_leaf]
                )
                copy_name = "{} - copy".format(self._item_leaf)
                # Change dictionary key
                self.presenter.documentsDict[title].multipleMassSpectrum[copy_name] = (
                    self.presenter.documentsDict[self.title].multipleMassSpectrum[self._item_leaf].copy()
                )
                document = self.presenter.documentsDict[title]
                self.data_handling.on_update_document(document, "document")
                self.Expand(docItem)
        # duplicate document
        elif evtID == ID_docTree_duplicate_document:
            document = self.data_handling.on_duplicate_document()
            document.title = "{} - copy".format(document.title)
            self.data_handling._load_document_data(document)

    #             self.data_handling.on_update_document(document, "document")

    # TODO: should restore items to various side panels

    def onRenameItem(self, evt):
        from origami.gui_elements.dialog_rename import DialogRenameObject

        if self._document_data is None:
            return

        current_name = None
        prepend_name = False
        if self._indent == 1 and self._item_leaf is None:
            prepend_name = False
        elif self._document_type == "Statistical" and self._item_leaf != "Statistical":
            prepend_name = True
        elif self._document_type == "Overlay" and self._item_leaf != "Overlay":
            prepend_name = True
        elif self._document_type == "Mass Spectra" and self._item_leaf != "Mass Spectra":
            current_name = self._item_leaf
        elif self._document_data.dataType == "Type: Interactive":
            if self._document_type not in ["Drift time (2D, EIC)"]:
                return
            current_name = self._item_leaf
        else:
            return

        if current_name is None:
            try:
                current_name = re.split("-|,|:|__", self._item_leaf.replace(" ", ""))[0]
            except AttributeError:
                current_name = self._document_data.title

        if current_name == "Grid(nxn)":
            current_name = "Grid (n x n)"
        elif current_name == "Grid(2":
            current_name = "Grid (2->1)"
        elif current_name == "RMSDMatrix":
            current_name = "RMSD Matrix"
        elif current_name == "Waterfall(Raw)":
            current_name = "Waterfall (Raw)"
        elif current_name == "Waterfall(Processed)":
            current_name = "Waterfall (Processed)"
        elif current_name == "Waterfall(Fitted)":
            current_name = "Waterfall (Fitted)"
        elif current_name == "Waterfall(DeconvolutedMW)":
            current_name = "Waterfall (Deconvoluted MW)"
        elif current_name == "Waterfalloverlay":
            current_name = "Waterfall overlay"

        kwargs = {"current_name": current_name, "prepend_name": prepend_name}
        renameDlg = DialogRenameObject(self, self.presenter, self.title, **kwargs)
        renameDlg.CentreOnScreen()
        renameDlg.ShowModal()
        new_name = renameDlg.new_name

        if new_name == current_name:
            print("Names are the same - ignoring")
        elif new_name == "" or new_name is None:
            print("Incorrect name")
        else:
            # Actual new name, prepended
            if self._indent == 1:
                # Change document tree
                docItem = self.get_item_by_data(self.presenter.documentsDict[current_name])
                document = self.presenter.documentsDict[current_name]
                document.title = new_name
                docItem.title = new_name
                parent = self.GetItemParent(docItem)
                del self.presenter.documentsDict[current_name]
                self.SetItemText(docItem, new_name)
                # Change dictionary key
                self.data_handling.on_update_document(document, "document")
                self.Expand(docItem)

                # check if item is in other panels
                # TODO: implement for other panels
                try:
                    self.presenter.view.panelMML.onRenameItem(current_name, new_name, item_type="document")
                except Exception:
                    pass
                try:
                    self.presenter.view.panelMultipleIons.onRenameItem(current_name, new_name, item_type="document")
                except Exception:
                    pass
            #                 try: self.presenter.view.panelMultipleText.on_remove_deleted_item(title)
            #                 except Exception: pass
            #                 try: self.presenter.view.panelMML.on_remove_deleted_item(title)
            #                 except Exception: pass
            #                 try: self.presenter.view.panelLinearDT.topP.on_remove_deleted_item(title)
            #                 except Exception: pass
            #                 try: self.presenter.view.panelLinearDT.bottomP.on_remove_deleted_item(title)
            #                 except Exception: pass

            elif self._document_type == "Statistical":
                # Change document tree
                docItem = self.get_item_by_data(
                    self.presenter.documentsDict[self.title].IMS2DstatsData[self._item_leaf]
                )
                parent = self.GetItemParent(docItem)
                self.SetItemText(docItem, new_name)
                # Change dictionary key
                self.presenter.documentsDict[self.title].IMS2DstatsData[new_name] = self.presenter.documentsDict[
                    self.title
                ].IMS2DstatsData.pop(self._item_leaf)
                self.Expand(docItem)
            elif self._document_type == "Overlay":
                # Change document tree
                docItem = self.get_item_by_data(
                    self.presenter.documentsDict[self.title].IMS2DoverlayData[self._item_leaf]
                )
                parent = self.GetItemParent(docItem)
                self.SetItemText(docItem, new_name)
                # Change dictionary key
                self.presenter.documentsDict[self.title].IMS2DoverlayData[new_name] = self.presenter.documentsDict[
                    self.title
                ].IMS2DoverlayData.pop(self._item_leaf)
                self.Expand(docItem)
            elif self._document_type == "Mass Spectra":
                # Change document tree
                docItem = self.get_item_by_data(
                    self.presenter.documentsDict[self.title].multipleMassSpectrum[self._item_leaf]
                )
                parent = self.GetItemParent(docItem)
                self.SetItemText(docItem, new_name)
                # Change dictionary key
                self.presenter.documentsDict[self.title].multipleMassSpectrum[new_name] = self.presenter.documentsDict[
                    self.title
                ].multipleMassSpectrum.pop(self._item_leaf)
                self.Expand(docItem)
                # check if item is in other panels
                try:
                    self.presenter.view.panelMML.onRenameItem(current_name, new_name, item_type="filename")
                except Exception:
                    pass
            elif self._document_type == "Drift time (2D, EIC)":
                new_name = new_name.replace(": ", " : ")
                # Change document tree
                docItem = self.get_item_by_data(self.presenter.documentsDict[self.title].IMS2Dions[self._item_leaf])
                parent = self.GetItemParent(docItem)
                self.SetItemText(docItem, new_name)
                # check if ":" found in the new name

                # TODO: check if iterm is in the peaklist
                # Change dictionary key
                self.presenter.documentsDict[self.title].IMS2Dions[new_name] = self.presenter.documentsDict[
                    self.title
                ].IMS2Dions.pop(self._item_leaf)
                self.Expand(docItem)
            else:
                return

            # just a msg
            args = ("Renamed {} to {}".format(current_name, new_name), 4)
            self.presenter.onThreading(None, args, action="updateStatusbar")

            # Expand parent
            try:
                self.Expand(parent)
            except Exception:
                pass

            self.SetFocus()

    def onGoToDirectory(self, evt):
        """Go to selected directory"""
        self.data_handling.on_open_directory(None)

    def on_save_unidec_results(self, evt, data_type="all"):
        basename = os.path.splitext(self._document_data.title)[0]

        if (self._document_type == "Mass Spectrum" and self._item_leaf == "UniDec") or (
            self._document_type == "UniDec" and self._indent == 2
        ):
            unidec_engine_data = self._document_data.massSpectrum["unidec"]
            data_type = "all"
        elif self._document_type == "Mass Spectrum" and self._item_branch == "UniDec" and self._indent == 4:
            unidec_engine_data = self._document_data.massSpectrum["unidec"]
            data_type = self._item_leaf
        elif self._document_type == "Mass Spectra" and self._item_leaf == "UniDec":
            unidec_engine_data = self._document_data.multipleMassSpectrum[self._item_branch]["unidec"]
            data_type = "all"
        elif self._document_type == "Mass Spectra" and self._item_branch == "UniDec":
            unidec_engine_data = self._document_data.multipleMassSpectrum[self._item_root]["unidec"]
            data_type = self._item_leaf

        #         try:
        if data_type in ["all", "MW distribution"]:
            data_type_name = "MW distribution"
            defaultValue = "unidec_MW_{}{}".format(basename, self.config.saveExtension)

            data = unidec_engine_data[data_type_name]
            kwargs = {"default_name": defaultValue}
            data = [data["xvals"], data["yvals"]]
            labels = ["MW(Da)", "Intensity"]
            self.data_handling.on_save_data_as_text(data=data, labels=labels, data_format="%.4f", **kwargs)
        #         except Exception:
        #             print('Failed to save MW distributions')

        try:
            if data_type in ["all", "m/z with isolated species"]:
                data_type_name = "m/z with isolated species"
                defaultValue = "unidec_mz_species_{}{}".format(basename, self.config.saveExtension)
                data = unidec_engine_data[data_type_name]

                i, save_data, labels = 0, [], ["m/z"]
                for key in data:
                    if key.split(" ")[0] != "MW:":
                        continue
                    xvals = data[key]["line_xvals"]
                    if i == 0:
                        save_data.append(xvals)
                    yvals = data[key]["line_yvals"]
                    save_data.append(yvals)
                    labels.append(key)
                    i = +1
                save_data = np.column_stack(save_data).T

                kwargs = {"default_name": defaultValue}
                self.data_handling.on_save_data_as_text(data=save_data, labels=labels, data_format="%.4f", **kwargs)
        except Exception:
            pass

        try:
            if data_type in ["all", "Fitted"]:
                data_type_name = "Fitted"
                defaultValue = "unidec_fitted_{}{}".format(basename, self.config.saveExtension)
                data = unidec_engine_data[data_type_name]

                kwargs = {"default_name": defaultValue}
                data = [data["xvals"][0], data["yvals"][0], data["yvals"][1]]
                labels = ["m/z(Da)", "Intensity(raw)", "Intensity(fitted)"]
                self.data_handling.on_save_data_as_text(data=data, labels=labels, data_format="%.4f", **kwargs)
        except Exception:
            pass

        try:
            if data_type in ["all", "Processed"]:
                data_type_name = "Processed"
                defaultValue = "unidec_processed_{}{}".format(basename, self.config.saveExtension)
                data = unidec_engine_data[data_type_name]

                kwargs = {"default_name": defaultValue}
                data = [data["xvals"], data["yvals"]]
                labels = ["m/z(Da)", "Intensity"]
                self.data_handling.on_save_data_as_text(data=data, labels=labels, data_format="%.4f", **kwargs)
        except Exception:
            pass

        try:
            if data_type in ["all", "m/z vs Charge"]:
                data_type_name = "m/z vs Charge"
                defaultValue = "unidec_mzVcharge_{}{}".format(basename, self.config.saveExtension)
                data = unidec_engine_data[data_type_name]["grid"]

                zvals = data[:, 2]
                xvals = np.unique(data[:, 0])
                yvals = np.unique(data[:, 1])

                # reshape data
                xlen = len(xvals)
                ylen = len(yvals)
                zvals = np.reshape(zvals, (xlen, ylen))

                # Combine x-axis with data
                save_data = np.column_stack((xvals, zvals)).T
                yvals = list(map(str, yvals.tolist()))
                labels = ["m/z(Da)"]
                for label in yvals:
                    labels.append(label)

                kwargs = {"default_name": defaultValue}
                self.data_handling.on_save_data_as_text(data=save_data, labels=labels, data_format="%.4f", **kwargs)
        except Exception:
            pass

        try:
            if data_type in ["all", "MW vs Charge"]:
                data_type_name = "MW vs Charge"
                defaultValue = "unidec_MWvCharge_{}{}".format(basename, self.config.saveExtension)
                data = unidec_engine_data[data_type_name]

                xvals = data["xvals"]
                yvals = data["yvals"]
                zvals = data["zvals"]
                # reshape data
                xlen = len(xvals)
                ylen = len(yvals)
                zvals = np.reshape(zvals, (xlen, ylen))

                # Combine x-axis with data
                save_data = np.column_stack((xvals, zvals)).T
                yvals = list(map(str, yvals.tolist()))
                labels = ["MW(Da)"]
                for label in yvals:
                    labels.append(label)

                kwargs = {"default_name": defaultValue}
                self.data_handling.on_save_data_as_text(data=save_data, labels=labels, data_format="%.4f", **kwargs)
        except Exception:
            pass

        try:
            if data_type in ["all", "Barchart"]:
                data_type_name = "Barchart"
                defaultValue = "unidec_Barchart_{}{}".format(basename, self.config.saveExtension)
                data = unidec_engine_data[data_type_name]

                xvals = data["xvals"]
                yvals = data["yvals"]
                legend_text = data["legend_text"]

                # get labels from legend
                labels = []
                for item in legend_text:
                    labels.append(item[1])

                save_data = [xvals, yvals, labels]

                kwargs = {"default_name": defaultValue}
                self.data_hafndling.on_save_data_as_text(
                    data=save_data, labels=["position", "intensity", "label"], data_format="%s", **kwargs
                )
        except Exception:
            pass

        try:
            if data_type in ["all", "Charge information"]:
                data_type_name = "Charge information"
                defaultValue = "unidec_ChargeInformation_{}{}".format(basename, self.config.saveExtension)
                data = unidec_engine_data[data_type_name]

                save_data = [data[:, 0], data[:, 1]]

                kwargs = {"default_name": defaultValue}
                self.data_handling.on_save_data_as_text(
                    data=save_data, labels=["charge", "intensity"], data_format="%s", **kwargs
                )
        except Exception:
            pass

    def on_show_unidec_results(self, evt, plot_type="all"):
        logger.error("This function was depracated")

    def on_show_plot_annotated_data(self, data, save_image=False, **kwargs):
        """Plot annotate data"""

        try:
            plot_type = data["plot_type"]
        except KeyError:
            logger.error("Could not determine plot type from the data")
            return

        if plot_type in [
            "scatter",
            "waterfall",
            "line",
            "multi-line",
            "grid-scatter",
            "grid-line",
            "vertical-bar",
            "horizontal-bar",
        ]:
            xlabel = data["xlabel"]
            ylabel = data["ylabel"]
            labels = data["labels"]
            colors = data["colors"]
            xvals = data["xvals"]
            yvals = data["yvals"]
            zvals = data["zvals"]

            plot_obj = kwargs.pop("plot_obj", None)

            kwargs = {
                "plot_modifiers": data["plot_modifiers"],
                "item_colors": data["itemColors"],
                "item_labels": data["itemLabels"],
                "xerrors": data["xvalsErr"],
                "yerrors": data["yvalsErr"],
                "xlabels": data["xlabels"],
                "ylabels": data["ylabels"],
                "plot_obj": plot_obj,
            }

        if plot_type == "scatter":
            self.panel_plot.on_plot_other_scatter(
                xvals, yvals, zvals, xlabel, ylabel, colors, labels, set_page=True, **kwargs
            )
        elif plot_type == "waterfall":
            kwargs = {"labels": labels, "plot_obj": plot_obj}
            self.panel_plot.on_plot_other_waterfall(
                xvals, yvals, None, xlabel, ylabel, colors=colors, set_page=True, **kwargs
            )
        elif plot_type == "multi-line":
            self.panel_plot.on_plot_other_overlay(
                xvals, yvals, xlabel, ylabel, colors=colors, set_page=True, labels=labels, **kwargs
            )
        elif plot_type == "line":
            kwargs = {
                "line_color": colors[0],
                "shade_under_color": colors[0],
                "plot_modifiers": data["plot_modifiers"],
                "plot_obj": plot_obj,
            }
            self.panel_plot.on_plot_other_1D(xvals, yvals, xlabel, ylabel, **kwargs)
        elif plot_type == "grid-line":
            self.panel_plot.on_plot_other_grid_1D(
                xvals, yvals, xlabel, ylabel, colors=colors, labels=labels, set_page=True, **kwargs
            )
        elif plot_type == "grid-scatter":
            self.panel_plot.on_plot_other_grid_scatter(
                xvals, yvals, xlabel, ylabel, colors=colors, labels=labels, set_page=True, **kwargs
            )

        elif plot_type in ["vertical-bar", "horizontal-bar"]:
            kwargs.update(orientation=plot_type)
            self.panel_plot.on_plot_other_bars(
                xvals, data["yvals_min"], data["yvals_max"], xlabel, ylabel, colors, set_page=True, **kwargs
            )
        elif plot_type in ["matrix"]:
            zvals, yxlabels, cmap = self.presenter.get2DdataFromDictionary(
                dictionary=data, plotType="Matrix", compact=False
            )
            self.panel_plot.on_plot_matrix(zvals=zvals, xylabels=yxlabels, cmap=cmap, set_page=True)
        else:
            msg = (
                "Plot: {} is not supported yet. Please contact Lukasz Migas \n".format(plot_type)
                + "if you would like to include a new plot type in ORIGAMI. Currently \n"
                + "supported plots include: line, multi-line, waterfall, scatter and grid."
            )
            DialogBox(exceptionTitle="Plot type not supported", exceptionMsg=msg, type="Error")

        if save_image:
            basename = os.path.splitext(self._document_data.title)[0]
            defaultValue = (
                "Custom_{}_{}".format(basename, os.path.splitext(self._item_leaf)[0]).replace(":", "").replace(" ", "")
            )
            save_kwargs = {"image_name": defaultValue}
            self.panel_plot.save_images(evt="other", **save_kwargs)

    def on_show_plot_mass_spectra(self, save_image=False):

        # Select dataset
        if self._item_leaf == "Mass Spectra":
            return

        # get plot data
        data = self.GetPyData(self._item_id)
        try:
            msX = data["xvals"]
            msY = data["yvals"]
        except (KeyError, TypeError):
            logger.error("Could not plot mass spectrum")
            return

        # get plot limits
        xlimits = [None, None]
        if "xlimits" in data:
            xlimits = data["xlimits"]
        elif "startMS" in self._document_data.parameters and "endMS" in self._document_data.parameters:
            xllimits = [self._document_data.parameters["startMS"], self._document_data.parameters["endMS"]]

        # setup kwargs
        if self._document_type in ["Mass Spectrum"]:
            name_kwargs = {"document": self._document_data.title, "dataset": "Mass Spectrum"}
        elif self._document_type in ["Mass Spectrum (processed)"]:
            name_kwargs = {"document": self._document_data.title, "dataset": "Mass Spectrum (processed)"}
        elif self._document_type == "Mass Spectra" and self._item_leaf != self._document_type:
            name_kwargs = {"document": self._document_data.title, "dataset": self._item_leaf}

        # plot
        if self._document_data.dataType == "Type: CALIBRANT":
            self.panel_plot.on_plot_MS_DT_calibration(msX, msY, xlimits=xlimits, plotType="MS", set_page=True)
        else:
            self.panel_plot.on_plot_MS(msX, msY, xlimits, set_page=True, **name_kwargs)

        if save_image:
            basename = os.path.splitext(self._document_data.title)[0]
            save_filename = f"MS_{basename}"
            if self._document_type == "Mass Spectrum (processed)":
                save_filename = f"MS_processed_{basename}"
            elif self._document_type == "Mass Spectra" and self._item_leaf != self._document_type:
                save_filename = "MS_{}_{}".format(basename, os.path.splitext(self._item_leaf)[0]).replace(":", "")
            # save plot
            self.panel_plot.save_images(evt="ms", image_name=save_filename)

    def on_show_plot_dtms(self, save_image=False):

        # get plot data
        data = self.GetPyData(self._item_id)
        xvals = data["xvals"]
        zvals = data["zvals"]
        xvals, zvals = self.data_processing.downsample_array(xvals, zvals)
        self.panel_plot.on_plot_MSDT(
            zvals,
            xvals,
            data["yvals"],
            data["xlabels"],
            data["ylabels"],
            set_page=True,
            full_data=dict(zvals=data["zvals"], xvals=data["xvals"]),
        )
        if save_image:
            basename = os.path.splitext(self._document_data.title)[0]
            save_filename = "DTMS_{}".format(basename)
            self.panel_plot.save_images(evt="ms/dt", image_name=save_filename)

    def on_show_plot_mobilogram(self, evtID, save_image=False):
        if self._item_leaf in ["Drift time (1D, EIC)", "Drift time (1D, EIC, DT-IMS)"]:
            return

        # get plot data
        data = self.GetPyData(self._item_id)
        dtX = data["xvals"]
        dtY = data["yvals"]
        if len(dtY) >= 1:
            dtY = data.get("yvalsSum", dtY)
        xlabel = data["xlabels"]

        # zoom-in on the ion
        if evtID == ID_showPlotMSDocument:
            self.on_show_plot_zoom_on_mass_spectrum(data, self._item_leaf)
            return

        if self._document_data.dataType != "Type: CALIBRANT":
            self.panel_plot.on_plot_1D(dtX, dtY, xlabel, set_page=True)
        else:
            self.panel_plot.on_plot_MS_DT_calibration(dtX=dtX, dtY=dtY, xlabelDT=xlabel, plotType="1DT", set_page=True)
            self.panel_plot.on_add_marker(
                xvals=data["peak"][0],
                yvals=data["peak"][1],
                color=self.config.annotColor,
                marker=self.config.markerShape,
                size=self.config.markerSize,
                plot="CalibrationDT",
            )

        if save_image:
            basename = os.path.splitext(self._document_data.title)[0]
            if self._document_type == "Drift time (1D)":
                save_filename = "DT_1D_{}".format(basename)
            elif self._document_type == "Drift time (1D, EIC, DT-IMS)":
                save_filename = "DTIMS_1D_{}_{}".format(basename, self._item_leaf)
            elif self._document_type == "Drift time (1D, EIC)":
                save_filename = "DT_1D_{}_{}".format(basename, self._item_leaf)
            self.panel_plot.save_images(evt="mobilogram", image_name=save_filename)

    def on_show_plot_chromatogram(self, evtID, save_image=False):
        if self._item_leaf in ["Chromatograms (EIC)", "Chromatograms (combined voltages, EIC)"]:
            return

        # get plot data
        data = self.GetPyData(self._item_id)
        rtX = data["xvals"]
        rtY = data["yvals"]
        xlabel = data["xlabels"]

        # zoom-in on the ion
        if evtID == ID_showPlotMSDocument:
            self.on_show_plot_zoom_on_mass_spectrum(data, self._item_leaf)
            return

        # Change panel and plot
        self.panel_plot.on_plot_RT(rtX, rtY, xlabel, set_page=True)
        if save_image:
            # generate plot name
            basename = os.path.splitext(self._document_data.title)[0]
            if self._document_type == "Chromatogram":
                save_filename = "RT_{}".format(basename)
            elif self._document_type == "Chromatograms (combined voltages, EIC)":
                save_filename = "RT_CV_{}_{}".format(basename, self._item_leaf)
            elif self._document_type == "Chromatograms (EIC)":
                save_filename = "RT_{}_{}".format(basename, self._item_leaf)
            self.panel_plot.save_images(evt="chromatogram", image_name=save_filename)

    def on_show_plot_zoom_on_mass_spectrum(self, data, ion_name):
        mz_min, mz_max = ut_labels.get_ion_name_from_label(ion_name)
        try:
            mz_min = str2num(mz_min) - self.config.zoomWindowX
            mz_max = str2num(mz_max) + self.config.zoomWindowX
        except TypeError:
            if "xylimits" in data:
                mz_min = data["xylimits"][0] - self.config.zoomWindowX
                mz_max = data["xylimits"][1] + self.config.zoomWindowX
            else:
                logger.error(f"Could not zoom-in on the selected item: {ion_name}")
                return

        self.panel_plot.on_zoom_1D_x_axis(mz_min, mz_max, set_page=True, plot="MS")

    def on_show_plot_heatmap(self, evtID, save_image=False):
        if self._item_leaf in [
            "Drift time (2D, EIC)",
            "Drift time (2D, combined voltages, EIC)",
            "Drift time (2D, processed, EIC)",
            "Input data",
            "Statistical",
        ]:
            return

        # get data for selected item
        data = self.GetPyData(self._item_id)

        # Unpack data
        if len(data) == 0:
            raise MessageError("Data buffer was empty...")

        # zoom-in on the ion
        if evtID == ID_showPlotMSDocument:
            self.on_show_plot_zoom_on_mass_spectrum(data, self._item_leaf)
            return

        # show as 1D plot
        if evtID == ID_showPlot1DDocument:
            self.panel_plot.on_plot_1D(
                data["yvals"],  # normally this would be the y-axis
                data["yvals1D"],
                data["ylabels"],  # data was rotated so using ylabel for xlabel
                set_page=True,
            )
            return
        # show as chromatogram
        elif evtID == ID_showPlotRTDocument:
            self.panel_plot.on_plot_RT(data["xvals"], data["yvalsRT"], data["xlabels"], set_page=True)
            return
        # show as violin
        elif evtID == ID_showPlotDocument_violin:
            dataOut = self.presenter.get2DdataFromDictionary(dictionary=data, dataType="plot", compact=True)
            self.panel_plot.on_plot_violin(data=dataOut, set_page=True)
            return
        # show as waterfall
        elif evtID == ID_showPlotDocument_waterfall:
            zvals, xvals, xlabel, yvals, ylabel, __ = self.presenter.get2DdataFromDictionary(
                dictionary=data, dataType="plot", compact=False
            )
            if len(xvals) > 500:
                msg = (
                    f"There are {len(xvals)} scans in this dataset (this could be slow...). "
                    + "Would you like to continue?"
                )
                dlg = DialogBox("Would you like to continue?", msg, type="Question")
                if dlg == wx.ID_NO:
                    return

            self.panel_plot.on_plot_waterfall(
                yvals=xvals, xvals=yvals, zvals=zvals, xlabel=xlabel, ylabel=ylabel, set_page=True
            )
            return

        # Change panel and plot data
        self.panel_plot.on_plot_2D(
            data["zvals"], data["xvals"], data["yvals"], data["xlabels"], data["ylabels"], set_page=True
        )

        if save_image:
            basename = os.path.splitext(self._document_data.title)[0]
            # check appropriate data is selected
            if self._document_type == "Drift time (2D, EIC)":
                save_filename = "DT_2D_{}_{}".format(basename, self._item_leaf)
            elif self._document_type == "Drift time (2D, combined voltages, EIC)":
                save_filename = "DT_2D_CV_{}_{}".format(basename, self._item_leaf)
            elif self._document_type == "Drift time (2D, processed, EIC)":
                save_filename = "DT_2D_processed_{}_{}".format(basename, self._item_leaf)
            elif self._document_type == "Input data":
                save_filename = "DT_2D_{}_{}".format(basename, self._item_leaf)
            elif self._document_type == "Statistical":
                save_filename = "DT_2D_{}_{}".format(basename, self._item_leaf)
            elif self._document_type == "Drift time (2D)":
                save_filename = "DT_2D_{}".format(basename)
            elif self._document_type == "Drift time (2D, processed)":
                save_filename = "DT_2D_processed_{}".format(basename)
            self.panel_plot.save_images(evt=ID_save2DImageDoc, image_name=save_filename)

    def on_show_plot_overlay(self, save_image):
        if self._item_leaf == self._document_type:
            return

        # get filename
        method = re.split("-|,|__|:", self._item_leaf)[0]
        basename = os.path.splitext(self._document_data.title)[0]
        fname_dict = {
            "Grid (n x n)": "overlay_Grid_NxN_{}".format(basename),
            "Grid (2": "overlay_Grid_2to1_{}".format(basename),
            "Mask": "overlay_mask_{}".format(basename),
            "Transparent": "overlay_transparent_{}".format(basename),
            "RMSF": "overlay_RMSF_{}".format(basename),
            "RGB": "overlay_RGB_{}".format(basename),
            "RMSD": "overlay_RMSD_{}".format(basename),
            "Variance": "overlay_variance_{}".format(basename),
            "Mean": "overlay_mean_{}".format(basename),
            "Standard Deviation": "overlay_std_{}".format(basename),
            "RMSD Matrix": "overlay_matrix_{}".format(basename),
            "Waterfall (Raw)": "MS_Waterfall_raw_{}".format(basename),
            "Waterfall (Processed)": "MS_Waterfall_processed_{}".format(basename),
            "Waterfall (Fitted)": "MS_Waterfall_fitted_{}".format(basename),
            "Waterfall (Deconvoluted MW)": "MS_Waterfall_deconvolutedMW_{}".format(basename),
            "Waterfall (Charge states)": "MS_Waterfall_charges_{}".format(basename),
            "Waterfall overlay": "Waterfall_overlay_{}".format(basename),
            "1D": "overlay_DT_1D_{}".format(basename),
            "Overlay (DT)": "overlay_DT_1D_{}".format(basename),
            "RT": "overlay_RT_{}".format(basename),
            "Overlay (RT)": "overlay_RT_{}".format(basename),
        }
        save_filename = fname_dict.get(method, f"overlay_{basename}")

        # get data
        data = self.GetPyData(self._item_id)
        if data is None:
            raise MessageError("Data buffer was empty...")

        # plot
        if method in [
            "Grid (n x n)",
            "Grid (2",
            "Mask",
            "Transparent",
            "RMSF",
            "RGB",
            "RMSD",
            "Variance",
            "Mean",
            "Standard Deviation",
            "RMSD Matrix",
            "1D",
            "Overlay (DT)",
            "RT",
            "Overlay (RT)",
            "Butterfly (MS)",
            "Butterfly (RT)",
            "Butterfly (DT)",
            "Subtract (MS)",
            "Subtract (RT)",
            "Subtract (DT)",
            "Waterfall (MS)",
            "Waterfall (RT)",
            "Waterfall (DT)",
            "Overlay (MS)",
        ]:

            if method == "Grid (n x n)":
                self.data_visualisation.on_show_overlay_heatmap_grid_nxn(data, set_page=True)
            elif method == "Grid (2":
                self.data_visualisation.on_show_overlay_heatmap_grid_2to1(data, set_page=True)
            elif method == "Mask":
                self.data_visualisation.on_show_overlay_heatmap_mask(data, set_page=True)
            elif method == "Transparent":
                self.data_visualisation.on_show_overlay_heatmap_transparent(data, set_page=True)
            elif method == "RMSF":
                self.data_visualisation.on_show_overlay_heatmap_rmsf(data, set_page=True)
            elif method == "RGB":
                self.data_visualisation.on_show_overlay_heatmap_rgb(data, set_page=True)
            elif method == "RMSD":
                self.data_visualisation.on_show_overlay_heatmap_rmsd(data, set_page=True)
            elif method in ["Variance", "Mean", "Standard Deviation"]:
                self.data_visualisation.on_show_overlay_heatmap_statistical(data, set_page=True)
            elif method == "RMSD Matrix":
                self.data_visualisation.on_show_overlay_heatmap_rmsd_matrix(data, set_page=True)
            # Overlayed 1D data
            elif method in ["1D", "Overlay (DT)"]:
                self.data_visualisation.on_show_overlay_spectrum_overlay(data, "mobilogram", set_page=True)
            elif method in ["RT", "Overlay (RT)"]:
                self.data_visualisation.on_show_overlay_spectrum_overlay(data, "chromatogram", set_page=True)
            elif method in ["Overlay (MS)"]:
                self.data_visualisation.on_show_overlay_spectrum_overlay(data, "mass_spectra", set_page=True)
            elif method in ["Butterfly (MS)", "Butterfly (RT)", "Butterfly (DT)"]:
                self.data_visualisation.on_show_overlay_spectrum_butterfly(data, set_page=True)
            elif method in ["Subtract (MS)", "Subtract (RT)", "Subtract (DT)"]:
                self.data_visualisation.on_show_overlay_spectrum_butterfly(data, set_page=True)
            elif method in ["Waterfall (MS)", "Waterfall (RT)", "Waterfall (DT)"]:
                self.data_visualisation.on_show_overlay_spectrum_waterfall(data, set_page=True)

            # save plot
            if save_image:
                self.panel_plot.save_images(evt="overlay", image_name=save_filename)
                return

        elif method in [
            "Waterfall (Raw)",
            "Waterfall (Processed)",
            "Waterfall (Fitted)",
            "Waterfall (Deconvoluted MW)",
            "Waterfall (Charge states)",
        ]:
            self.panel_plot.on_plot_waterfall(
                data["xvals"],
                data["yvals"],
                None,
                colors=data["colors"],
                xlabel=data["xlabel"],
                ylabel=data["ylabel"],
                set_page=True,
                **data["waterfall_kwargs"],
            )
        elif method == "Waterfall overlay":
            self.panel_plot.on_plot_waterfall_overlay(
                data["xvals"],
                data["yvals"],
                data["zvals"],
                data["colors"],
                data["xlabel"],
                data["ylabel"],
                data["labels"],
                set_page=True,
            )

        if save_image:
            self.panel_plot.save_images(evt="waterfall", image_name=save_filename)

    def on_show_plot(self, evt, save_image=False):
        """ This will send data, plot and change window"""
        if self._document_data is None:
            return

        if isinstance(evt, int):
            evtID = evt
        elif evt is None:
            evtID = None
        else:
            evtID = evt.GetId()

        _click_obj = self._document_type
        # show annotated data
        if _click_obj in "Annotated data":
            # exit early if user clicked on the header
            if self._item_leaf == "Annotated data":
                return

            # open annotations
            if self._item_leaf == "Annotations":
                self.on_open_annotation_editor(None)
                return

            data = deepcopy(self.GetPyData(self._item_id))
            self.on_show_plot_annotated_data(data, save_image)

        # show tandem MS
        elif _click_obj == "Tandem Mass Spectra":
            if self._item_leaf == "Tandem Mass Spectra":
                data = self._document_data.tandem_spectra
                kwargs = {"document": self._document_data.title, "tandem_spectra": data}
                self.on_open_MSMS_viewer(**kwargs)
                return

        # show mass spectrum
        elif any(_click_obj in _item for _item in ["Mass Spectrum", "Mass Spectra", "Mass Spectrum (processed)"]):
            self.on_show_plot_mass_spectra(save_image)

        # show mobilogram
        elif any(
            _click_obj in _item
            for _item in [
                "Drift time (1D)",
                "Drift time (1D, EIC, DT-IMS)",
                "Drift time (1D, EIC)",
                "Calibration peaks",
                "Calibrants",
            ]
        ):
            self.on_show_plot_mobilogram(evtID, save_image)

        # show chromatogram
        elif any(
            _click_obj in _item
            for _item in ["Chromatogram", "Chromatograms (EIC)", "Chromatograms (combined voltages, EIC)"]
        ):
            self.on_show_plot_chromatogram(evtID, save_image)

        # show heatmap
        elif any(
            _click_obj in _item
            for _item in [
                "Drift time (2D)",
                "Drift time (2D, processed)",
                "Drift time (2D, EIC)",
                "Drift time (2D, combined voltages, EIC)",
                "Drift time (2D, processed, EIC)",
                "Input data",
            ]
        ):
            self.on_show_plot_heatmap(evtID, save_image)

        # show overlay / statistical plots
        elif _click_obj in ["Overlay", "Statistical"]:
            self.on_show_plot_overlay(save_image)

        # show dt/ms plot
        elif _click_obj == "DT/MS" or evtID in [ID_ylabel_DTMS_bins, ID_ylabel_DTMS_ms, ID_ylabel_DTMS_restore]:
            self.on_show_plot_dtms(save_image)

    def onSaveDF(self, evt):

        print("Saving dataframe...")
        tstart = time.time()

        if self._document_type == "Mass Spectra" and self._item_leaf == "Mass Spectra":
            dataframe = self._document_data.massSpectraSave
            if len(self._document_data.massSpectraSave) == 0:
                msFilenames = ["m/z"]
                for i, key in enumerate(self._document_data.multipleMassSpectrum):
                    msY = self._document_data.multipleMassSpectrum[key]["yvals"]
                    if self.config.normalizeMultipleMS:
                        msY = msY / max(msY)
                    msFilenames.append(key)
                    if i == 0:
                        tempArray = msY
                    else:
                        tempArray = np.concatenate((tempArray, msY), axis=0)
                try:
                    # Form pandas dataframe
                    msX = self._document_data.multipleMassSpectrum[key]["xvals"]
                    combMSOut = np.concatenate((msX, tempArray), axis=0)
                    combMSOut = combMSOut.reshape((len(msY), int(i + 2)), order="F")
                    dataframe = pd.DataFrame(data=combMSOut, columns=msFilenames)
                except Exception:
                    self.presenter.view.SetStatusText(
                        "Mass spectra are not of the same size. Please export each item separately", 3
                    )
            try:
                # Save data
                if evt.GetId() == ID_saveData_csv:
                    filename = self.presenter.getImageFilename(
                        defaultValue="MS_multiple", withPath=True, extension=self.config.saveExtension
                    )
                    if filename is None:
                        return
                    dataframe.to_csv(path_or_buf=filename, sep=self.config.saveDelimiter, header=True, index=True)
                elif evt.GetId() == ID_saveData_pickle:
                    filename = self.presenter.getImageFilename(
                        defaultValue="MS_multiple", withPath=True, extension=".pickle"
                    )
                    if filename is None:
                        return
                    dataframe.to_pickle(path=filename, protocol=2)
                elif evt.GetId() == ID_saveData_excel:
                    filename = self.presenter.getImageFilename(
                        defaultValue="MS_multiple", withPath=True, extension=".xlsx"
                    )
                    if filename is None:
                        return
                    dataframe.to_excel(excel_writer=filename, sheet_name="data")
                elif evt.GetId() == ID_saveData_hdf:
                    filename = self.presenter.getImageFilename(
                        defaultValue="MS_multiple", withPath=True, extension=".h5"
                    )
                    if filename is None:
                        return
                    dataframe.to_hdf(path_or_buf=filename, key="data")

                print(
                    "Dataframe was saved in {}. It took: {} s.".format(filename, str(np.round(time.time() - tstart, 4)))
                )
            except AttributeError:
                args = (
                    "This document does not have correctly formatted MS data. Please export each item separately",
                    4,
                )
                self.presenter.onThreading(None, args, action="updateStatusbar")

    def onSaveData(self, data=None, labels=None, data_format="%.4f", **kwargs):
        """
        Helper function to save data in consistent manner
        """
        wildcard = (
            "CSV (Comma delimited) (*.csv)|*.csv|"
            + "Text (Tab delimited) (*.txt)|*.txt|"
            + "Text (Space delimited (*.txt)|*.txt"
        )

        wildcard_dict = {",": 0, "\t": 1, " ": 2}

        if kwargs.get("ask_permission", False):
            style = wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
        else:
            style = wx.FD_SAVE

        dlg = wx.FileDialog(
            self.presenter.view, "Please select a name for the file", "", "", wildcard=wildcard, style=style
        )
        dlg.CentreOnParent()

        if "default_name" in kwargs:
            defaultName = kwargs.pop("default_name")
        else:
            defaultName = ""
        defaultName = (
            defaultName.replace(" ", "")
            .replace(":", "")
            .replace(" ", "")
            .replace(".csv", "")
            .replace(".txt", "")
            .replace(".raw", "")
            .replace(".d", "")
            .replace(".", "_")
        )

        dlg.SetFilename(defaultName)

        try:
            dlg.SetFilterIndex(wildcard_dict[self.config.saveDelimiter])
        except Exception:
            pass

        if not kwargs.get("return_filename", False):
            if dlg.ShowModal() == wx.ID_OK:
                filename = dlg.GetPath()
                __, extension = os.path.splitext(filename)
                self.config.saveExtension = extension
                self.config.saveDelimiter = list(wildcard_dict.keys())[
                    list(wildcard_dict.values()).index(dlg.GetFilterIndex())
                ]
                saveAsText(
                    filename=filename,
                    data=data,
                    format=data_format,
                    delimiter=self.config.saveDelimiter,
                    header=self.config.saveDelimiter.join(labels),
                )
            else:
                self.presenter.onThreading(None, ("Cancelled operation", 4, 5), action="updateStatusbar")
        else:
            if dlg.ShowModal() == wx.ID_OK:
                filename = dlg.GetPath()
                basename, extension = os.path.splitext(filename)

                return filename, basename, extension
            else:
                return None, None, None

    def onSaveCSV(self, evt):
        """
        This function extracts the 1D or 2D data and saves it in a CSV format
        """
        if self._document_data is None:
            return

        saveFileName = None
        basename = os.path.splitext(self._document_data.title)[0]
        # Save MS - single
        if (
            self._document_type == "Mass Spectrum"
            or self._document_type == "Mass Spectrum (processed)"
            or self._document_type == "Mass Spectra"
            and self.extractData != self._document_type
        ):
            # Default name
            defaultValue = "MSout"
            # Saves MS to file. Automatically removes values with 0s from the array
            # Get data
            if self._document_type == "Mass Spectrum":
                data = self._document_data.massSpectrum
                defaultValue = "MS_{}{}".format(basename, self.config.saveExtension)
            elif self._document_type == "Mass Spectrum (processed)":
                data = self._document_data.smoothMS
                defaultValue = "MS_processed_{}{}".format(basename, self.config.saveExtension)
            elif self._document_type == "Mass Spectra" and self._item_leaf != self._document_type:
                data = self._document_data.multipleMassSpectrum[self._item_leaf]
                extractBasename = os.path.splitext(self._item_leaf)[0]
                defaultValue = "MS_{}_{}{}".format(basename, extractBasename, self.config.saveExtension).replace(
                    ":", ""
                )

            # Extract MS and find where items are equal to 0 = to reduce filesize
            msX = data["xvals"]
            msXzero = np.where(msX == 0)[0]
            msY = data["yvals"]
            msYzero = np.where(msY == 0)[0]
            # Find which index to use for removal
            removeIdx = np.concatenate((msXzero, msYzero), axis=0)
            msXnew = np.delete(msX, removeIdx)
            msYnew = np.delete(msY, removeIdx)

            kwargs = {"default_name": defaultValue}
            data = [msXnew, msYnew]
            labels = ["m/z", "Intensity"]
            self.data_handling.on_save_data_as_text(data=data, labels=labels, data_format="%.4f", **kwargs)

        # Save MS - multiple MassLynx fiels
        elif self._document_type == "Mass Spectra" and self._item_leaf == "Mass Spectra":
            for key in self._document_data.multipleMassSpectrum:
                stripped_key_name = clean_filename(key)
                defaultValue = "MS_{}_{}{}".format(basename, stripped_key_name, self.config.saveExtension)
                msX = self._document_data.multipleMassSpectrum[key]["xvals"]
                msY = self._document_data.multipleMassSpectrum[key]["yvals"]
                # Extract MS and find where items are equal to 0 = to reduce filesize
                msXzero = np.where(msX == 0)[0]
                msYzero = np.where(msY == 0)[0]
                # Find which index to use for removal
                removeIdx = np.concatenate((msXzero, msYzero), axis=0)
                msXnew = np.delete(msX, removeIdx)
                msYnew = np.delete(msY, removeIdx)
                xlabel = "m/z(Da)"
                data = [msXnew, msYnew]
                kwargs = {"default_name": defaultValue}
                self.data_handling.on_save_data_as_text(
                    data=data, labels=[xlabel, "Intensity"], data_format="%.4f", **kwargs
                )

        # Save calibration parameters - single
        elif self._document_type == "Calibration Parameters":
            if evt.GetId() == ID_saveDataCSVDocument:
                saveFileName = self.presenter.getImageFilename(prefix=True, csv=True, defaultValue="calibrationTable")
                if saveFileName == "" or saveFileName is None:
                    saveFileName = "calibrationTable"

            filename = "".join([self._document_data.path, "\\", saveFileName, self.config.saveExtension])

            df = self._document_data.calibrationParameters["dataframe"]
            df.to_csv(path_or_buf=filename, sep=self.config.saveDelimiter)

        # Save RT - single
        elif self._document_type == "Chromatogram":
            if evt.GetId() == ID_saveDataCSVDocument:
                defaultValue = "RT_{}{}".format(basename, self.config.saveExtension)
                rtX = self._document_data.RT["xvals"]
                rtY = self._document_data.RT["yvals"]
                xlabel = self._document_data.RT["xlabels"]
                kwargs = {"default_name": defaultValue}
                self.data_handling.on_save_data_as_text(
                    data=[rtX, rtY], labels=[xlabel, "Intensity"], data_format="%.4f", **kwargs
                )

        # Save 1D - single
        elif self._document_type == "Drift time (1D)":
            if evt.GetId() == ID_saveDataCSVDocument:
                defaultValue = "DT_1D_{}{}".format(basename, self.config.saveExtension)
                dtX = self._document_data.DT["xvals"]
                dtY = self._document_data.DT["yvals"]
                ylabel = self._document_data.DT["xlabels"]
                kwargs = {"default_name": defaultValue}
                self.data_handling.on_save_data_as_text(
                    data=[dtX, dtY], labels=[ylabel, "Intensity"], data_format="%.2f", **kwargs
                )

        # Save RT (combined voltages) - batch + single
        elif self._document_type == "Chromatograms (combined voltages, EIC)":
            # Batch mode
            if self._item_leaf == "Chromatograms (combined voltages, EIC)":
                for key in self._document_data.IMSRTCombIons:
                    stripped_key_name = key.replace(" ", "")
                    defaultValue = "RT_{}_{}{}".format(basename, stripped_key_name, self.config.saveExtension)
                    rtX = self._document_data.IMSRTCombIons[key]["xvals"]
                    rtY = self._document_data.IMSRTCombIons[key]["yvals"]
                    xlabel = self._document_data.IMSRTCombIons[key]["xlabels"]
                    kwargs = {"default_name": defaultValue}
                    self.data_handling.on_save_data_as_text(
                        data=[rtX, rtY], labels=[xlabel, "Intensity"], data_format="%.4f", **kwargs
                    )
            #             # Single mode
            else:
                defaultValue = "RT_{}_{}{}".format(basename, self._item_leaf, self.config.saveExtension)
                rtX = self._document_data.IMSRTCombIons[self._item_leaf]["xvals"]
                rtY = self._document_data.IMSRTCombIons[self._item_leaf]["yvals"]
                xlabel = self._document_data.IMSRTCombIons[self._item_leaf]["xlabels"]
                kwargs = {"default_name": defaultValue}
                self.data_handling.on_save_data_as_text(
                    data=[rtX, rtY], labels=[xlabel, "Intensity"], data_format="%.4f", **kwargs
                )

        # Save 1D - batch + single
        elif self._document_type == "Drift time (1D, EIC, DT-IMS)":
            if evt.GetId() == ID_saveDataCSVDocument:
                saveFileName = self.presenter.getImageFilename(prefix=True, csv=True, defaultValue="DT_1D_")
                if saveFileName == "" or saveFileName is None:
                    saveFileName = "DT_1D_"
            # Batch mode
            if self._item_leaf == "Drift time (1D, EIC, DT-IMS)":
                for key in self._document_data.IMS1DdriftTimes:
                    if self._document_data.dataType == "Type: MANUAL":
                        name = re.split(", File: |.raw", key)
                        filename = "".join(
                            [
                                self._document_data.path,
                                "\\",
                                saveFileName,
                                name[0],
                                "_",
                                name[1],
                                self.config.saveExtension,
                            ]
                        )
                        dtX = self._document_data.IMS1DdriftTimes[key]["xvals"]
                        dtY = self._document_data.IMS1DdriftTimes[key]["yvals"]
                        xlabel = self._document_data.IMS1DdriftTimes[key]["xlabels"]
                        saveAsText(
                            filename=filename,
                            data=[dtX, dtY],
                            format="%.4f",
                            delimiter=self.config.saveDelimiter,
                            header=self.config.saveDelimiter.join([xlabel, "Intensity"]),
                        )
                    else:
                        filename = "".join(
                            [self._document_data.path, "\\", saveFileName, key, self.config.saveExtension]
                        )
                        zvals = self._document_data.IMS1DdriftTimes[key]["yvals"]
                        yvals = self._document_data.IMS1DdriftTimes[key]["xvals"]
                        xvals = np.asarray(self._document_data.IMS1DdriftTimes[key]["driftVoltage"])
                        # Y-axis labels need a value for [0,0]
                        yvals = np.insert(yvals, 0, 0)  # array, index, value
                        # Combine x-axis with data
                        saveData = np.vstack((xvals, zvals.T))
                        saveData = np.vstack((yvals, saveData.T))
                        # Save data
                        saveAsText(
                            filename=filename,
                            data=saveData,
                            format="%.2f",
                            delimiter=self.config.saveDelimiter,
                            header="",
                        )

            # Single mode
            else:
                if self._document_data.dataType == "Type: MANUAL":
                    name = re.split(", File: |.raw", self._item_leaf)
                    filename = "".join(
                        [self._document_data.path, "\\", saveFileName, name[0], "_", name[1], self.config.saveExtension]
                    )
                    dtX = self._document_data.IMS1DdriftTimes[self._item_leaf]["xvals"]
                    dtY = self._document_data.IMS1DdriftTimes[self._item_leaf]["yvals"]
                    xlabel = self._document_data.IMS1DdriftTimes[self._item_leaf]["xlabels"]
                    saveAsText(
                        filename=filename,
                        data=[dtX, dtY],
                        format="%.4f",
                        delimiter=self.config.saveDelimiter,
                        header=self.config.saveDelimiter.join([xlabel, "Intensity"]),
                    )
                else:
                    filename = "".join(
                        [self._document_data.path, "\\", saveFileName, self._item_leaf, self.config.saveExtension]
                    )
                    zvals = self._document_data.IMS1DdriftTimes[self._item_leaf]["yvals"]
                    yvals = self._document_data.IMS1DdriftTimes[self._item_leaf]["xvals"]
                    xvals = np.asarray(self._document_data.IMS1DdriftTimes[self._item_leaf].get("driftVoltage", " "))
                    # Y-axis labels need a value for [0,0]
                    yvals = np.insert(yvals, 0, 0)  # array, index, value
                    # Combine x-axis with data
                    saveData = np.vstack((xvals, zvals.T))
                    saveData = np.vstack((yvals, saveData.T))
                    saveAsText(
                        filename=filename, data=saveData, format="%.2f", delimiter=self.config.saveDelimiter, header=""
                    )
        # Save DT/MS
        elif self._document_type == "DT/MS":
            data = self.GetPyData(self._item_id)
            zvals = data["zvals"]
            xvals = data["xvals"]
            yvals = data["yvals"]

            if evt.GetId() == ID_saveDataCSVDocument:
                defaultValue = "MSDT_{}{}".format(basename, self.config.saveExtension)
                saveData = np.vstack((xvals, zvals))
                xvals = list(map(str, xvals.tolist()))
                labels = ["DT"]
                labels.extend(yvals)
                fmts = ["%.4f"] + ["%i"] * len(yvals)
                # Save 2D array
                kwargs = {"default_name": defaultValue}
                self.data_handling.on_save_data_as_text(data=[saveData], labels=labels, data_format=fmts, **kwargs)

        # Save 1D/2D - batch + single
        elif any(
            self._document_type in itemType
            for itemType in [
                "Drift time (2D)",
                "Drift time (2D, processed)",
                "Drift time (2D, EIC)",
                "Drift time (2D, combined voltages, EIC)",
                "Drift time (2D, processed, EIC)",
                "Input data",
                "Statistical",
            ]
        ):
            # Select dataset
            if self._document_type in ["Drift time (2D)", "Drift time (2D, processed)"]:
                if self._document_type == "Drift time (2D)":
                    data = self._document_data.IMS2D
                    defaultValue = "DT_2D_raw_{}{}".format(basename, self.config.saveExtension)

                elif self._document_type == "Drift time (2D, processed)":
                    data = self._document_data.IMS2Dprocess
                    defaultValue = "DT_2D_processed_{}{}".format(basename, self.config.saveExtension)

                # Save 2D
                if evt.GetId() == ID_saveDataCSVDocument:
                    # Prepare data for saving
                    zvals, xvals, xlabel, yvals, ylabel, __ = self.presenter.get2DdataFromDictionary(
                        dictionary=data, dataType="plot", compact=False
                    )
                    saveData = np.vstack((yvals, zvals.T))
                    xvals = list(map(str, xvals.tolist()))
                    labels = ["DT"]
                    for label in xvals:
                        labels.append(label)
                    # Save 2D array
                    kwargs = {"default_name": defaultValue}
                    self.data_handling.on_save_data_as_text(
                        data=[saveData], labels=labels, data_format="%.2f", **kwargs
                    )

                # Save 1D
                elif evt.GetId() == ID_saveDataCSVDocument1D:
                    if self._document_type == "Drift time (2D)":
                        defaultValue = "DT_1D_raw_{}{}".format(basename, self.config.saveExtension)

                    elif self._document_type == "Drift time (2D, processed)":
                        defaultValue = "DT_1D_processed_{}{}".format(basename, self.config.saveExtension)
                    # Get data from the document
                    dtX = data["yvals"]
                    ylabel = data["xlabels"]
                    try:
                        dtY = data["yvals1D"]
                    except KeyError:
                        msg = "Missing data. Cancelling operation."
                        self.presenter.view.SetStatusText(msg, 3)
                        return
                    kwargs = {"default_name": defaultValue}
                    self.data_handling.on_save_data_as_text(
                        data=[dtX, dtY], labels=[ylabel, "Intensity"], data_format="%.4f", **kwargs
                    )

            # Save 1D/2D - single + batch
            elif any(
                self._document_type in itemType
                for itemType in [
                    "Drift time (2D, EIC)",
                    "Drift time (2D, combined voltages, EIC)",
                    "Drift time (2D, processed, EIC)",
                    "Input data",
                    "Statistical",
                ]
            ):
                # Save 1D/2D - batch
                if any(
                    self._item_leaf in extractData
                    for extractData in [
                        "Drift time (2D, EIC)",
                        "Drift time (2D, combined voltages, EIC)",
                        "Drift time (2D, processed, EIC)",
                        "Input data",
                        "Statistical",
                    ]
                ):
                    name_modifier = ""
                    if self._document_type == "Drift time (2D, EIC)":
                        data = self._document_data.IMS2Dions
                    elif self._document_type == "Drift time (2D, combined voltages, EIC)":
                        data = self._document_data.IMS2DCombIons
                        name_modifier = "_CV_"
                    elif self._document_type == "Drift time (2D, processed, EIC)":
                        data = self._document_data.IMS2DionsProcess
                    elif self._document_type == "Input data":
                        data = self._document_data.IMS2DcompData
                    elif self._document_type == "Statistical":
                        data = self._document_data.IMS2DstatsData

                    # 2D - batch
                    if evt.GetId() == ID_saveDataCSVDocument:
                        # Iterate over dictionary
                        for key in data:
                            stripped_key_name = key.replace(" ", "")
                            defaultValue = "DT_2D_{}_{}{}{}".format(
                                basename, name_modifier, stripped_key_name, self.config.saveExtension
                            )
                            # Prepare data for saving
                            zvals, xvals, xlabel, yvals, ylabel, __ = self.presenter.get2DdataFromDictionary(
                                dictionary=data[key], dataType="plot", compact=False
                            )
                            saveData = np.vstack((yvals, zvals.T))
                            xvals = list(map(str, xvals.tolist()))
                            labels = ["DT"]
                            for label in xvals:
                                labels.append(label)
                            # Save 2D array
                            kwargs = {"default_name": defaultValue}
                            self.data_handling.on_save_data_as_text(
                                data=[saveData], labels=labels, data_format="%.2f", **kwargs
                            )
                    # 1D - batch
                    elif evt.GetId() == ID_saveDataCSVDocument1D:
                        if not (self._document_type == "Input data" or self._document_type == "Statistical"):
                            for key in data:
                                stripped_key_name = key.replace(" ", "")
                                defaultValue = "DT_1D_{}_{}{}{}".format(
                                    basename, name_modifier, stripped_key_name, self.config.saveExtension
                                )
                                # Get data from the document
                                dtX = data[key]["yvals"]
                                ylabel = data[key]["xlabels"]
                                try:
                                    dtY = data[key]["yvals1D"]
                                except KeyError:
                                    msg = "Missing data. Cancelling operation."
                                    self.presenter.view.SetStatusText(msg, 3)
                                    continue
                                kwargs = {"default_name": defaultValue}
                                self.data_handling.on_save_data_as_text(
                                    data=[dtX, dtY], labels=[ylabel, "Intensity"], data_format="%.4f", **kwargs
                                )

                # Save 1D/2D - single
                else:
                    name_modifier = ""
                    if self._document_type == "Drift time (2D, EIC)":
                        data = self._document_data.IMS2Dions
                    elif self._document_type == "Drift time (2D, combined voltages, EIC)":
                        data = self._document_data.IMS2DCombIons
                        name_modifier = "_CV_"
                    elif self._document_type == "Drift time (2D, processed, EIC)":
                        data = self._document_data.IMS2DionsProcess
                    elif self._document_type == "Input data":
                        data = self._document_data.IMS2DcompData
                    elif self._document_type == "Statistical":
                        data = self._document_data.IMS2DstatsData
                    # Save RMSD matrix
                    out = self._item_leaf.split(":")
                    if out[0] == "RMSD Matrix":
                        if evt.GetId() == ID_saveDataCSVDocument:
                            saveFileName = self.presenter.getImageFilename(prefix=True, csv=True, defaultValue="DT_")
                        if saveFileName == "" or saveFileName is None:
                            saveFileName = "DT_"

                        # Its a bit easier to save data with text labels using pandas df,
                        # so data is reshuffled to pandas dataframe and then saved
                        # in a standard .csv format
                        filename = "".join(
                            [self._document_data.path, "\\", saveFileName, self._item_leaf, self.config.saveExtension]
                        )
                        zvals, xylabels, __ = self.presenter.get2DdataFromDictionary(
                            dictionary=data[self._item_leaf], plotType="Matrix", compact=False
                        )
                        saveData = pd.DataFrame(data=zvals, index=xylabels, columns=xylabels)
                        saveData.to_csv(path_or_buf=filename, sep=self.config.saveDelimiter, header=True, index=True)
                    # Save 2D - single
                    elif self._item_leaf != "RMSD Matrix" and evt.GetId() == ID_saveDataCSVDocument:
                        defaultValue = "DT_2D_{}_{}{}{}".format(
                            basename, name_modifier, self._item_leaf, self.config.saveExtension
                        )

                        zvals, xvals, xlabel, yvals, ylabel, __ = self.presenter.get2DdataFromDictionary(
                            dictionary=data[self._item_leaf], dataType="plot", compact=False
                        )
                        saveData = np.vstack((yvals, zvals.T))
                        try:
                            xvals = list(map(str, xvals.tolist()))
                        except AttributeError:
                            xvals = list(map(str, xvals))
                        labels = ["DT"]
                        for label in xvals:
                            labels.append(label)
                        # Save 2D array
                        kwargs = {"default_name": defaultValue}
                        self.data_handling.on_save_data_as_text(
                            data=[saveData], labels=labels, data_format="%.2f", **kwargs
                        )
                    # Save 1D - single
                    elif self._item_leaf != "RMSD Matrix" and evt.GetId() == ID_saveDataCSVDocument1D:
                        defaultValue = "DT_1D_{}_{}{}{}".format(
                            basename, name_modifier, self._item_leaf, self.config.saveExtension
                        )

                        # Get data from the document
                        dtX = data[self._item_leaf]["yvals"]
                        ylabel = data[self._item_leaf]["xlabels"]
                        try:
                            dtY = data[self._item_leaf]["yvals1D"]
                        except KeyError:
                            msg = "Missing data. Cancelling operation."
                            self.presenter.view.SetStatusText(msg, 3)
                            return
                        kwargs = {"default_name": defaultValue}
                        self.data_handling.on_save_data_as_text(
                            data=[dtX, dtY], labels=[ylabel, "Intensity"], data_format="%.4f", **kwargs
                        )
        else:
            return

    def onOpenDocInfo(self, evt):

        self.presenter.currentDoc = self.on_enable_document()
        document_title = self.on_enable_document()
        if self.presenter.currentDoc == "Documents":
            return
        document = self.presenter.documentsDict.get(document_title, None)

        if document is None:
            return

        for key in self.presenter.documentsDict:
            print(self.presenter.documentsDict[key].title)

        if self._indent == 2 and any(
            self._document_type in itemType for itemType in ["Drift time (2D)", "Drift time (2D, processed)"]
        ):
            kwargs = {"currentTool": "plot2D", "itemType": self._document_type, "extractData": None}
            self.panelInfo = PanelDocumentInformation(self, self.presenter, self.config, self.icons, document, **kwargs)
        elif self._indent == 3 and any(
            self._document_type in itemType
            for itemType in [
                "Drift time (2D, EIC)",
                "Drift time (2D, combined voltages, EIC)",
                "Drift time (2D, processed, EIC)",
                "Input data",
            ]
        ):
            kwargs = {"currentTool": "plot2D", "itemType": self._document_type, "extractData": self._item_leaf}
            self.panelInfo = PanelDocumentInformation(self, self.presenter, self.config, self.icons, document, **kwargs)
        else:

            kwargs = {"currentTool": "summary", "itemType": None, "extractData": None}
            self.panelInfo = PanelDocumentInformation(self, self.presenter, self.config, self.icons, document, **kwargs)

        self.panelInfo.Show()

    def _add_annotation_to_object(self, data, root_obj, check=False):
        if check:
            child, cookie = self.GetFirstChild(root_obj)
            while child.IsOk():
                if self.GetItemText(child) == "Annotations":
                    self.Delete(child)
                child, cookie = self.GetNextChild(root_obj, cookie)

        # add annotations
        if "annotations" in data and len(data["annotations"]) > 0:
            branch_item = self.AppendItem(root_obj, "Annotations")
            self.SetItemImage(branch_item, self.bullets_dict["annot"], wx.TreeItemIcon_Normal)

    def _add_unidec_to_object(self, data, root_obj, check=False):
        if check:
            child, cookie = self.GetFirstChild(root_obj)
            while child.IsOk():
                if self.GetItemText(child) == "UniDec":
                    self.Delete(child)
                child, cookie = self.GetNextChild(root_obj, cookie)

        # add unidec results
        if "unidec" in data:
            branch_item = self.AppendItem(root_obj, "UniDec")
            self.SetItemImage(branch_item, self.bullets_dict["mass_spec"], wx.TreeItemIcon_Normal)
            for unidec_name in data["unidec"]:
                leaf_item = self.AppendItem(branch_item, unidec_name)
                self.SetPyData(leaf_item, data["unidec"][unidec_name])
                self.SetItemImage(leaf_item, self.bullets_dict["mass_spec"], wx.TreeItemIcon_Normal)

    def add_document(self, docData, expandAll=False, expandItem=None):
        """Add document to the document tree"""

        # Get title for added data
        title = byte2str(docData.title)

        if not title:
            title = "Document"
        # Get root
        root = self.GetRootItem()

        item, cookie = self.GetFirstChild(self.GetRootItem())
        while item.IsOk():
            if self.GetItemText(item) == title:
                self.Delete(item)
            item, cookie = self.GetNextChild(root, cookie)

        # update document with new attributes
        if not hasattr(docData, "other_data"):
            setattr(docData, "other_data", {})
            logger.info("Added missing attributute ('other_data') to document")

        if not hasattr(docData, "tandem_spectra"):
            setattr(docData, "tandem_spectra", {})
            logger.info("Added missing attributute ('tandem_spectra') to document")

        if not hasattr(docData, "file_reader"):
            setattr(docData, "file_reader", {})
            logger.info("Added missing attributute ('file_reader') to document")

        if not hasattr(docData, "app_data"):
            setattr(docData, "app_data", {})
            logger.info("Added missing attributute ('app_data') to document")

        if not hasattr(docData, "last_saved"):
            setattr(docData, "last_saved", {})
            logger.info("Added missing attributute ('last_saved') to document")

        if not hasattr(docData, "metadata"):
            setattr(docData, "metadata", {})
            logger.info("Added missing attributute ('metadata') to document")

        # update document to latest version

        # Add document
        docItem = self.AppendItem(self.GetRootItem(), title)
        self.SetFocusedItem(docItem)
        self.SetItemImage(docItem, self.bullets_dict["document_on"], wx.TreeItemIcon_Normal)
        self.title = title
        self.SetPyData(docItem, docData)

        # Add annotations to document tree
        if hasattr(docData, "dataType"):
            annotsItem = self.AppendItem(docItem, docData.dataType)
            self.SetItemImage(annotsItem, self.bullets_dict["annot_on"], wx.TreeItemIcon_Normal)
            self.SetPyData(annotsItem, docData.dataType)

        if hasattr(docData, "fileFormat"):
            annotsItem = self.AppendItem(docItem, docData.fileFormat)
            self.SetItemImage(annotsItem, self.bullets_dict["annot_on"], wx.TreeItemIcon_Normal)
            self.SetPyData(annotsItem, docData.fileFormat)

        if hasattr(docData, "fileInformation"):
            if docData.fileInformation is not None:
                annotsItem = self.AppendItem(docItem, "Sample information")
                self.SetPyData(annotsItem, docData.fileInformation)
                self.SetItemImage(annotsItem, self.bullets_dict["annot_on"], wx.TreeItemIcon_Normal)

        if docData.massSpectrum:
            annotsItemParent = self.AppendItem(docItem, "Mass Spectrum")
            self.SetPyData(annotsItemParent, docData.massSpectrum)
            self.SetItemImage(annotsItemParent, self.bullets_dict["mass_spec"], wx.TreeItemIcon_Normal)
            self._add_unidec_to_object(docData.massSpectrum, annotsItemParent)
            self._add_annotation_to_object(docData.massSpectrum, annotsItemParent)

        if docData.smoothMS:
            annotsItemParent = self.AppendItem(docItem, "Mass Spectrum (processed)")
            self.SetItemImage(annotsItemParent, self.bullets_dict["mass_spec"], wx.TreeItemIcon_Normal)
            self.SetPyData(annotsItemParent, docData.smoothMS)
            self._add_unidec_to_object(docData.smoothMS, annotsItemParent)
            self._add_annotation_to_object(docData.smoothMS, annotsItemParent)

        if docData.multipleMassSpectrum:
            docIonItem = self.AppendItem(docItem, "Mass Spectra")
            self.SetItemImage(docIonItem, self.bullets_dict["mass_spec"], wx.TreeItemIcon_Normal)
            self.SetPyData(docIonItem, docData.multipleMassSpectrum)
            for annotData in docData.multipleMassSpectrum:
                annotsItem = self.AppendItem(docIonItem, annotData)
                self.SetPyData(annotsItem, docData.multipleMassSpectrum[annotData])
                self.SetItemImage(annotsItem, self.bullets_dict["mass_spec_on"], wx.TreeItemIcon_Normal)
                self._add_unidec_to_object(docData.multipleMassSpectrum[annotData], annotsItem)
                self._add_annotation_to_object(docData.multipleMassSpectrum[annotData], annotsItem)

        if docData.tandem_spectra:
            docIonItem = self.AppendItem(docItem, "Tandem Mass Spectra")
            self.SetItemImage(docIonItem, self.bullets_dict["mass_spec"], wx.TreeItemIcon_Normal)
            self.SetPyData(docIonItem, docData.tandem_spectra)

        if docData.RT:
            annotsItem = self.AppendItem(docItem, "Chromatogram")
            self.SetPyData(annotsItem, docData.RT)
            self.SetItemImage(annotsItem, self.bullets_dict["rt"], wx.TreeItemIcon_Normal)
            self._add_annotation_to_object(docData.RT, annotsItem)

        if docData.multipleRT:
            docIonItem = self.AppendItem(docItem, "Chromatograms (EIC)")
            self.SetItemImage(docIonItem, self.bullets_dict["rt"], wx.TreeItemIcon_Normal)
            self.SetPyData(docIonItem, docData.multipleRT)
            for annotData, __ in natsorted(list(docData.multipleRT.items())):
                annotsItem = self.AppendItem(docIonItem, annotData)
                self.SetPyData(annotsItem, docData.multipleRT[annotData])
                self.SetItemImage(annotsItem, self.bullets_dict["rt_on"], wx.TreeItemIcon_Normal)
                self._add_annotation_to_object(docData.multipleRT[annotData], annotsItem)

        if docData.DT:
            annotsItem = self.AppendItem(docItem, "Drift time (1D)")
            self.SetPyData(annotsItem, docData.DT)
            self.SetItemImage(annotsItem, self.bullets_dict["drift_time"], wx.TreeItemIcon_Normal)
            self._add_annotation_to_object(docData.DT, annotsItem)

        if docData.multipleDT:
            docIonItem = self.AppendItem(docItem, "Drift time (1D, EIC)")
            self.SetItemImage(docIonItem, self.bullets_dict["drift_time"], wx.TreeItemIcon_Normal)
            self.SetPyData(docIonItem, docData.multipleDT)
            for annotData, __ in natsorted(list(docData.multipleDT.items())):
                annotsItem = self.AppendItem(docIonItem, annotData)
                self.SetPyData(annotsItem, docData.multipleDT[annotData])
                self.SetItemImage(annotsItem, self.bullets_dict["drift_time_on"], wx.TreeItemIcon_Normal)
                self._add_annotation_to_object(docData.multipleDT[annotData], annotsItem)

        if docData.IMS1DdriftTimes:
            docIonItem = self.AppendItem(docItem, "Drift time (1D, EIC, DT-IMS)")
            self.SetItemImage(docIonItem, self.bullets_dict["drift_time"], wx.TreeItemIcon_Normal)
            self.SetPyData(docIonItem, docData.IMS1DdriftTimes)
            for annotData, __ in natsorted(list(docData.IMS1DdriftTimes.items())):
                annotsItem = self.AppendItem(docIonItem, annotData)
                self.SetPyData(annotsItem, docData.IMS1DdriftTimes[annotData])
                self.SetItemImage(annotsItem, self.bullets_dict["drift_time_on"], wx.TreeItemIcon_Normal)

        if docData.IMS2D:
            annotsItem = self.AppendItem(docItem, "Drift time (2D)")
            self.SetPyData(annotsItem, docData.IMS2D)
            self.SetItemImage(annotsItem, self.bullets_dict["heatmap"], wx.TreeItemIcon_Normal)
            self._add_annotation_to_object(docData.IMS2D, annotsItem)

        if docData.IMS2Dprocess or len(docData.IMS2Dprocess) > 0:
            annotsItem = self.AppendItem(docItem, "Drift time (2D, processed)")
            self.SetPyData(annotsItem, docData.IMS2Dprocess)
            self.SetItemImage(annotsItem, self.bullets_dict["heatmap"], wx.TreeItemIcon_Normal)
            self._add_annotation_to_object(docData.IMS2Dprocess, annotsItem)

        if docData.IMS2Dions:
            docIonItem = self.AppendItem(docItem, "Drift time (2D, EIC)")
            self.SetItemImage(docIonItem, self.bullets_dict["heatmap"], wx.TreeItemIcon_Normal)
            self.SetPyData(docIonItem, docData.IMS2Dions)
            for annotData, __ in natsorted(list(docData.IMS2Dions.items())):
                annotsItem = self.AppendItem(docIonItem, annotData)
                self.SetPyData(annotsItem, docData.IMS2Dions[annotData])
                self.SetItemImage(annotsItem, self.bullets_dict["heatmap_on"], wx.TreeItemIcon_Normal)
                self._add_annotation_to_object(docData.IMS2Dions[annotData], annotsItem)

        if docData.IMS2DCombIons:
            docIonItem = self.AppendItem(docItem, "Drift time (2D, combined voltages, EIC)")
            self.SetItemImage(docIonItem, self.bullets_dict["heatmap"], wx.TreeItemIcon_Normal)
            self.SetPyData(docIonItem, docData.IMS2DCombIons)
            for annotData, __ in natsorted(list(docData.IMS2DCombIons.items())):
                annotsItem = self.AppendItem(docIonItem, annotData)
                self.SetPyData(annotsItem, docData.IMS2DCombIons[annotData])
                self.SetItemImage(annotsItem, self.bullets_dict["heatmap_on"], wx.TreeItemIcon_Normal)
                self._add_annotation_to_object(docData.IMS2DCombIons[annotData], annotsItem)

        if docData.IMSRTCombIons:
            docIonItem = self.AppendItem(docItem, "Chromatograms (combined voltages, EIC)")
            self.SetItemImage(docIonItem, self.bullets_dict["rt"], wx.TreeItemIcon_Normal)
            self.SetPyData(docIonItem, docData.IMSRTCombIons)
            for annotData, __ in natsorted(list(docData.IMSRTCombIons.items())):
                annotsItem = self.AppendItem(docIonItem, annotData)
                self.SetPyData(annotsItem, docData.IMSRTCombIons[annotData])
                self.SetItemImage(annotsItem, self.bullets_dict["rt_on"], wx.TreeItemIcon_Normal)
                self._add_annotation_to_object(docData.IMSRTCombIons[annotData], annotsItem)

        if docData.IMS2DionsProcess:
            docIonItem = self.AppendItem(docItem, "Drift time (2D, processed, EIC)")
            self.SetItemImage(docIonItem, self.bullets_dict["heatmap"], wx.TreeItemIcon_Normal)
            self.SetPyData(docIonItem, docData.IMS2DionsProcess)
            for annotData, __ in natsorted(list(docData.IMS2DionsProcess.items())):
                annotsItem = self.AppendItem(docIonItem, annotData)
                self.SetPyData(annotsItem, docData.IMS2DionsProcess[annotData])
                self.SetItemImage(annotsItem, self.bullets_dict["heatmap_on"], wx.TreeItemIcon_Normal)
                self._add_annotation_to_object(docData.IMS2DionsProcess[annotData], annotsItem)

        if docData.calibration:
            docIonItem = self.AppendItem(docItem, "Calibration peaks")
            self.SetItemImage(docIonItem, self.bullets_dict["calibration"], wx.TreeItemIcon_Normal)
            for annotData, __ in natsorted(list(docData.calibration.items())):
                annotsItem = self.AppendItem(docIonItem, annotData)
                self.SetPyData(annotsItem, docData.calibration[annotData])
                self.SetItemImage(annotsItem, self.bullets_dict["dots_on"], wx.TreeItemIcon_Normal)

        if docData.calibrationDataset:
            docIonItem = self.AppendItem(docItem, "Calibrants")
            self.SetItemImage(docIonItem, self.bullets_dict["calibration_on"], wx.TreeItemIcon_Normal)
            for annotData in docData.calibrationDataset:
                annotsItem = self.AppendItem(docIonItem, annotData)
                self.SetPyData(annotsItem, docData.calibrationDataset[annotData])
                self.SetItemImage(annotsItem, self.bullets_dict["dots_on"], wx.TreeItemIcon_Normal)

        if docData.calibrationParameters:
            annotsItem = self.AppendItem(docItem, "Calibration parameters")
            self.SetPyData(annotsItem, docData.calibrationParameters)
            self.SetItemImage(annotsItem, self.bullets_dict["calibration"], wx.TreeItemIcon_Normal)

        if docData.IMS2DcompData:
            docIonItem = self.AppendItem(docItem, "Input data")
            self.SetItemImage(docIonItem, self.bullets_dict["overlay"], wx.TreeItemIcon_Normal)
            for annotData, __ in natsorted(list(docData.IMS2DcompData.items())):
                annotsItem = self.AppendItem(docIonItem, annotData)
                self.SetPyData(annotsItem, docData.IMS2DcompData[annotData])
                self.SetItemImage(annotsItem, self.bullets_dict["heatmap_on"], wx.TreeItemIcon_Normal)

        if docData.IMS2DoverlayData or len(docData.IMS2DoverlayData) > 0:
            docIonItem = self.AppendItem(docItem, "Overlay")
            self.SetItemImage(docIonItem, self.bullets_dict["overlay"], wx.TreeItemIcon_Normal)
            self.SetPyData(docIonItem, docData.IMS2DoverlayData)
            for annotData, __ in natsorted(list(docData.IMS2DoverlayData.items())):
                annotsItem = self.AppendItem(docIonItem, annotData)
                self.SetPyData(annotsItem, docData.IMS2DoverlayData[annotData])
                self.SetItemImage(annotsItem, self.bullets_dict["heatmap_on"], wx.TreeItemIcon_Normal)

        if docData.IMS2DstatsData:
            docIonItem = self.AppendItem(docItem, "Statistical")
            self.SetItemImage(docIonItem, self.bullets_dict["overlay"], wx.TreeItemIcon_Normal)
            self.SetPyData(docIonItem, docData.IMS2DstatsData)
            for annotData, __ in natsorted(list(docData.IMS2DstatsData.items())):
                annotsItem = self.AppendItem(docIonItem, annotData)
                self.SetPyData(annotsItem, docData.IMS2DstatsData[annotData])
                self.SetItemImage(annotsItem, self.bullets_dict["heatmap_on"], wx.TreeItemIcon_Normal)

        if docData.DTMZ:
            annotsItem = self.AppendItem(docItem, "DT/MS")
            self.SetPyData(annotsItem, docData.DTMZ)
            self.SetItemImage(annotsItem, self.bullets_dict["heatmap"], wx.TreeItemIcon_Normal)

        if docData.other_data:
            docIonItem = self.AppendItem(docItem, "Annotated data")
            self.SetItemImage(docIonItem, self.bullets_dict["calibration"], wx.TreeItemIcon_Normal)
            self.SetPyData(docIonItem, docData.other_data)
            for annotData, __ in natsorted(list(docData.other_data.items())):
                annotsItem = self.AppendItem(docIonItem, annotData)
                self.SetPyData(annotsItem, docData.other_data[annotData])
                self.SetItemImage(annotsItem, self.bullets_dict["calibration_on"], wx.TreeItemIcon_Normal)
                self._add_annotation_to_object(docData.other_data[annotData], annotsItem)

        # Recursively check currently selected document
        self.on_enable_document(loadingData=True, expandAll=expandAll, evt=None)

        # If expandItem is not empty, the Tree will expand specified item
        if expandItem is not None:
            # Change document tree
            try:
                docItem = self.get_item_by_data(expandItem)
                parent = self.GetItemParent(docItem)
                self.Expand(parent)
            except Exception:
                pass

    def removeDocument(self, evt, deleteItem="", ask_permission=True):
        """
        Remove selected document from the document tree
        """
        # Find the root first
        root = None
        if root is None:
            root = self.GetRootItem()

        try:
            evtID = evt.GetId()
        except AttributeError:
            evtID = None

        if evtID == ID_removeDocument or (evtID is None and deleteItem == ""):
            __, cookie = self.GetFirstChild(self.GetRootItem())

            if ask_permission:
                dlg = DialogBox(
                    exceptionTitle="Are you sure?",
                    exceptionMsg="".join(["Are you sure you would like to delete: ", self._document_data.title, "?"]),
                    type="Question",
                )
                if dlg == wx.ID_NO:
                    self.presenter.onThreading(None, ("Cancelled operation", 4, 5), action="updateStatusbar")
                    return
                else:
                    deleteItem = self._document_data.title

            # Clear all plotsf
            if self.presenter.currentDoc == deleteItem:
                self.panel_plot.on_clear_all_plots()
                self.presenter.currentDoc = None

        if deleteItem == "":
            return

        # Delete item from the list
        if self.ItemHasChildren(root):
            child, cookie = self.GetFirstChild(self.GetRootItem())
            title = self.GetItemText(child)
            iters = 0
            while deleteItem != title and iters < 500:
                child, cookie = self.GetNextChild(self.GetRootItem(), cookie)
                try:
                    title = self.GetItemText(child)
                    iters += 1
                except Exception:
                    pass

            if deleteItem == title:
                if child:
                    print("Deleted {}".format(deleteItem))
                    self.Delete(child)
                    # Remove data from dictionary if removing whole document
                    if evtID == ID_removeDocument or evtID is None:
                        # make sure to clean-up various tables
                        try:
                            self.presenter.view.panelMultipleIons.on_remove_deleted_item(title)
                        except Exception:
                            pass
                        try:
                            self.presenter.view.panelMultipleText.on_remove_deleted_item(title)
                        except Exception:
                            pass
                        try:
                            self.presenter.view.panelMML.on_remove_deleted_item(title)
                        except Exception:
                            pass
                        try:
                            self.presenter.view.panelLinearDT.topP.on_remove_deleted_item(title)
                        except Exception:
                            pass
                        try:
                            self.presenter.view.panelLinearDT.bottomP.on_remove_deleted_item(title)
                        except Exception:
                            pass

                        # delete document
                        del self.presenter.documentsDict[title]
                        self.presenter.currentDoc = None
                        # go to the next document
                        if len(self.presenter.documentsDict) > 0:
                            self.presenter.currentDoc = list(self.presenter.documentsDict.keys())[0]
                            self.on_enable_document()
                        # collect garbage
                        gc.collect()

                    return True
            else:
                return False

    def onShowSampleInfo(self, evt=None):

        try:
            sample_information = self._document_data.fileInformation.get("SampleDescription", "None")
        except AttributeError:
            sample_information = "N/A"

        kwargs = {"title": "Sample information...", "information": sample_information}

        from origami.gui_elements.panel_file_information import PanelInformation

        info = PanelInformation(self, **kwargs)
        info.Show()

    def on_open_MSMS_viewer(self, evt=None, **kwargs):
        from origami.widgets.panel_tandem_spectra_viewer import PanelTandemSpectraViewer

        self.panelTandemSpectra = PanelTandemSpectraViewer(
            self.presenter.view, self.presenter, self.config, self.icons, **kwargs
        )
        self.panelTandemSpectra.Show()

    def on_process_UVPD(self, evt=None, **kwargs):
        from origami.widgets.panel_UVPD_editor import PanelUVPDEditor

        self.panelUVPD = PanelUVPDEditor(self.presenter.view, self.presenter, self.config, self.icons, **kwargs)
        self.panelUVPD.Show()

    def on_open_extract_DTMS(self, evt):
        from origami.gui_elements.panel_process_extract_dtms import PanelProcessExtractDTMS

        self.PanelProcessExtractDTMS = PanelProcessExtractDTMS(
            self.presenter.view, self.presenter, self.config, self.icons
        )
        self.PanelProcessExtractDTMS.Show()

    def on_open_peak_picker(self, evt, **kwargs):
        """Open peak picker"""
        from origami.gui_elements.panel_peak_picker import PanelPeakPicker

        # get data
        document_title, dataset_type, dataset_name = self._get_query_info_based_on_indent()
        __, data = self.data_handling.get_mobility_chromatographic_data([document_title, dataset_type, dataset_name])

        if self._picker_panel:
            self._picker_panel.SetFocus()
            raise MessageError("Warning", "An instance of a Peak Picking panel is already open")

        # initilize peak picker
        self._picker_panel = PanelPeakPicker(
            self.presenter.view,
            self.presenter,
            self.config,
            self.icons,
            mz_data=data,
            document_title=document_title,
            dataset_type=dataset_type,
            dataset_name=dataset_name,
        )
        self._picker_panel.Show()

    def on_open_extract_data(self, evt, **kwargs):
        from origami.gui_elements.panel_process_extract_data import PanelProcessExtractData

        document = self.data_handling.on_get_document()

        # initilize data extraction panel
        self.PanelProcessExtractData = PanelProcessExtractData(
            self.presenter.view,
            self.presenter,
            self.config,
            self.icons,
            document=document,
            document_title=document.title,
        )
        self.PanelProcessExtractData.Show()

    def on_open_UniDec(self, evt, **kwargs):
        """Open UniDec panel which allows processing and visualisation"""
        from origami.widgets.UniDec.panel_process_UniDec import PanelProcessUniDec

        # get data
        document_title, dataset_type, dataset_name = self._get_query_info_based_on_indent()
        __, data = self.data_handling.get_mobility_chromatographic_data([document_title, dataset_type, dataset_name])

        try:
            if self.PanelProcessUniDec.document_title == document_title:
                logger.warning("An instance of a processing panel is alread open")
                self.PanelProcessUniDec.SetFocus()
                self.PanelProcessUniDec.CenterOnParent()
                return
        except (AttributeError, RuntimeError):
            pass

        # initilize data extraction panel
        self.PanelProcessUniDec = PanelProcessUniDec(
            self.presenter.view,
            self.presenter,
            self.config,
            self.icons,
            mz_data=data,
            document_title=document_title,
            dataset_type=dataset_type,
            dataset_name=dataset_name,
            **kwargs,
        )
        self.PanelProcessUniDec.Show()

    def on_delete_data__ions(self, document, document_title, delete_type, ion_name=None, confirm_deletion=False):
        """
        Delete data from document tree and document

        Parameters
        ----------
        document: py object
            document object
        document_title: str
            name of the document - also found in document.title
        delete_type: str
            type of deletion. Accepted: `ions.all`, `ions.one`
        ion_name: str
            name of the EIC item to be deleted
        confirm_deletion: bool
            check whether all items should be deleted before performing the task


        Returns
        -------
        document: ORIGAMI object
            updated document object
        outcome: bool
            result of positive/negative deletion of document tree object
        """

        if confirm_deletion:
            msg = "Are you sure you want to continue with this action?" + "\nThis action cannot be undone."
            dlg = DialogBox(exceptionMsg=msg, type="Question")
            if dlg == wx.ID_NO:
                logger.info("The operation was cancelled")
                return document, True

        docItem = False
        main_docItem = self.get_item_by_data(document.ion2Dmaps)
        # delete all ions
        if delete_type == "ions.all":
            docItem = self.get_item_by_data(document.ion2Dmaps)
            self.ionPanel.on_remove_deleted_item(list(document.ion2Dmaps.keys()), document_title)
            document.ion2Dmaps = {}
            document.gotIon2Dmaps = False
        # delete one ion
        elif delete_type == "ions.one":
            self.ionPanel.on_remove_deleted_item([ion_name], document_title)
            docItem = self.get_item_by_data(document.ion2Dmaps[ion_name])
            try:
                del document.ion2Dmaps[ion_name]
            except KeyError:
                msg = (
                    "Failed to delete {} from  2D (EIC) dictionary. ".format(ion_name)
                    + "You probably have reselect it in the document tree"
                )
                logger.warning(msg)

        if len(document.ion2Dmaps) == 0:
            document.gotIon2Dmaps = False
            try:
                self.Delete(main_docItem)
            except Exception:
                logger.warning("Failed to delete item: 2D (EIC) from the document tree")

        if docItem is False:
            return document, False
        else:
            self.Delete(docItem)
            return document, True

    def on_delete_data__text(self, document, document_title, delete_type, ion_name=None, confirm_deletion=False):
        """
        Delete data from document tree and document

        Parameters
        ----------
        document: py object
            document object
        document_title: str
            name of the document - also found in document.title
        delete_type: str
            type of deletion. Accepted: `ions.all`, `ions.one`
        ion_name: str
            name of the EIC item to be deleted
        confirm_deletion: bool
            check whether all items should be deleted before performing the task


        Returns
        -------
        document: py object
            updated document object
        outcome: bool
            result of positive/negative deletion of document tree object
        """

        if confirm_deletion:
            msg = "Are you sure you want to continue with this action?" + "\nThis action cannot be undone."
            dlg = DialogBox(exceptionMsg=msg, type="Question")
            if dlg == wx.ID_NO:
                logger.info("The operation was cancelled")
                return document, True

        docItem = False
        main_docItem = self.get_item_by_data(document.ion2Dmaps)
        # delete all ions
        if delete_type == "text.all":
            docItem = self.get_item_by_data(document.ion2Dmaps)
            self.ionPanel.on_remove_deleted_item(list(document.ion2Dmaps.keys()), document_title)
            document.ion2Dmaps = {}
            document.gotIon2Dmaps = False
        # delete one ion
        elif delete_type == "text.one":
            self.ionPanel.on_remove_deleted_item([ion_name], document_title)
            docItem = self.get_item_by_data(document.ion2Dmaps[ion_name])
            try:
                del document.ion2Dmaps[ion_name]
            except KeyError:
                msg = (
                    "Failed to delete {} from  2D (EIC) dictionary. ".format(ion_name)
                    + "You probably have reselect it in the document tree"
                )
                logger.warning(msg)

        if len(document.ion2Dmaps) == 0:
            document.gotIon2Dmaps = False
            try:
                self.Delete(main_docItem)
            except Exception:
                logger.warning("Failed to delete item: 2D (EIC) from the document tree")

        if docItem is False:
            return document, False
        else:
            self.Delete(docItem)
            return document, True

    def on_delete_data__document(self, document_title, ask_permission=True):
        """
        Remove selected document from the document tree
        """
        document = self.data_handling.on_get_document(document_title)

        if ask_permission:
            dlg = DialogBox(
                exceptionTitle="Are you sure?",
                exceptionMsg="Are you sure you would like to delete {}".format(document_title),
                type="Question",
            )
            if dlg == wx.ID_NO:
                self.presenter.onThreading(None, ("Cancelled operation", 4, 5), action="updateStatusbar")
                return

        main_docItem = self.get_item_by_data(document)

        # Delete item from the list
        if self.ItemHasChildren(main_docItem):
            child, cookie = self.GetFirstChild(self.GetRootItem())
            title = self.GetItemText(child)
            iters = 0
            while document_title != title and iters < 500:
                child, cookie = self.GetNextChild(self.GetRootItem(), cookie)
                try:
                    title = self.GetItemText(child)
                    iters += 1
                except Exception:
                    pass

            if document_title == title:
                if child:
                    print("Deleted {}".format(document_title))
                    self.Delete(child)
                    # make sure to clean-up various tables
                    try:
                        self.presenter.view.panelMultipleIons.on_remove_deleted_item(title)
                    except Exception:
                        pass
                    try:
                        self.presenter.view.panelMultipleText.on_remove_deleted_item(title)
                    except Exception:
                        pass
                    try:
                        self.presenter.view.panelMML.on_remove_deleted_item(title)
                    except Exception:
                        pass
                    try:
                        self.presenter.view.panelLinearDT.topP.on_remove_deleted_item(title)
                    except Exception:
                        pass
                    try:
                        self.presenter.view.panelLinearDT.bottomP.on_remove_deleted_item(title)
                    except Exception:
                        pass

                    # delete document
                    del self.presenter.documentsDict[document_title]
                    self.presenter.currentDoc = None

                    # go to the next document
                    if len(self.presenter.documentsDict) > 0:
                        self.presenter.currentDoc = list(self.presenter.documentsDict.keys())[0]
                        self.on_enable_document()

                    # collect garbage
                    gc.collect()

    def on_delete_data__heatmap(self, document, document_title, delete_type, ion_name=None, confirm_deletion=False):
        """
        Delete data from document tree and document

        Parameters
        ----------
        document: py object
            document object
        document_title: str
            name of the document - also found in document.title
        delete_type: str
            type of deletion. Accepted: `file.all`, `file.one`
        ion_name: str
            name of the unsupervised item to be deleted
        confirm_deletion: bool
            check whether all items should be deleted before performing the task


        Returns
        -------
        document: py object
            updated document object
        outcome: bool
            result of positive/negative deletion of document tree object
        """

        if confirm_deletion:
            msg = "Are you sure you want to continue with this action?" + "\nThis action cannot be undone."
            dlg = DialogBox(exceptionMsg=msg, type="Question")
            if dlg == wx.ID_NO:
                logger.info("The operation was cancelled")
                return document, True

        docItem = False
        if delete_type == "heatmap.all.one":
            delete_types = [
                "heatmap.raw.one",
                "heatmap.raw.one.processed",
                "heatmap.processed.one",
                "heatmap.combined.one",
                "heatmap.rt.one",
            ]
        elif delete_type == "heatmap.all.all":
            delete_types = ["heatmap.raw.all", "heatmap.processed.all", "heatmap.combined.all", "heatmap.rt.all"]
        else:
            delete_types = [delete_type]

        if document is None:
            return None, False

        # delete all classes
        if delete_type.endswith(".all"):
            for delete_type in delete_types:
                if delete_type == "heatmap.raw.all":
                    docItem = self.get_item_by_data(document.IMS2Dions)
                    document.IMS2Dions = {}
                    document.gotExtractedIons = False
                if delete_type == "heatmap.processed.all":
                    docItem = self.get_item_by_data(document.IMS2DionsProcess)
                    document.IMS2DionsProcess = {}
                    document.got2DprocessIons = False
                if delete_type == "heatmap.rt.all":
                    docItem = self.get_item_by_data(document.IMSRTCombIons)
                    document.IMSRTCombIons = {}
                    document.gotCombinedExtractedIonsRT = False
                if delete_type == "heatmap.combined.all":
                    docItem = self.get_item_by_data(document.IMS2DCombIons)
                    document.IMS2DCombIons = {}
                    document.gotCombinedExtractedIons = False

                try:
                    self.Delete(docItem)
                except Exception:
                    logger.warning("Failed to delete: {}".format(delete_type))

                if delete_type.startswith("heatmap.raw"):
                    self.ionPanel.delete_row_from_table(delete_item_name=None, delete_document_title=document_title)
                    self.on_update_extracted_patches(document.title, "__all__", None)

        elif delete_type.endswith(".one"):
            for delete_type in delete_types:
                if delete_type == "heatmap.raw.one":
                    main_docItem = self.get_item_by_data(document.IMS2Dions)
                    docItem = self.get_item_by_data(document.IMS2Dions.get(ion_name, "N/A"))
                    if docItem not in ["N/A", None, False]:
                        try:
                            del document.IMS2Dions[ion_name]
                        except KeyError:
                            logger.warning(
                                "Failed to delete {}: {} from {}.".format(delete_type, ion_name, document_title)
                            )
                        if len(document.IMS2Dions) == 0:
                            document.gotExtractedIons = False
                            try:
                                self.Delete(main_docItem)
                            except Exception:
                                pass
                if delete_type == "heatmap.raw.one.processed":
                    ion_name_processed = f"{ion_name} (processed)"
                    main_docItem = self.get_item_by_data(document.IMS2Dions)
                    docItem = self.get_item_by_data(document.IMS2Dions.get(ion_name_processed, "N/A"))
                    if docItem not in ["N/A", None, False]:
                        try:
                            del document.IMS2Dions[ion_name_processed]
                        except KeyError:
                            logger.warning(
                                "Failed to delete {}: {} from {}.".format(
                                    delete_type, ion_name_processed, document_title
                                )
                            )
                        if len(document.IMS2Dions) == 0:
                            document.gotExtractedIons = False
                            try:
                                self.Delete(main_docItem)
                            except Exception:
                                pass
                if delete_type == "heatmap.processed.one":
                    main_docItem = self.get_item_by_data(document.IMS2DionsProcess)
                    docItem = self.get_item_by_data(document.IMS2DionsProcess.get(ion_name, "N/A"))
                    if docItem not in ["N/A", None, False]:
                        try:
                            del document.IMS2DionsProcess[ion_name]
                        except KeyError:
                            logger.warning(
                                "Failed to delete {}: {} from {}.".format(delete_type, ion_name, document_title)
                            )
                        if len(document.IMS2DionsProcess) == 0:
                            document.got2DprocessIons = False
                            try:
                                self.Delete(main_docItem)
                            except Exception:
                                pass
                if delete_type == "heatmap.rt.one":
                    main_docItem = self.get_item_by_data(document.IMSRTCombIons)
                    docItem = self.get_item_by_data(document.IMSRTCombIons.get(ion_name, "N/A"))
                    if docItem not in ["N/A", None, False]:
                        try:
                            del document.IMSRTCombIons[ion_name]
                        except KeyError:
                            logger.warning(
                                "Failed to delete {}: {} from {}.".format(delete_type, ion_name, document_title)
                            )
                        if len(document.IMSRTCombIons) == 0:
                            document.gotCombinedExtractedIonsRT = False
                            try:
                                self.Delete(main_docItem)
                            except Exception:
                                pass
                if delete_type == "heatmap.combined.one":
                    main_docItem = self.get_item_by_data(document.IMS2DCombIons)
                    docItem = self.get_item_by_data(document.IMS2DCombIons.get(ion_name, "N/A"))
                    if docItem not in ["N/A", None, False]:
                        try:
                            del document.IMS2DCombIons[ion_name]
                        except KeyError:
                            logger.warning(
                                "Failed to delete {}: {} from {}.".format(delete_type, ion_name, document_title)
                            )
                        if len(document.IMS2DCombIons) == 0:
                            document.gotCombinedExtractedIons = False
                            try:
                                self.Delete(main_docItem)
                            except Exception:
                                pass

                try:
                    self.Delete(docItem)
                    docItem = False
                except Exception:
                    pass

                if delete_type.startswith("heatmap.raw"):
                    self.ionPanel.delete_row_from_table(delete_item_name=ion_name, delete_document_title=document_title)
                    self.on_update_extracted_patches(document.title, None, ion_name)

        return document, True

    def on_delete_data__mass_spectra(
        self, document, document_title, delete_type, spectrum_name=None, confirm_deletion=False
    ):
        """
        Delete data from document tree and document

        Parameters
        ----------
        document: py object
            document object
        document_title: str
            name of the document - also found in document.title
        delete_type: str
            type of deletion. Accepted: `file.all`, `file.one`
        spectrum_name: str
            name of the unsupervised item to be deleted
        confirm_deletion: bool
            check whether all items should be deleted before performing the task


        Returns
        -------
        document: py object
            updated document object
        outcome: bool
            result of positive/negative deletion of document tree object
        """

        if confirm_deletion:
            msg = "Are you sure you want to continue with this action?" + "\nThis action cannot be undone."
            dlg = DialogBox(exceptionMsg=msg, type="Question")
            if dlg == wx.ID_NO:
                logger.info("The operation was cancelled")
                return document, True

        docItem = False
        main_docItem = self.get_item_by_data(document.multipleMassSpectrum)
        # delete all classes
        if delete_type == "spectrum.all":
            docItem = self.get_item_by_data(document.multipleMassSpectrum)
            document.multipleMassSpectrum = {}
            document.gotMultipleMS = False
            self.filesPanel.delete_row_from_table(delete_item_name=None, delete_document_title=document_title)
        elif delete_type == "spectrum.one":
            docItem = self.get_item_by_data(document.multipleMassSpectrum[spectrum_name])
            try:
                del document.multipleMassSpectrum[spectrum_name]
            except KeyError:
                msg = (
                    "Failed to delete {} from Fits (Supervised) dictionary. ".format(spectrum_name)
                    + "You probably have reselect it in the document tree"
                )
                logger.warning(msg)
            self.filesPanel.delete_row_from_table(delete_item_name=spectrum_name, delete_document_title=document_title)

        if len(document.multipleMassSpectrum) == 0:
            document.gotMultipleMS = False
            try:
                self.Delete(main_docItem)
            except Exception:
                logger.warning("Failed to delete item: Mass Spectra from the document tree")

        if docItem is False:
            return document, False
        else:
            self.Delete(docItem)
            return document, True

    def on_delete_data__chromatograms(
        self, document, document_title, delete_type, spectrum_name=None, confirm_deletion=False
    ):
        """
        Delete data from document tree and document

        Parameters
        ----------
        document: py object
            document object
        document_title: str
            name of the document - also found in document.title
        delete_type: str
            type of deletion. Accepted: `file.all`, `file.one`
        spectrum_name: str
            name of the unsupervised item to be deleted
        confirm_deletion: bool
            check whether all items should be deleted before performing the task


        Returns
        -------
        document: py object
            updated document object
        outcome: bool
            result of positive/negative deletion of document tree object
        """

        if confirm_deletion:
            msg = "Are you sure you want to continue with this action?" + "\nThis action cannot be undone."
            dlg = DialogBox(exceptionMsg=msg, type="Question")
            if dlg == wx.ID_NO:
                logger.info("The operation was cancelled")
                return document, True

        docItem = False
        main_docItem = self.get_item_by_data(document.multipleRT)
        # delete all classes
        if delete_type == "chromatogram.all":
            docItem = self.get_item_by_data(document.multipleRT)
            document.multipleMassSpectrum = {}
            document.gotMultipleMS = False
        elif delete_type == "chromatogram.one":
            docItem = self.get_item_by_data(document.multipleRT[spectrum_name])
            try:
                del document.multipleRT[spectrum_name]
            except KeyError:
                msg = (
                    "Failed to delete {} from Fits (Supervised) dictionary. ".format(spectrum_name)
                    + "You probably have reselect it in the document tree"
                )
                logger.warning(msg)

        if len(document.multipleRT) == 0:
            document.gotMultipleRT = False
            try:
                self.Delete(main_docItem)
            except Exception:
                logger.warning("Failed to delete item: Mass Spectra from the document tree")

        if docItem is False:
            return document, False
        else:
            self.Delete(docItem)
            return document, True

    def on_update_unidec(self, unidec_data, document_title, dataset, set_data_only=False):
        """
        Update annotations in specified document/dataset
        ----------
        Parameters
        ----------
        annotations : dict
            dictionary with annotations
        document : str
            name of the document
        dataset : str
            name of the dataset
        set_data_only : bool
            specify whether all annotations should be removed and readded or if
            we it should simply set data
        """

        document = self.data_handling.on_get_document(document_title)
        item = False
        docItem = False
        if dataset == "Mass Spectrum":
            item = self.get_item_by_data(document.massSpectrum)
            document.massSpectrum["unidec"] = unidec_data
        elif dataset == "Mass Spectrum (processed)":
            item = self.get_item_by_data(document.smoothMS)
            document.smoothMS["unidec"] = unidec_data
        else:
            item = self.get_item_by_data(document.multipleMassSpectrum[dataset])
            document.multipleMassSpectrum[dataset]["unidec"] = unidec_data

        if item is not False and not set_data_only:
            self.append_unidec(item, unidec_data)
            self.data_handling.on_update_document(document, "no_refresh")
        else:
            try:
                docItem = self.get_item_by_data(document)
            except Exception:
                docItem = False
            if docItem is not False:
                self.SetPyData(docItem, document)
                self.presenter.documentsDict[document.title] = document
            else:
                self.data_handling.on_update_document(document, "document")

    def append_unidec(self, item, unidec_data, expand=True):
        """
        Update annotations in the document tree
        ----------
        Parameters
        ----------
        item : wxPython document tree item
            item in the document tree that should be cleared and re-filled
        unidec_data : dict
            dictionary with UniDec data
        expand : bool
            specify if tree item should be expanded

        """
        image = self.get_item_image("unidec")

        child, cookie = self.GetFirstChild(item)
        i = 0
        while child.IsOk():
            #             print("child", i, self.GetItemText(child))
            if self.GetItemText(child) == "UniDec":
                self.Delete(child)
            child, cookie = self.GetNextChild(item, cookie)
            i += 1

        if len(unidec_data) == 0:
            return

        unidec_item = self.AppendItem(item, "UniDec")
        self.SetPyData(unidec_item, unidec_data)
        self.SetItemImage(unidec_item, image, wx.TreeItemIcon_Normal)

        for key in unidec_data:
            unidec_item_individual = self.AppendItem(unidec_item, key)
            self.SetPyData(unidec_item_individual, unidec_data[key])
            self.SetItemImage(unidec_item_individual, image, wx.TreeItemIcon_Normal)

        if expand:
            self.Expand(unidec_item)

    def on_update_data(self, item_data, item_name, document, data_type, set_data_only=False):
        """Update document data

        Parameters
        ----------
        item_data: list
            new data to be added to document
        item_name: str
            name of the EIC
        item_type : str
            which type of data is provided
        document: py object
            document object
        set_data_only: bool
            specify whether data should be added with full refresh or just set
        """
        item = False
        # spectrum
        if data_type == "main.raw.spectrum":
            item = self.get_item_by_data(document.massSpectrum)
            document.gotMS = True
            document.massSpectrum = item_data

        elif data_type == "main.raw.spectrum.unidec":
            item = self.get_item_by_data(document.massSpectrum["unidec"])
            document.gotMS = True
            document.massSpectrum["unidec"] = item_data

        elif data_type == "main.processed.spectrum":
            item = self.get_item_by_data(document.smoothMS)
            document.gotSmoothMS = True
            document.smoothMS = item_data

        elif data_type == "extracted.spectrum":
            item = self.get_item_by_data(document.multipleMassSpectrum)
            document.gotMultipleMS = True
            document.multipleMassSpectrum[item_name] = item_data

        # mobilogram
        elif data_type == "main.mobilogram":
            item = self.get_item_by_data(document.DT)
            document.got1DT = True
            document.DT = item_data

        elif data_type == "ion.mobilogram":
            item = self.get_item_by_data(document.IMS1DdriftTimes)
            document.gotExtractedDriftTimes = True
            document.IMS1DdriftTimes[item_name] = item_data

        elif data_type == "ion.mobilogram.raw":
            item = self.get_item_by_data(document.multipleDT)
            document.gotMultipleDT = True
            document.multipleDT[item_name] = item_data

        # chromatogram
        elif data_type == "main.chromatogram":
            item = self.get_item_by_data(document.RT)
            document.got1RT = True
            document.RT = item_data

        elif data_type == "extracted.chromatogram":
            item = self.get_item_by_data(document.multipleRT)
            document.gotMultipleRT = True
            document.multipleRT[item_name] = item_data

        elif data_type == "ion.chromatogram.combined":
            item = self.get_item_by_data(document.IMSRTCombIons)
            document.gotCombinedExtractedIonsRT = True
            document.IMSRTCombIons[item_name] = item_data

        # heatmap
        elif data_type == "main.raw.heatmap":
            item = self.get_item_by_data(document.IMS2D)
            document.got2DIMS = True
            document.IMS2D = item_data

        elif data_type == "main.processed.heatmap":
            item = self.get_item_by_data(document.IMS2Dprocess)
            document.got2Dprocess = True
            document.IMS2Dprocess = item_data

        elif data_type == "ion.heatmap.raw":
            item = self.get_item_by_data(document.IMS2Dions)
            document.gotExtractedIons = True
            document.IMS2Dions[item_name] = item_data

        elif data_type == "ion.heatmap.combined":
            item = self.get_item_by_data(document.IMS2DCombIons)
            document.gotCombinedExtractedIons = True
            document.IMS2DCombIons[item_name] = item_data

        elif data_type == "ion.heatmap.processed":
            item = self.get_item_by_data(document.IMS2DionsProcess)
            document.got2DprocessIons = True
            document.IMS2DionsProcess[item_name] = item_data

        elif data_type == "ion.heatmap.comparison":
            item = self.get_item_by_data(document.IMS2DcompData)
            document.gotComparisonData = True
            document.IMS2DcompData[item_name] = item_data

        # overlay
        elif data_type == "overlay.statistical":
            item = self.get_item_by_data(document.IMS2DstatsData)
            document.gotStatsData = True
            document.IMS2DstatsData[item_name] = item_data

        elif data_type == "overlay.overlay":
            item = self.get_item_by_data(document.IMS2DoverlayData)
            document.gotOverlay = True
            document.IMS2DoverlayData[item_name] = item_data

        # annotated data
        elif data_type == "custom.annotated":
            item = self.get_item_by_data(document.other_data)
            document.other_data[item_name] = item_data

        else:
            logger.error(f"Not implemented yet... {item_name}, {data_type}")

        if item is not False and not set_data_only:
            # will add to the main root
            if item_name in ["", None]:
                self.update_one_item(item, item_data, image=data_type)
            # will add to the branch
            else:
                self.add_one_to_group(item, item_data, item_name, image=data_type)

            # add data to document without updating it
            self.data_handling.on_update_document(document, "no_refresh")
        else:
            logger.warning("Failed to quietly update document")
            self.data_handling.on_update_document(document, "document")

    def on_update_extracted_patches(self, document_title, data_type, ion_name):
        """
        Remove rectangles/patches from plot area. Triggered upon deletion of item
        from the 'classes' subtree.

        Parameters
        ----------
        document_title: str
            name of document
        data_type: str
            name of dataset
        ion_name: str
            name of item
        """

        # remove all patches
        if data_type == "__all__" or ion_name is None:
            self.panel_plot.on_clear_patches(plot="MS")
        # remove specific patch
        else:
            rect_label = "{};{}".format(document_title, ion_name)
            self.panel_plot.plot_remove_patches_with_labels(rect_label, plot_window="MS")

        self.panel_plot.plot_repaint(plot_window="MS")

    def get_item_image(self, image_type):
        if image_type in ["main.raw.spectrum", "extracted.spectrum", "main.processed.spectrum", "unidec"]:
            image = self.bullets_dict["mass_spec_on"]
        elif image_type == [
            "ion.heatmap.combined",
            "ion.heatmap.raw",
            "ion.heatmap.processed",
            "main.raw.heatmap",
            "main.processed.heatmap",
            "ion.heatmap.comparison",
        ]:
            image = self.bullets_dict["heatmap_on"]
        elif image_type == ["ion.mobilogram", "ion.mobilogram.raw"]:
            image = self.bullets_dict["drift_time_on"]
        elif image_type in ["main.chromatogram", "extracted.chromatogram", "ion.chromatogram.combined"]:
            image = self.bullets_dict["rt_on"]
        elif image_type in ["annotation"]:
            image = self.bullets_dict["annot"]
        else:
            image = self.bullets_dict["heatmap_on"]

        return image

    def add_one_to_group(self, item, data, name, image, expand=True):
        """
        Append data to the docoument
        ----------
        Parameters
        ----------
        item : wxPython document tree item
            item in the document tree that should be cleared and re-filled
        data : dict
            dictionary with annotations
        name : str
            name of the classifier
        expand : bool
            specify if tree item should be expanded
        """
        image = self.get_item_image(image)
        child, cookie = self.GetFirstChild(item)
        while child.IsOk():
            if self.GetItemText(child) == name:
                self.Delete(child)
            child, cookie = self.GetNextChild(item, cookie)

        if len(data) == 0:
            return

        itemClass = self.AppendItem(item, name)
        self.SetPyData(itemClass, data)
        self.SetItemImage(itemClass, image, wx.TreeItemIcon_Normal)

        # add annotations
        self._add_unidec_to_object(data, itemClass, check=True)
        self._add_annotation_to_object(data, itemClass, check=True)

        if expand:
            self.Expand(itemClass)

    def update_one_item(self, item, data, image):
        image = self.get_item_image(image)
        self.SetPyData(item, data)
        self.SetItemImage(item, image, wx.TreeItemIcon_Normal)

        # add annotations
        self._add_unidec_to_object(data, item, check=True)
        self._add_annotation_to_object(data, item, check=True)