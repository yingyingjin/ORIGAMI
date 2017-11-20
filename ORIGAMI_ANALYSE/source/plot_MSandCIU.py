# -*- coding: utf-8 -*-

# -------------------------------------------------------------------------
#    Copyright (C) 2017 Lukasz G. Migas <lukasz.migas@manchester.ac.uk>
# 
#	 GitHub : https://github.com/lukasz-migas/ORIGAMI
#	 University of Manchester IP : https://www.click2go.umip.com/i/s_w/ORIGAMI.html
#	 Cite : 10.1016/j.ijms.2017.08.014
#
#    This program is free software. Feel free to redistribute it and/or 
#    modify it under the condition you cite and credit the authors whenever 
#    appropriate. 
#    The program is distributed in the hope that it will be useful but is 
#    provided WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE
# -------------------------------------------------------------------------

from plottingWindow import plottingWindow
from numpy import arange, sin, pi
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
from matplotlib import gridspec

class plotMSandCIU(plottingWindow):
    
    def __init__(self, *args, **kwargs):
        plottingWindow.__init__(self, *args, **kwargs)
        
        self.plotData()
        
    def plotData(self, xvals=None, yvals=None, title="", xlabel="", ylabel="", label="", color="black", **kwargs):
        self.zoomtype = "box"
        self.xlabel = xlabel
        self.ylabel = ylabel
        x1 = np.linspace(0.0, 5.0)
        x2 = np.linspace(0.0, 5.0)       
        y1 = np.cos(2 * np.pi * x1) * np.exp(-x1)
        y2 = np.cos(2 * np.pi * x2)
        # This should plot MS (1) and CIU (3) + GEL if desired (0.1)
        gs = gridspec.GridSpec(3, 1, height_ratios=[0.1,1,3]) #, hspace=0.05)
        
        self.plot1 = self.figure.add_subplot(gs[0], aspect='auto')
        #self.plot1 = self.figure.add_subplot(211, aspect='auto')
        self.plot1.plot(x1, y1, 'o-')
        self.plot1.tick_params(axis='both', which='both',bottom='off', top='off',
                                left='off', labelbottom='off', labelleft='off')
        
                
        self.plot1 = self.figure.add_subplot(gs[1], aspect='auto')
        #self.plot1 = self.figure.add_subplot(211, aspect='auto')
        self.plot1.plot(x1, y1, 'o-')
        
        self.plot2 = self.figure.add_subplot(gs[2], aspect='auto')
        #self.plot2 = self.figure.add_subplot(212, aspect='auto')
        self.plot2.plot(x2, y2, '.-')
        
        self.figure.set_tight_layout(True)
        
        self.setup_zoom([self.plot1, self.plot2], self.zoomtype)
        #print('Subplot')

