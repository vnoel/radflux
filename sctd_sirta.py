#!/usr/bin/env python
#encoding:utf-8

import numpy as np
import netCDF4
from datetime import datetime, timedelta
import matplotlib.dates as mdates

class sctd(dict):
    
    def constrain_period(self, start, end):
        
        ltime = len(self['time_num'])
        ltime_photometer = len(self['time_photometer_num'])
        
        idx = (self.datetimes >= start) & (self.datetimes <= end)
        for var in self:
            if len(var) != ltime:
                continue
            self[var] = self[var][idx]
        self.datetimes = self.datetimes[idx]
        
        idx = (self.datetimes_photometer >= start) & (self.datetimes_photometer <= end)
        for var in self:
            if len(var) != ltime_photometer:
                continue
            self[var] = self[var][idx]
        self.datetimes_photometer = self.datetimes_photometer[idx]
    
    def _read_variables(self, variable_names):
        
        for variable_name in variable_names:
            ncvar = self.nc.variables[variable_name][:]
            ncvar = ncvar.data
            idx = (ncvar < -999.9)
            ncvar[idx] = np.nan
            self[variable_name] = ncvar
    
    def temp_to_celsius(self):
        if 'tas' not in self:
            return
        self['tas'] -= 273.
    
    def __init__(self, sirtafile='data/sctd_sirta_sansprofiles_lidars_beta_cc_20131031.nc', variable_names=None):
        
        print 'Loading ', sirtafile
        
        self.nc = netCDF4.Dataset(sirtafile, 'r')
        
        # hours since 1970-01-01 00:00:0.0, UTC
        time = self.nc.variables['time'][:]
        self.datetimes = np.array([datetime(1970, 1, 1) + timedelta(hours=np.int(x)) for x in time])
        self['time_num'] = mdates.num2epoch(mdates.date2num(self.datetimes))

        time_photometer = self.nc.variables['time_photometer'][:]
        self.datetimes_photometer = np.array([datetime(1970, 1, 1) + timedelta(hours=np.int(x)) for x in time_photometer])
        self['time_photometer_num'] = mdates.num2epoch(mdates.date2num(self.datetimes_photometer))

        if variable_names is not None:
            self._read_variables(variable_names)
        
        self.constrain_period(datetime(2006,1,1), datetime(2014,1,1))
        
    def close(self):
        self.nc.close()
        