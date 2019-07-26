# -*- coding: utf-8 -*-
# __author__ lukasz.g.migas
import wx


def DialogBox(exceptionTitle="", exceptionMsg="", type="Error", exceptionPrint=True):
    """
    Generic message box
    """

    if type == "Error":
        dlgStyle = wx.OK | wx.ICON_ERROR
    elif type == "Info":
        dlgStyle = wx.OK | wx.ICON_INFORMATION
    elif type == "Stop":
        dlgStyle = wx.OK | wx.ICON_STOP
    elif type == "Warning":
        dlgStyle = wx.OK | wx.ICON_EXCLAMATION
    elif type == "Question":
        dlgStyle = wx.YES_NO | wx.ICON_QUESTION

    if exceptionPrint:
        print(exceptionMsg)

    dlg = wx.MessageDialog(None, exceptionMsg, exceptionTitle, dlgStyle)
    result = dlg.ShowModal()

    if type == "Question":
        return result


def DialogSimpleAsk(message="", title="", defaultValue=""):
    dlg = wx.TextEntryDialog(None, message, title, defaultValue)  # parent
    dlg.CentreOnScreen()

    if dlg.ShowModal() == wx.ID_CANCEL:
        return None

    result = dlg.GetValue()
    dlg.Destroy()
    return result
