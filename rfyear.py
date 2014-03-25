#!/usr/bin/env python
# encoding: utf-8
"""
radflux_sw_year.py

Created by Vincent Noel - LMD/CNRS on 2011-11-08.
"""

import numpy as np

import os, tempfile
from reportlab.pdfgen import canvas

import chaco.api as chaco
from chaco.tools.api import ZoomTool, PanTool

from pyface.api import OK, FileDialog, AboutDialog, MessageDialog

from traits.api import HasTraits, Instance
from traits.api import Bool, Str, Button
from traitsui.api import View, VGroup, HGroup, Item, UItem, Spring
from traitsui.api import Handler
from traitsui.menu import MenuBar, Menu, Action, CloseAction, Separator

from enable.api import ComponentEditor

from chaco.scales.api import CalendarScaleSystem
from chaco.scales_tick_generator import ScalesTickGenerator

from radflux_utils import radflux_year_read, meteo_year_read

from sctd_sirta import sctd


def add_date_axis(plot):
    
    bottom_axis = chaco.PlotAxis(plot, orientation='bottom', 
                        tick_generator=ScalesTickGenerator(scale=CalendarScaleSystem()))
    plot.underlays.append(bottom_axis)


class RFTimeSeries(HasTraits):
    
    '''
    Generic RFTimeSeries
    needs to be subclassed as SWRFTimeSeries or LWRFTimeSeries
    will not plot stuff by itself
    '''

    window_title = 'RadFlux Year Time Series'
    plot_title = Str('')
    basetitle = 'SIRTA RadFlux data - '
    
    # needs to set those in the __init__ of the subclass
    data_to_plot = 'NA'
    clearsky_name = 'NA'
    
    rfcontainer = Instance(chaco.Plot)
    sacontainer = Instance(chaco.Plot)
    tcontainer = Instance(chaco.Plot)
    
    show_clearsky = Bool(False)
    reset_zoom_button = Button('Reset Zoom')
    open_sw_file_button = Button('Open SW Data File...')
    open_lw_file_button = Button('Open LW Data File...')

    traits_view = View(
        # this part of the view is only shown when plot_title is not ""
        # ie when there is data
        VGroup(
            UItem('rfcontainer', editor=ComponentEditor()),
            HGroup(
                Item('show_clearsky', label='Show Clear-Sky Model'),
                UItem('reset_zoom_button'),
                padding=10
            ),
            HGroup(
                UItem('sacontainer', editor=ComponentEditor()),
                UItem('tcontainer', editor=ComponentEditor()),
            ),
            visible_when = 'plot_title != ""'
        ), 
        # this part of the view is shown when there is no data
        VGroup(
            Spring(),
            HGroup(
                UItem('open_sw_file_button', padding=15, springy=True),
                UItem('open_lw_file_button', padding=15, springy=True),
            ),
            Spring(),
            visible_when='plot_title == ""',
        ),
        menubar = MenuBar(
            Menu(
                CloseAction,
                Separator(),
                Action(name='Open SW data file...', action='open_sw_file'),
                Action(name='Open LW data file...', action='open_lw_file'),
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
    
    
    def _open_sw_file_button_fired(self):
        
        if self.data is not None:
            # this should never happen
            return
            
        self.handler.open_sw_file(None)
        
    
    def _open_lw_file_button_fired(self):
        
        if self.data is not None:
            return
            
        self.handler.open_lw_file(None)
        
    
    def _reset_zoom_button_fired(self):
    
        if self.data is None:
            # this should never happen
            return
    
        self.rfcontainer.index_range.set_bounds(self.data['time_num'][0], self.data['time_num'][-1])
        idx = np.isfinite(self.data[self.data_to_plot])
        value_range = (np.min(self.data[self.data_to_plot][idx]) - 50, np.max(self.data[self.data_to_plot][idx]) + 50)
        self.rfcontainer.value_range.set_bounds(*value_range)
    
    
    def _show_clearsky_changed(self):

        if self.data is None:
            # this should never happen
            return

        self.clearskyplot.visible = self.show_clearsky
        self.rfcontainer.legend.visible = True
        self.rfcontainer.request_redraw()
    
    
    def open_year(self):
        
        # data = radflux_year_read(rf_file)
        data = sctd()
        self.data = data
        # if data is not None:
            # self.time = data['time']
            # self.date = data['date']
            # self.data = data
            # self.meteo = meteo_year_read(self.date.year, os.path.dirname(rf_file))

        
    def save_multipage_pdf(self, pdfname, plots_list):
        
        c = canvas.Canvas(pdfname)

        for obj in plots_list:
            
            f = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            filename = f.name
            f.close()

            window_size = obj.outer_bounds
            gc = chaco.PlotGraphicsContext(window_size)
            gc.render_component(obj)
            gc.save(filename)

            c.setPageSize(window_size)
            c.drawInlineImage(filename, 0, 0)
            c.showPage()
            
            os.unlink(filename)
            
        c.save()
        
        
    def save_image(self, imagefile):
        
        print 'Save image ', imagefile
        self.save_multipage_pdf(imagefile, [self.rfcontainer, self.sacontainer, self.tcontainer])
        
    
    def set_data_in_plot(self):
        
        if self.data is None or self.rfcontainer is None or self.rfdata is None:
            return
            
        self.plot_title = self.basetitle # + str(self.date.year)
        self.rfcontainer.y_axis.title = self.data_to_plot + ' (W/m2)'
        
        self.rfcontainer.title = self.plot_title
        self.rfdata.set_data('index', self.data['time_num'])
        self.rfdata.set_data('value', self.data[self.data_to_plot])
        self.rfdata.set_data('clearsky', self.data[self.clearsky_name])
        self.rfcontainer.index_mapper.domain_limits = (self.data['time_num'][0], self.data['time_num'][-1])
    
        self.sadata.set_data('index', self.data['time_photometer_num'])
        self.sadata.set_data('value', self.data['solar_zenith_angle'])
        
        self.tdata.set_data('index', self.data['time_num'])
        self.tdata.set_data('value', self.data['temp'])
        
        self._reset_zoom_button_fired()
    
    
    def init_double_time_series(self, data, name1, name2, title, label1, label2):
        
        plot = chaco.Plot(data, name=title, width=300, height=100)
        plotline1 = plot.plot(('index', name1), name=label1)
        plotline2 = plot.plot(('index', name2), name=label2, visible=False, color='green', alpha=0.5)
        chaco.add_default_grids(plot)
        plot.underlays.remove(plot.x_axis)
        add_date_axis(plot)
        plot.x_axis.title = 'Time'
        plot.title = title
        plot.legend.visible = False
        
        plot.padding_bottom = 25
        
        return plot, plotline1, plotline2
        
    
    def init_time_series(self, data, name, xrange, color):
        
        plot = chaco.Plot(data)
        plot.plot(('index', 'value'), name=name, color=color)
        plot.x_axis.title = 'Time'
        plot.y_axis.title = name
        plot.underlays.remove(plot.x_axis)
        add_date_axis(plot)
        
        plot.index_range = xrange
        
        plot.padding = 50
        plot.padding_top = 10

        return plot


    def __init__(self, file_to_open='data/sctd_sirta_sansprofiles_lidars_beta_cc_20131031.nc', data_to_plot='NA', clearsky_name='NA'):

        self.data = None

        self.rfdata = chaco.ArrayPlotData()
        self.rfdata.set_data('value', [])
        self.rfdata.set_data('index', [])
        self.rfdata.set_data('clearsky', [])
        plot, plotline1, plotline2 = self.init_double_time_series(  self.rfdata, 
                                                                    'value', 'clearsky', 
                                                                    self.plot_title, 
                                                                    'measurements', 'model')
        self.rfcontainer = plot
        self.rfplotline = plotline1[0]
        self.clearskyplot = plotline2[0]
        self.clearskyplot.visible = self.show_clearsky
        
        self.rfcontainer.overlays.append(ZoomTool(self.rfcontainer, axis='index', tool_mode='range', 
                                                drag_button='left', always_on=True, restrict_to_data=True))
        self.rfcontainer.tools.append(PanTool(self.rfcontainer, drag_button='right', 
                                                constrain=True, constrain_direction='x', restrict_to_data=True))
        
        self.sadata = chaco.ArrayPlotData()
        self.sadata.set_data('value', [])
        self.sadata.set_data('index', [])
        plot = self.init_time_series(self.sadata, 'Solar Angle', self.rfcontainer.index_range, 'darkred')
        self.sacontainer = plot
        self.sacontainer.value_range.set_bounds(10, 180)
        
        self.tdata = chaco.ArrayPlotData()
        self.tdata.set_data('value', [])
        self.tdata.set_data('index', [])
        plot = self.init_time_series(self.tdata, 'Temperature [degC]', self.rfcontainer.index_range, 'darkblue')
        self.tcontainer = plot
        
        self.data_to_plot = data_to_plot
        self.clearsky_name = clearsky_name
        
        if file_to_open is not None:
            self.open_year(file_to_open)
            self.set_data_in_plot()
            

class SWRFTimeSeries(RFTimeSeries):


    def __init__(self, file_to_open=None):
        
        RFTimeSeries.__init__(self, file_to_open=file_to_open)

        self.window_title = 'SW RadFlux Year Time Series'
        


class RFController(Handler):

    view = Instance(SWRFTimeSeries)

    def init(self, info):

        self.view = info.object
        self.view.handler = self


    def open_file(self):

        wildcard = 'ASCII data files (*.txt)|*.txt|All files|*.*'
        fd = FileDialog(action='open', 
                        title='Open RadFlux Year Time Series', 
                        wildcard=wildcard)
        if fd.open() == OK:

            basename = os.path.basename(fd.path)
            if not (basename.endswith('.txt') and basename.startswith('radflux_')) or basename.startswith('radflux_1a'):
                msg = MessageDialog(message='Not a valid year RadFlux file. Valid files follow the form radflux_YYYY.txt', severity='warning', title='invalid file')
                msg.open()
                return None

            return fd.path
        
        return None

        
    def open_sw_file(self, ui_info):
        
        # swfile = self.open_file()
        # if swfile is None:
        #     return

        # print 'Opening ' + 
        self.view.open_year()
        self.view.data_to_plot = 'sw'
        self.view.clearsky_name = 'sw_cs'
        self.view.set_data_in_plot()
            
            
    def open_lw_file(self, ui_info):

        # lwfile = self.open_file()
        # if lwfile is None:
        #     return

        # print 'Opening ' + lwfile
        self.view.open_year()
        self.view.data_to_plot = 'lw'
        self.view.clearsky_name = 'lw_cs'
        self.view.set_data_in_plot()


    def save_plot(self, ui_info):
        
        wildcard = 'PDF Figure files (*.pdf)|*.pdf|All files|*.*'
        fd = FileDialog(action='save as', 
                        title='Same figures in PDF file', 
                        default_filename='figure.pdf',
                        wildcard=wildcard)
        if fd.open() == OK:
            self.view.save_image(fd.path)
            

    def about(self, ui_info):
        text = ['rfyear.py', 'VNoel 2011 CNRS', 'Radflux Day Time Series viewer', 'SIRTA']
        dlg = AboutDialog(parent=ui_info.ui.control, additions=text)
        dlg.open()


def main():
    
    # rftimeseries = RFTimeSeries(file_to_open='data/radflux_1a_1min_v04_20100604_000000_1440.txt')
    rftimeseries = SWRFTimeSeries()
    controller = RFController(view=rftimeseries)
    rftimeseries.configure_traits(handler=controller)


if __name__ == '__main__':
    main()

