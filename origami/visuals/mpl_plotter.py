# -*- coding: utf-8 -*-
# __author__ lukasz.g.migas
import os

import matplotlib
import matplotlib.patches as patches
import wx
from gui_elements.misc_dialogs import DialogBox
from matplotlib import interactive
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D
from numpy import amax
from numpy import divide
from PIL import Image
from PIL import ImageChops
from ZoomBox import GetXValues
from ZoomBox import ZoomBox
matplotlib.use('WXAgg')

interactive(True)


class mpl_plotter(wx.Window):

    def __init__(self, *args, **kwargs):

        if 'figsize' in kwargs:
            self.figsize = kwargs.pop('figsize')
        else:
            self.figsize = [8, 2.5]

        if 'axes_size' in kwargs:
            self._axes = kwargs.pop('axes_size')
        else:
            self._axes = [0.15, 0.12, 0.8, 0.8]

        self.figure = Figure(
            figsize=self.figsize,
        )

        if 'config' in kwargs:
            self.config = kwargs.pop('config')

        self.window_name = kwargs.pop('window_name', None)

        wx.Window.__init__(self, *args, **kwargs)
        self.canvas = FigureCanvasWxAgg(self, -1, self.figure)

        # Create a resizer
        self.Bind(wx.EVT_SIZE, self.on_resize)

        # Prepare for zoom
        self.zoom = None
        self.zoomtype = 'box'
        self.plotName = None
        self.resize = 1

        # plot data
        self.data_limits = []

    def get_xlimits(self):
        return [self.data_limits[0], self.data_limits[0]]

    def get_ylimits(self):
        return [self.data_limits[1], self.data_limits[3]]

#     def onPick(self, evt):
#         pass
        # to be used to improve 3D plot
#         print(dir(evt.artist.get_xdata))
#         print('pick')

    def _generatePlotParameters(self):
        plot_parameters = {
            'grid_show': self.config._plots_grid_show,
            'grid_color': self.config._plots_grid_color,
            'grid_line_width': self.config._plots_grid_line_width,
            'extract_color': self.config._plots_extract_color,
            'extract_line_width': self.config._plots_extract_line_width,
            'extract_crossover_sensitivity_1D': self.config._plots_extract_crossover_1D,
            'extract_crossover_sensitivity_2D': self.config._plots_extract_crossover_2D,
            'zoom_color_vertical': self.config._plots_zoom_vertical_color,
            'zoom_color_horizontal': self.config._plots_zoom_horizontal_color,
            'zoom_color_box': self.config._plots_zoom_box_color,
            'zoom_line_width': self.config._plots_zoom_line_width,
            'zoom_crossover_sensitivity': self.config._plots_zoom_crossover,
        }
        return plot_parameters

    def setupGetXAxies(self, plots):
        self.getxaxis = GetXValues(plots)

    def setup_zoom(
        self, plots, zoom, data_lims=None, plotName=None,
        plotParameters=None, allowWheel=True, preventExtraction=False,
    ):
        if plotParameters is None:
            plotParameters = self._generatePlotParameters()

        self.data_limits = data_lims

        self.zoom = ZoomBox(
            plots, None, drawtype='box',
            useblit=True, button=1,
            onmove_callback=None,
            rectprops=dict(alpha=0.2, facecolor='yellow'),
            spancoords='data', data_lims=data_lims,
            plotName=plotName,
            allowWheel=allowWheel,
            preventExtraction=preventExtraction,
            plotParameters=plotParameters,
        )
        self.onRebootZoomKeys(evt=None)

    def update_extents(self, extents):
        ZoomBox.update_extents(self.zoom, extents)

    def update_y_extents(self, y_min, y_max):
        ZoomBox.update_y_extents(self.zoom, y_min, y_max)

    def _on_mark_annotation(self, state):
        try:
            ZoomBox.update_mark_state(self.zoom, state)
        except TypeError:
            pass

    def onRebootZoomKeys(self, evt):
        """
        Reboot 'stuck' keys
        """
        if self.zoom is not None:
            ZoomBox.onRebootKeyState(self.zoom, evt=None)

    def kda_test(self, xvals):
        """
        Adapted from Unidec/PlottingWindow.py

        Test whether the axis should be normalized to convert mass units from Da to kDa.
        Will use kDa if: xvals[int(len(xvals) / 2)] > 100000 or xvals[len(xvals) - 1] > 1000000

        If kDa is used, self.kda=True and self.kdnorm=1000. Otherwise, self.kda=False and self.kdnorm=1.
        :param xvals: mass axis
        :return: None
        """
        try:
            if xvals[int(len(xvals) / 2)] > 100000 or xvals[len(xvals) - 1] > 1000000:
                kdnorm = 1000.
                xlabel = 'Mass (kDa)'
                kda = True
            elif amax(xvals) > 10000:
                kdnorm = 1000.
                xlabel = 'Mass (kDa)'
                kda = True
            else:
                xlabel = 'Mass (Da)'
                kda = False
                kdnorm = 1.
        except (TypeError, ValueError):
            try:
                if xvals > 10000:
                    kdnorm = 1000.
                    xlabel = 'Mass (kDa)'
                    kda = True
            except Exception:
                xlabel = 'Mass (Da)'
                kdnorm = 1.
                kda = False

        # convert x-axis
        xvals = xvals / kdnorm

        return xvals, xlabel, kda

    def testXYmaxVals(self, values=None):
        """
        Function to check whether x/y axis labels do not need formatting
        """
        if max(values) > 1000:
            divider = 1000
        elif max(values) > 1000000:
            divider = 1000000
        else:
            divider = 1
        return divider

    def testXYmaxValsUpdated(self, values=None):
        """
        Function to check whether x/y axis labels do not need formatting
        """
        baseDiv = 10
        increment = 10
        divider = baseDiv

        try:
            itemShape = values.shape
        except Exception:
            from numpy import array
            values = array(values)
            itemShape = values.shape

        if len(itemShape) > 1:
            maxValue = amax(values)
        elif len(itemShape) == 1:
            maxValue = max(values)
        else:
            maxValue = values

        while 10 <= (maxValue / divider) >= 1:
            divider = divider * increment

        expo = len(str(divider)) - len(str(divider).rstrip('0'))

        return divider, expo

    def repaint(self):
        """
        Redraw and refresh the plot.
        :return: None
        """
        self.canvas.draw()

    def clearPlot(self, *args):
        """
        Clear the plot and rest some of the parameters.
        :param args: Arguments
        :return:
        """
        self.figure.clear()
        # clear labels
        try:
            self.text = []
        except Exception:
            pass
        try:
            self.lines = []
        except Exception:
            pass
        try:
            self.patch = []
        except Exception:
            pass
        try:
            self.markers = []
        except Exception:
            pass
        try:
            self.arrows = []
        except Exception:
            pass
        try:
            self.temporary = []
        except Exception:
            pass

        self.rotate = 0

        # clear plots
        try:
            self.cax = None
        except Exception:
            pass

        try:
            self.plotMS = None
        except Exception:
            pass

        try:
            self.plot2D_upper = None
        except Exception:
            pass

        try:
            self.plot2D_lower = None
        except Exception:
            pass

        try:
            self.plot2D_side = None
        except Exception:
            pass

        try:
            self.plotRMSF = None
        except Exception:
            pass

        self.repaint()

    def on_resize(self, *args, **kwargs):

        if self.lock_plot_from_updating_size:
            self.SetBackgroundColour(wx.WHITE)
            return

        if self.resize == 1:
            self.canvas.SetSize(self.GetSize())

    def onselect(self, ymin, ymax):
        pass

    def pil_trim(self, im):
        bg = Image.new(im.mode, im.size, im.getpixel((0, 0)))
        diff = ImageChops.difference(im, bg)
        diff = ImageChops.add(diff, diff, 2.0, -100)
        bbox = diff.getbbox()
        if bbox:
            return im.crop(bbox)

    def saveFigure(self, path, transparent, dpi, **kwargs):
        """
        Saves figures in specified location.
        Transparency and DPI taken from config file
        """
        self.figure.savefig(path, transparent=transparent, dpi=dpi, **kwargs)

    def save_figure(self, path, **kwargs):
        """
        Saves figures in specified location.
        Transparency and DPI taken from config file
        """
        # check if plot exists
        if not hasattr(self, 'plotMS'):
            print('Cannot save a plot that does not exist')
            return

        # Get resize parameter
        resizeName = kwargs.get('resize', None)
        resizeSize = None

        if resizeName is not None:
            resizeSize = self.config._plotSettings[resizeName]['resize_size']

        if not hasattr(self.plotMS, 'get_position'):
            resizeSize = None

        if resizeSize is not None and not self.lock_plot_from_updating_size:
            dpi = wx.ScreenDC().GetPPI()
            # Calculate new size
            figsizeNarrowPix = (int(resizeSize[0] * dpi[0]), int(resizeSize[1] * dpi[1]))
            # Set new canvas size and reset the view
            self.canvas.SetSize(figsizeNarrowPix)
            self.canvas.draw()
            # Get old and new plot sizes
            oldAxesSize = self.plotMS.get_position()
            newAxesSize = self.config._plotSettings[resizeName]['save_size']
            try:
                self.plotMS.set_position(newAxesSize)
            except RuntimeError:
                self.plotMS.set_position(oldAxesSize)

            self.repaint()

        # Save figure
        try:
            kwargs['bbox_inches'] = 'tight'
            self.figure.savefig(path, **kwargs)

        except IOError:
            # reset axes size
            if resizeSize is not None and not self.lock_plot_from_updating_size:
                self.plotMS.set_position(oldAxesSize)
                self.on_resize()
            # warn user
            DialogBox(
                exceptionTitle='Warning',
                exceptionMsg="Cannot save file: %s as it appears to be currently open or the folder doesn't exist" %
                path,
                type='Error',
            )
            # get file extension
            fname, delimiter_txt = os.path.splitext(path)
            try:
                bname = os.path.basename(fname)
            except Exception:
                bname = ''

            fileType = 'Image file ({})|*{}'.format(delimiter_txt, delimiter_txt)
            dlg = wx.FileDialog(
                None, 'Save as...',
                '', '', fileType, wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
            )
            dlg.SetFilename(bname)

            if dlg.ShowModal() == wx.ID_OK:
                fname, __ = os.path.splitext(dlg.GetPath())
                path = os.path.join(fname + delimiter_txt)

                # reset axes, again
                if resizeSize is not None and not self.lock_plot_from_updating_size:
                    self.canvas.SetSize(figsizeNarrowPix)
                    self.canvas.draw()
                    try:
                        self.plotMS.set_position(newAxesSize)
                    except RuntimeError:
                        self.plotMS.set_position(oldAxesSize)
                    self.repaint()

                try:
                    kwargs['bbox_inches'] = 'tight'
                    self.figure.savefig(path, **kwargs)
                except Exception:
                    try:
                        del kwargs['bbox_inches']
                        self.figure.savefig(path, **kwargs)
                    except Exception:
                        pass

        # Reset previous view
        if resizeSize is not None and not self.lock_plot_from_updating_size:
            self.plotMS.set_position(oldAxesSize)
            self.on_resize()

    def onAddMarker(
        self, xval=None, yval=None, marker='s', color='r', size=5,
        testMax='none', label='', as_line=True,
    ):
        """
        This function adds a marker to 1D plot
        """
        if testMax == 'yvals':
            ydivider, expo = self.testXYmaxValsUpdated(values=yval)
            if expo > 1:
                yvals = divide(yval, float(ydivider))

        if as_line:
            self.plotMS.plot(
                xval, yval, color=color, marker=marker,
                linestyle='None', markersize=size,
                markeredgecolor='k', label=label,
            )
        else:
            self.plotMS.scatter(
                xval, yval, color=color, marker=marker,
                s=size, edgecolor='k', label=label,
                alpha=1.0,
            )

    def addText(
        self, xval=None, yval=None, text=None, rotation=90, color='k',
        fontsize=16, weight=True, plot=None,
    ):
        """
        This function annotates the MS peak
        """
        # Change label weight
        if weight:
            weight = 'bold'
        else:
            weight = 'regular'

        if plot is None:
            self.text = self.plotMS.text(
                x=xval, y=yval,
                s=text,
                fontsize=fontsize,
                rotation=rotation,
                weight=weight,
                fontdict=None,
                color=color,
            )
        elif plot == 'Grid':
            self.text = self.plot2D_side.text(
                x=xval, y=yval,
                s=text,
                fontsize=fontsize,
                rotation=rotation,
                weight=weight,
                fontdict=None,
                color=color,
            )

    def addRectangle(
        self, x, y, width, height, color='green',
        alpha=0.5, linewidth=0,
    ):
        """
        Add rect patch to plot
        """
        # (x,y), width, height, alpha, facecolor, linewidth
        add_patch = patches.Rectangle(
            (x, y), width, height,
            color=color, alpha=alpha,
            linewidth=linewidth,
        )
        self.plotMS.add_patch(add_patch)

    def onZoomIn(self, startX, endX, endY):
        self.plotMS.axis([startX, endX, 0, endY])

    def onZoomRMSF(self, startX, endX):
        x1, x2, y1, y2 = self.plotRMSF.axis()
        self.plotRMSF.axis([startX, endX, y1, y2])

    def onGetXYvals(self, axes='both'):
        xvals = self.plotMS.get_xlim()
        yvals = self.plotMS.get_ylim()
        if axes == 'both':
            return xvals, yvals
        elif axes == 'x':
            return xvals
        elif axes == 'y':
            return yvals

    def get_plot_name(self):
        return self.plot_name

    def get_axes_size(self):
        return self._axes
