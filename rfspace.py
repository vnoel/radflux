#!/usr/bin/env python
# encoding: utf-8
"""
rfspace.py

Created by Vincent Noel - LMD/CNRS on 2011-11-10.
"""

import numpy as np

import os

import chaco.api as chaco

from pyface.api import OK, FileDialog, AboutDialog, MessageDialog

from traits.api import HasTraits, Instance
from traits.api import Str, Button, Int, Enum, Range
from traitsui.api import View, HGroup, VGroup, UItem, Item, Spring
from traitsui.api import Handler
from traitsui.menu import MenuBar, Menu, Action, CloseAction, Separator

from enable.api import ComponentEditor

from radflux_utils import ceres_nc_read, coastlines_read



class RFMaps(HasTraits):

    window_title = 'RadFlux Space Maps'
    plot_title = Str('')
    month_start = Int(1)
    month_start = Range(value=1, low=1, high=12)
    nmonth = Range(value=3, low=1, high=12)
    show_year = Enum((2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010))
    data_selector = Enum('Shortwave Upgoing Radiation Flux (measurements)', 
                         'Shortwave Clear-Sky Upgoing Radiation Flux (model)', 
                         'Shortwave, measurements - model',
                         'Longwave Upgoing Radiation Flux (measurements)',
                         'Longwave Clear-Sky Upgoing Radiation Flux (model)',
                         'Longwave, measurements - model',
                         'Cloud Radiative Impact (LW difference + SW difference)')
    
    rfcontainer = Instance(chaco.Plot)
    
    open_file_button = Button('Open Data File...')

    traits_view = View(
        VGroup(
            # this part of the view is only shown when plot_title is not ""
            # ie when there is data
            HGroup(
                Item('show_year', label='Year'),
                Item('data_selector', springy=True),
                springy=True,
                padding=5
            ),
            HGroup(
                UItem('map_container', editor=ComponentEditor(), width=800, height=300),
            ),
            # Item('yearlist'),
            Item('month_start', label='Start Month'),
            Item('nmonth', label='Number of averaged months'),
            padding=5,
            visible_when='plot_title != ""'
        ), 
        # this part of the view is shown when there is no data
        VGroup(
            Spring(),
            UItem('open_file_button', padding=15),
            Spring(),
            visible_when='plot_title == ""',
            springy=True
        ),
        menubar=MenuBar(
            Menu(
                CloseAction,
                Separator(),
                Action(name='Open data file...', action='open_file'),
                Action(name='Save Plot...', action='save_plot', enabled_when='plot_title != ""'),
                name='File',
            ),
            Menu(
                Action(name='About', action='about'),
                name='Help'
            )
        ),
        resizable=True,
        title=window_title,
    )
    
    def update_plot(self):

        self.update_period()
        self.set_data_in_plot()
    
    
    def update_period(self):

        y = self.show_year
        ms = self.month_start
        me = self.month_start + self.nmonth
        idx = [1 if (d.year == y and d.month >= ms and d.month < me) else 0 for d in self.dates]
        idx = (np.array(idx) > 0)

        months_idx = np.arange(len(self.dates))[idx]        

        self.tstart = np.min(months_idx)
        self.tend = np.max(months_idx) + 1
                
    
    def _data_selector_changed(self):

        self.update_plot()
    
    
    def _show_year_changed(self):

        self.update_plot()
        
        
    def _month_start_changed(self):

        if (self.month_start + self.nmonth) > 13:
            self.nmonth = 13 - self.month_start
        self.update_plot()
        
    
    def _nmonth_changed(self):

        if (self.month_start + self.nmonth) > 13:
            self.month_start = 13 - self.nmonth
        self.update_plot()
        
    
    def _open_file_button_fired(self):
        
        if self.data is not None:
            # this should never happen
            return
            
        self.handler.open_file(None)
        
    
    def set_data_from_file(self, filedata):

        self.time = filedata['time']
        self.dates = filedata['dates']
        self.lon = filedata['lon']
        self.lat = filedata['lat']
        
        self.data = {'Shortwave Upgoing Radiation Flux (measurements)':filedata['swup'], 
                     'Shortwave Clear-Sky Upgoing Radiation Flux (model)':filedata['swupclr'],
                     'Shortwave, measurements - model':filedata['swup'] - filedata['swupclr'],
                     'Longwave Upgoing Radiation Flux (measurements)':filedata['lwup'],
                     'Longwave Clear-Sky Upgoing Radiation Flux (model)':filedata['lwupclr'],
                     'Longwave, measurements - model':filedata['lwup'] - filedata['lwupclr'],
                     'Cloud Radiative Impact (LW difference + SW difference)': filedata['swup'] - filedata['swupclr'] + filedata['lwup'] - filedata['lwupclr'],
                     }
                    
        self.update_period()
                
        
    def open_ceres_data(self, rf_file):
        
        filedata = ceres_nc_read(rf_file)
        if filedata is not None:
            self.coastlon, self.coastlat = coastlines_read(os.path.dirname(rf_file))
            self.set_data_from_file(filedata)
                
        
    def save_image(self, imagefile):

        print 'saving ', imagefile
        window_size = self.map_container.outer_bounds
        gc = chaco.PlotGraphicsContext(window_size)
        gc.render_component(self.map_container)
        gc.save(imagefile)
        
    
    def set_data_in_plot(self):
        
        if self.data is None or self.map_container is None:
            return
            
        selected_data = self.data[self.data_selector]
        imagedata = np.mean(selected_data[self.tstart:self.tend,:,:], axis=0)
        self.rfdata.set_data('image', imagedata)
        self.rfdata.set_data('coastlon', self.coastlon)
        self.rfdata.set_data('coastlat', self.coastlat)

        self.plot_title = 'CERES RF DATA %d months average since %04d-%02d-01' % (self.nmonth, self.show_year, self.month_start)
        self.map_plot.title = self.plot_title
        
        if 'measurements - model' in self.data_selector:
            cmin, cmax = -80, 80
        elif self.data_selector.startswith('Shortwave'):
            cmin, cmax = 0, 250
        elif self.data_selector.startswith('Longwave'):
            cmin, cmax = 0, 400
        else:
            cmin, cmax = -50, 50
        self.map_img.color_mapper.range.set_bounds(cmin,cmax)
        
        self.map_colorbar._axis.title = self.data_selector
        
        if 'measurements - model' in self.data_selector or 'Impact' in self.data_selector:
            self.map_img.color_mapper = chaco.RdBu(self.map_img.color_mapper.range)
            self.map_img.color_mapper.reverse_colormap()
        else:
            self.map_img.color_mapper = chaco.jet(self.map_img.color_mapper.range)
            

    
    def init_map(self, arrayplotdata):
        
        map_plot = chaco.Plot(arrayplotdata, padding=40)
        map_plot.title = self.plot_title
        map_img = map_plot.img_plot('image', colormap=chaco.jet, xbounds=(-180,180), ybounds=(-90,90))[0]
        
        map_colorbar = chaco.ColorBar(orientation='v',
                                    resizable='v',
                                    width=20,
                                    padding=20,
                                    plot=map_img,
                                    padding_left=60,
                                    padding_top=map_plot.padding_top,
                                    padding_bottom=map_plot.padding_bottom,
                                    index_mapper=chaco.LinearMapper(range=map_img.color_mapper.range),
                                    color_mapper=map_img.color_mapper)
        
        map_container = chaco.HPlotContainer(map_colorbar, map_plot)
        
        return map_container, map_plot, map_img, map_colorbar
        

    def init_coastlines_on_map(self, map_plot):
        
        coastlines_plot = map_plot.plot(('coastlon', 'coastlat'), type='scatter', marker_size=0.1)
        return coastlines_plot
        

    def __init__(self, file_to_open=None):

        self.data = None

        self.rfdata = chaco.ArrayPlotData()
        fakedata = np.random.rand(200,200)
        self.rfdata.set_data('image', fakedata)
        self.rfdata.set_data('coastlon', (0, 0))
        self.rfdata.set_data('coastlat', (0, 0))
        
        container, plot, img, colorbar = self.init_map(self.rfdata)
        coastlines_plot = self.init_coastlines_on_map(plot)

        self.map_container = container
        self.map_plot = plot
        self.map_img = img
        self.map_colorbar = colorbar
        self.coastlines_plot = coastlines_plot
                
        if file_to_open is not None:
            self.open_ceres_data(file_to_open)
            self.update_plot()
            

class RFController(Handler):

    view = Instance(RFMaps)

    def init(self, info):

        self.view = info.object
        self.view.handler = self


    def open_file(self, ui_info):

        wildcard = 'NetCDF (*.nc4)|*.nc4|All files|*.*'
        fd = FileDialog(action='open', 
                        title='Open RadFlux Daily Time Series', 
                        wildcard=wildcard)
        if fd.open() == OK:

            basename = os.path.basename(fd.path)
            if not (basename.endswith('.nc4') and basename.startswith('CERES')):
                msg = MessageDialog(message='Not a valid CERES file. Valid files follow the form CERES*.nc4', severity='warning', title='invalid file')
                msg.open()
                return

            print 'Opening ' + fd.path
            self.view.open_ceres_data(fd.path)
            self.view.update_plot()
            
            
    def save_plot(self, ui_info):
        
        wildcard = 'PNG Figure files (*.png)|*.png|All files|*.*'
        fd = FileDialog(action='save as',
                        title='Same figures in PNG file', 
                        default_filename='figure.png',
                        wildcard=wildcard)
        if fd.open() == OK:
            self.view.save_image(fd.path)
            

    def about(self, ui_info):
        text = ['rfspace.py', 'VNoel 2011 CNRS', 'Radflux Day Time Series viewer', 'SIRTA']
        dlg = AboutDialog(parent=ui_info.ui.control, additions=text)
        dlg.open()


def main():
    
    # rfmap = RFMaps(file_to_open='data/CERES_EBAF_TOA_Terra_Edition1A_200003-200510.mat')
    rfmap = RFMaps()
    
    controller = RFController(view=rfmap)
    rfmap.configure_traits(handler=controller)


if __name__ == '__main__':
    main()

