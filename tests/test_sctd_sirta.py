#!/usr/bin/env python
#encoding:utf-8

import sctd_sirta

def test_length():
    
    f = sctd_sirta.sctd('../data/sctd_sirta_sansprofiles_lidars_beta_cc_20131031.nc')
    assert len(f.time)==94968