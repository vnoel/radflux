#!/usr/bin/env python
#encoding:utf-8

import numpy as np
import netCDF4
from datetime import datetime, timedelta
import matplotlib.dates as mdates


class sctd(dict):
    
    def __init__(self, sirtafile='data/sctd_sirta_sansprofiles_lidars_beta_cc_20131031.nc'):
        
        print 'Loading ', sirtafile
        
        nc = netCDF4.Dataset(sirtafile, 'r')
        
        # hours since 1970-01-01 00:00:0.0, UTC
        time = nc.variables['time'][:]
        self['time'] = np.array([datetime(1970, 1, 1) + timedelta(hours=np.int(x)) for x in time])
        self['time_num'] = mdates.num2epoch(mdates.date2num(self['time']))        
                
        # surface downwelling longwave radiation - W/m2
        # uncertainty ±5 W/m2 at 1000 W/m2
        # missing value -999.96
        self['lw'] = nc.variables['rlds'][:]
        
        # surface downwelling shortwave radiation - W/m2
        # uncertainty ±5 W/m2 at 1000 W/m2
        # missing value -999.96
        self['sw'] = nc.variables['rsds'][:]
        self['sw'] = np.ma.masked_invalid(self['sw'])
        self['sw'] = np.ma.masked_where(self['sw'] < 0, self['sw'])
        
        # surface downwelling shortwave radiation - clear sky
        self['sw_cs'] = nc.variables['rsdscs'][:]
        
        # surface downwelling longwave radiation - clear sky
        self['lw_cs'] = nc.variables['rldscs'][:]
        
        # Average near-surface(2m) air temperature
        self['temp'] = nc.variables['tas'][:]
        self['temp'] = np.ma.masked_where(self['temp'] < -100, self['temp'])
        
        # 
        time_photometer = nc.variables['time_photometer'][:]
        self['time_photometer'] = np.array([datetime(1970, 1, 1) + timedelta(hours=np.int(x)) for x in time_photometer])
        self['time_photometer_num'] = mdates.num2epoch(mdates.date2num(self['time_photometer']))
        
        # solar angle
        self['solar_zenith_angle'] = nc.variables['solar_zenith_angle'][:]
        
        nc.close()
        