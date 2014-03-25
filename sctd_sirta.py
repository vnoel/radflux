#!/usr/bin/env python
#encoding:utf-8

import numpy as np
import netCDF4
from datetime import datetime, timedelta
import matplotlib.dates as mdates


class sctd(dict):
    
    time_variables = ['sw', 'sw_cs', 'lw', 'lw_cs', 'temp']
    time_photometer_variables = ['solar_zenith_angle']
    
    def constrain_period(self, start, end):
        
        idx = (self.datetimes >= start) & (self.datetimes <= end)
        for var in self.time_variables:
            self[var] = self[var][idx]
        self['time_num'] = self['time_num'][idx]
        self.datetimes = self.datetimes[idx]
        
        idx = (self.datetimes_photometer >= start) & (self.datetimes_photometer <= end)
        for var in self.time_photometer_variables:
            self[var] = self[var][idx]
        self['time_photometer_num'] = self['time_photometer_num'][idx]
        self.datetimes_photometer = self.datetimes_photometer[idx]
    
    
    def __init__(self, sirtafile='data/sctd_sirta_sansprofiles_lidars_beta_cc_20131031.nc'):
        
        print 'Loading ', sirtafile
        
        nc = netCDF4.Dataset(sirtafile, 'r')
        
        # hours since 1970-01-01 00:00:0.0, UTC
        time = nc.variables['time'][:]
        self.datetimes = np.array([datetime(1970, 1, 1) + timedelta(hours=np.int(x)) for x in time])
        self['time_num'] = mdates.num2epoch(mdates.date2num(self.datetimes))
                
        # surface downwelling longwave radiation - W/m2
        # uncertainty ±5 W/m2 at 1000 W/m2
        # missing value -999.96
        self['lw'] = nc.variables['rlds'][:]
        self['lw'][self['lw'] < 0] = np.nan
        
        # surface downwelling shortwave radiation - W/m2
        # uncertainty ±5 W/m2 at 1000 W/m2
        # missing value -999.96
        self['sw'] = nc.variables['rsds'][:]
        self['sw'] = self['sw'].data
        self['sw'][self['sw'] < 0] = np.nan
        
        # surface downwelling shortwave radiation - clear sky
        self['sw_cs'] = nc.variables['rsdscs'][:]
        self['sw_cs'] = self['sw_cs'].data
        self['sw_cs'][self['sw_cs']<0] = np.nan
        
        # surface downwelling longwave radiation - clear sky
        self['lw_cs'] = nc.variables['rldscs'][:]
        self['lw_cs'][self['lw_cs'] < 0] = np.nan
        
        # Average near-surface(2m) air temperature
        self['temp'] = nc.variables['tas'][:]
        self['temp'] = self['temp'].data - 273.
        self['temp'][self['temp'] < -100] = np.nan
        
        # 
        time_photometer = nc.variables['time_photometer'][:]
        self.datetimes_photometer = np.array([datetime(1970, 1, 1) + timedelta(hours=np.int(x)) for x in time_photometer])
        self['time_photometer_num'] = mdates.num2epoch(mdates.date2num(self.datetimes_photometer))
        
        # solar angle
        self['solar_zenith_angle'] = nc.variables['solar_zenith_angle'][:]
        self['solar_zenith_angle'] = self['solar_zenith_angle'].data
        self['solar_zenith_angle'][self['solar_zenith_angle'] < -90] = np.nan
        
        self.constrain_period(datetime(2006,1,1), datetime(2014,1,1))
        
        nc.close()
        