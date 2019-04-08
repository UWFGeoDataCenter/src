# -*- coding: utf-8 -*-
"""
Created on Fri Apr  5 15:21:00 2019

@author: jmorgan3
"""

from arcgis.gis import GIS

afile = open("auth_file.config", "r")
for line in afile:
    pieces = line.split(",")
    agol_url  = pieces[0]
    agol_user = pieces[1]
    agol_pass = pieces[2]

gis = GIS(agol_url, agol_user, agol_pass)
uwfBuildings = gis.content.get('ea0c379c597c409e843939710add43f2')
display(uwfBuildings)

