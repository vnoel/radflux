#!/usr/bin/env python
# encoding: utf-8
"""
radflux_utils.py

Created by Vincent Noel on 2011-07-12.
Copyright (c) 2011 LMD/CNRS. All rights reserved.
"""

import numpy as np
import glob
from datetime import datetime, timedelta

import matplotlib.dates as mdates
import h5py
from scipy.io import matlab


def coastlines_read(path):
    coastlines = matlab.loadmat(path + '/coastlines.mat')['tmp']
    lon = coastlines[:,0]
    lat = coastlines[:,1]
    idx = np.isfinite(lon) & np.isfinite(lat)
    lon = lon[idx]
    lat = lat[idx]
    return lon, lat


def lw_clearsky(temp, rh):
    
    # clearsky longwave flux as a function of temperature
    a = 1.05
    b = 1./7
    tk = temp + 273.15
    esat = 0.611 * np.exp(temp/(tk-35.86))
    e = esat * rh
    epsilon = a * np.power(e / tk, b)
    sigma = 5.67e-8
    lw = epsilon * sigma * np.power(tk, 4)
    
    return lw


def sw_clearsky(solar_angle):
    
    a = 1100
    b = 1.0987
    c = 0.9472
    solar_angle = solar_angle / 180. * np.pi
    sw = np.abs(a * np.power(np.cos(solar_angle), b) * np.power(c, 1./np.cos(solar_angle)))
    return sw


def fix_lon(var):
    
    var2 = np.zeros_like(var)
    var2[:,:,180:] = var[:,:,:180]
    var2[:,:,:180] = var[:,:,180:]
    return var2


def ceres_nc_read(ceresfile):
    
    import netCDF4
    
    nc = netCDF4.Dataset(ceresfile)
    lon = nc.variables['lon'][:]
    lat = nc.variables['lat'][:]
    time = nc.variables['time'][:]
    swup = nc.variables['toa_sw_all_mon'][:]
    lwup = nc.variables['toa_lw_all_mon'][:]
    swupclr = nc.variables['toa_sw_clr_mon'][:]
    lwupclr = nc.variables['toa_lw_clr_mon'][:]
    nc.close()
    
    lon2 = np.zeros_like(lon)
    lon2[180:] = lon[:180]
    lon2[:180] = lon[180:]
    lon = lon2
    
    swup = fix_lon(swup)
    lwup = fix_lon(lwup)
    swupclr = fix_lon(swupclr)
    lwupclr = fix_lon(lwupclr)
    
    dates = np.array([datetime(2000,3,1) + timedelta(days=int(i)) for i in time])
    
    data = {'time':time, 'lon':lon, 'lat':lat, 'swup':swup, 'lwup':lwup, 'swupclr':swupclr, 'lwupclr':lwupclr, 'dates':dates}
    return data


def ceres_read(ceresfile):
    
    # mat = matlab.loadmat(ceresfile)
    # lon = mat['lon']
    # lat = mat['lat']
    
    h5file = h5py.File(ceresfile)
    lon = h5file['lon'][:]
    lat = h5file['lat'][:]
    time = h5file['time'][:]
    lon = lon.squeeze()
    lat = lat.squeeze()
    time = time.squeeze()
    # swup = np.mean(h5file['swup'][:,:], axis=2)
    swup = h5file['swup'][:]
    lwup = h5file['lwup'][:]
    swupclr = h5file['swupclr'][:]
    lwupclr = h5file['lwupclr'][:]
    
    h5file.close()
    
    data = {'time':time, 'lon':lon, 'lat':lat, 'swup':swup, 'lwup':lwup, 'swupclr':swupclr, 'lwupclr':lwupclr}
    return data


def radflux_read(radfile):
    
    x = np.loadtxt(radfile, converters={0:mdates.datestr2num})
    # time = np.array(mdates.num2date(x[:,0]), dtype=np.float64)
    date = mdates.num2date(x[0,0])
    time = mdates.num2epoch(x[:,0])
    sangle = x[:,1]
    totalf = x[:,4]
    lw = x[:,5]
    data = dict()
    data['solar angle'] = sangle
    data['clear sky'] = sw_clearsky(sangle)
    data['total SW flux'] = np.array(totalf, dtype=np.float64)
    data['LW flux'] = np.array(lw, dtype=np.float64)
    
    return time, data, date
    

def radflux_year_read(radfile):
    
    x = np.genfromtxt(radfile, delimiter=',', missing_values='NaN')
    if x.ndim < 2:
        return
    
    yy = x[:,0]
    mm = x[:,1]
    dd = x[:,2]
    hh = x[:,3]
    dates = [datetime(int(y), int(m), int(d), int(h)) for (y, m, d, h) in zip(yy, mm, dd, hh)]
    date = dates[0].date()
    dates = mdates.date2num(dates)
    dates = mdates.num2epoch(dates)
    solar_angle = x[:,6]
    sw_global = x[:,9]
    lw = x[:,10]
    sw_clearsky = x[:,11]
    lw_clearsky = x[:,12]
    data = {'solar angle': solar_angle, 'lw_clearsky': lw_clearsky, 'sw_clearsky': sw_clearsky,
                'total SW flux':sw_global, 'LW flux':lw, 'date':date, 'time':dates}
    return data



def find_meteo_file(date, path):
    
    mask = path + '/meteoz1_*_%04d%02d%02d*.asc' % (date.year, date.month, date.day)
    files = glob.glob(mask)
    if len(files) < 1:
        print mask
        print files
        print 'problem ! Could not find meteo files'
        return None
    else:
        meteo_file = files[0]
    return meteo_file


def meteo_read(date, path):
    
    meteo_file = find_meteo_file(date, path)
    if meteo_file is not None:
        x = np.loadtxt(meteo_file, converters={0:mdates.datestr2num})
        time = mdates.num2epoch(x[:,0])
        meteo = {'time':time, 'temperature':x[:,3], 'rh':x[:,4]}
        return meteo
    else:
        return None


def meteo_year_read(year, path):
    
    print 'Reading meteo data for ', year
    meteo_file = path + '/MeteoZ1_SIRTA_Z1_1hour%04d.txt' % (year)
    print 'Trying ', meteo_file
    x = np.loadtxt(meteo_file, delimiter=',')
    y = np.int32(x[:,0])
    m = np.int32(x[:,1])
    d = np.int32(x[:,2])
    hh = np.int32(x[:,3])
    mm = np.int32(x[:,4])
    temperature = x[:,5]
    matemperature = np.ma.masked_where(temperature < -100, temperature)
    temperature[temperature < -100] = np.nan
    
    time = []
    for i in np.r_[0:len(y)]:
        time.append(datetime(y[i], m[i], d[i], hh[i], mm[i]))
    epochtime = mdates.num2epoch(mdates.date2num(time))
    
    meteo = {'time':time, 'Temperature [C]':matemperature, 'epochtime':epochtime, 'temperature':temperature}
    
    return meteo


def solar_year_read(year):
    print 'Reading solar data'
    solar_file = 'data/solar_angle_SIRTA_year.txt'
    x = np.loadtxt(solar_file)
    m = np.int32(x[:,0])
    d = np.int32(x[:,1])
    hh = np.int32(x[:,2]) - 1
    time = []
    angle = []
    for i in np.r_[0:len(m)]:
        # the solar angle file gives 31 days to every month.
        # great.
        try:
            date = datetime(year, m[i], d[i], hh[i])
        except ValueError:
            continue
        time.append(date)
        angle.append(x[i,3])
    
    solar = {'time':time, 'Solar Angle [deg]':angle}
    return solar

def main():
    pass


if __name__ == '__main__':
    main()

