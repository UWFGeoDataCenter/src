############################################################################################################################
## Script: AGOLSQLSync.py
## Author: Jeremy Mullins, Derek Morgan
## Date: 06/05/2019
##
## Description:
##        This script is the test script for syncing data between ArcGIS Online
##        and an MS SQL Server database.
##
## Required prerequisites:
##        - ArcGIS API for Python
##            (https://developers.arcgis.com/python/guide/install-and-set-up/)
##
##        - pyodbc Module
##            (https://github.com/mkleehammer/pyodbc)
##                to install after download, open Python command
##                prompt and type the following:
##                    -- conda install pyodbc  --
##
##        - pandas Module
##            (https://pandas.pydata.org/pandas-docs/stable/)
##                to install after download, open Python command
##                prompt and type the following:
##                    -- conda install pandas --
##
##        - MS ODBC Driver for SQL Server (v17)
##            (https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server?view=sql-server-2017)
##
############################################################################################################################

###########################################################################
## SECTION 1: ACCESSING FEATURE LAYER DATA, PREPARE CSV FOR SQL DATABASE ##
###########################################################################
# import all necessary modules
from arcgis.gis import GIS
from arcgis import geometry
from copy import deepcopy
import pyodbc as sql
import pandas as pd
import configparser
import zipfile
import os

# read config file
config = configparser.ConfigParser()
config.read('')

# assign config variables
agolURL = config['AGOL']['URL']
agolUSER = config['AGOL']['USER']
agolPW = config['AGOL']['PW']
sqlDRVR = config['SQL']['SQLDRVR']
sqlSERV = config['SQL']['SERVER']
sqlDB = config['SQL']['DB']
sqlUSER = config['SQL']['USER']
sqlPW = config['SQL']['PW']
iD = config['SCRIPT']['itemID']
csvNAME = config['SCRIPT']['csvTITLE']
csvLOC = config['SCRIPT']['csvLOC']
zipLOC = config['SCRIPT']['zipLOC']
csvDOC = config['SCRIPT']['csvDOC']
newTEMP1 = config['SCRIPT']['newTEMP1']
newTEMP2 = config['SCRIPT']['newTEMP2']
csv2TEMP = config['SCRIPT']['csv2TEMP']
newINS1 = config['SCRIPT']['newINS1']
newINS2 = config['SCRIPT']['newINS2']
SQL2CSV = config['SCRIPT']['SQL2CSV']
sql2CSVout = config['SCRIPT']['sql2CSVout']
delTEMP1 = config['SCRIPT']['delTEMP1']
delTEMP2 = config['SCRIPT']['delTEMP2']

# sign into AGOL acct
gis = GIS(agolURL,agolUSER,agolPW)

# get feature layer in question
featureLayer = gis.content.get(iD)

# export feature layer as CSV (ZIP file)
output_file = featureLayer.export(title=csvNAME,export_format="CSV")
output_file.download(csvLOC)

# unzip downloaded ZIP folder containing feature layer as CSV
zip_ref = zipfile.ZipFile(zipLOC,'r')
zip_ref.extractall(csvLOC)
zip_ref.close()

# delete ZIP folder on disk and CSV collection file in AGOL
os.remove(zipLOC)
output_file.delete()

# read CSV; replace NaNs with '000'
df = pd.read_csv(csvDOC)
df.fillna('000',inplace=True)


######################################################
## SECTION 2: CONNECT TO SQL, PERFORM DATA ANALYSIS ##
######################################################
#Connect to SQL db and assign cursor
conn = sql.connect('Driver='+sqlDRVR+';'
                      'Server='+sqlSERV+';'
                      'Database='+sqlDB+';'
                      'trusted_connection=yes;'
                      'UID='+sqlUSER+';'
                      'PWD='+sqlPW+';')
cursor = conn.cursor()

# create temporary tables in SQL db
cursor.execute(newTEMP1)
cursor.commit()
cursor.execute(newTEMP2)
cursor.commit()

# insert CSV into temporary table
for index,row in df.iterrows():
    cursor.execute(csv2TEMP,row[''],
                   row[''],
                   row['']
                  )
cursor.commit()

# compare tables and look for non-duplicated FIDs
cursor.execute(newINS1)
cursor.commit()

# compare tables and look for any updated records in prod table
cursor.execute(newINS2)
cursor.commit()

##########################################################################
## SECTION 3: CONVERT SQL UPDATES TO CSV, PUSH TO AGOL, PERFORM UPDATES ##
##########################################################################
# export SQL data to CSV
outCSVscript = SQL2CSV
df2 = pd.read_sql_query(outCSVscript,conn)
df2.to_csv(sql2CSVout)

# read the SQL update CSV
csv2 = sql2CSVout
updates_df_2 = pd.read_csv(csv2)

# query all features in target AGOL feature layer
fl = featureLayer.layers[0]
flquery = fl.query()

# determine which features overlap between update CSV and AGOL feature layer using an INNER join
overlap_rows = pd.merge(left = flquery.sdf, right = updates_df_2, how = 'inner', on = 'FID')

# create list containing corrected features
updatefeatures = []
all_features = flquery.features

# for loop to prepare updated geometries and attributes for each of the updated features
# geometry module used to project coordinates form geographic to projected coordinate system
for fid in overlap_rows['FID']:
    # get the feature to be updated
    original_feature = [f for f in all_features if f.attributes['FID'] == fid][0]
    ftbu = deepcopy(original_feature)
    # get the matching row from csv
    matching_row = updates_df_2.where(updates_df_2.FID == fid).dropna()
    # get geometries in the destination coordinate system
    input_geometry = {'y':float(matching_row['']),
                      'x':float(matching_row[''])}
    output_geometry = geometry.project(geometries = [input_geometry],
                                       in_sr = 4326,
                                       out_sr = flquery.spatial_reference['latestWkid'],
                                       gis = gis)
    # assign the updated values
    ftbu.geometry = output_geometry[0]
    ftbu.attributes[''] = matching_row[''].values[0]
    ftbu.attributes[''] = int(matching_row[''])
    # add this to the list of features to be updated
    updatefeatures.append(ftbu)
    
# call the edit_features() method of FeatureLayer object and pass features to the updates parameter
if len(updatefeatures) > 0:
    fl.edit_features(updates = updatefeatures)

###########################################################
## SECTION 4: CLEAN UP DATA WITHIN SQL AND LOCAL MACHINE ##
###########################################################
# delete temporary tables
cursor.execute(delTEMP1)
cursor.commit()
cursor.execute(delTEMP2)
cursor.commit()

# close and delete cursor; close SQL db connection
cursor.close()
del cursor
conn.close()

# remove all CSVs
os.remove(csvDOC)
os.remove(sql2CSVout)
