# -*- coding: utf-8 -*-
#=====================
# For ArcGIS Pro

import csv, os, arcpy, simplekml, shutil
from arcpy import da
import pandas as pd
from distutils.dir_util import copy_tree
import PIL
import os.path
from PIL import Image
import re

aprx = arcpy.mp.ArcGISProject("CURRENT")
map = aprx.activeMap

# Define Maximum number of photos to support
MAX_PHOTOS = 20

#enable Overwrite
arcpy.env.overwriteOutput = True

#User Input variables----------------------

geodb = arcpy.GetParameterAsText(0)
exportFolder = os.path.dirname(geodb) # get parent folder
photoLyr = "Photograph"
photoTableLyr = "Photograph__ATTACH"

#Folder variables----------------------
cultFolder = exportFolder + '\\Cultural'
fieldFolder = cultFolder + '\\Field'
fieldPhotoFolder = fieldFolder + '\\Photos'
reportFolder = cultFolder + '\\Report'
reportPhotoFolder = reportFolder + '\\Photos'
reportResizedPhotoFolder = reportFolder + '\\Photos Resized'
if not os.path.exists(reportResizedPhotoFolder):
    os.makedirs(reportResizedPhotoFolder)
kmzFolder = exportFolder+'\\KMZ'
kmzPhotoFolder = kmzFolder + '\\Photos'
kmzResizedPhotoFolder = kmzFolder + '\\Photos Resized'
if not os.path.exists(kmzResizedPhotoFolder):
    os.makedirs(kmzResizedPhotoFolder)
shpFolder = exportFolder+'\\SHP'
shpPhoto = geodb + '\\Photograph'
workingFolder = exportFolder + '\\WorkingFiles'
templateFolder = r'J:\Cultural Resources\GIS\Photopage\Photopage Template V3'
reportfolder = f'{cultFolder}\Report'

#---------------------------------------------------
#Copy Folders Over
copy_tree(templateFolder, exportFolder)


#----------------------------------------------------
#Check for Photograph and Photoattachment table

layers_to_check = ["Photograph", "Photograph__ATTACH"]

existing_layers = [layer.name for layer in map.listLayers()]

for layer_name in layers_to_check:
	if layer_name not in existing_layers:
		print(f"{layer_name} not found. Adding to map.")
		# Add the layer from the geodatabase
		layer_path = f"{geodb}/{layer_name}"

		shp_lyr = map.addDataFromPath(layer_path)

#------------------------------------------------------
#Join Photograph_ATTACH and Photogrpah Feature Classes
try:
	arcpy.AddJoin_management(photoTableLyr, "REL_GLOBALID", photoLyr, "GLOBALID")
	arcpy.AddMessage('\nJoining Photograph_ATTACH and Photograph')
except:
	arcpy.AddError('\nPlease Add the Photograph feature class and/or Photograph__ATTACH table to the map\n')
	exit()

#Calculate OID using DATA_SIZE Field
arcpy.management.CalculateField(photoTableLyr, "Photograph__ATTACH.DATA_SIZE", "!Photograph.OBJECTID!", "PYTHON3", '', "TEXT", "NO_ENFORCE_DOMAINS")

#Calculate Photograph Name using the CONTENT_TYPE field
arcpy.management.CalculateField(photoTableLyr, "Photograph__ATTACH.CONTENT_TYPE", 'str(!Photograph__ATTACH.DATA_SIZE!) + "_" + str(!Photograph__ATTACH.ATTACHMENTID!) + "_" + str(!Photograph__ATTACH.ATT_NAME!)', "PYTHON3", '', "TEXT", "NO_ENFORCE_DOMAINS")

# ----------------------------------------------------
#Export PhotoTableRAW.csv
photoTableRAW = workingFolder + "\\PhotoTableRAW.csv"
csv_delimiter = ","

# Read in fields and get field names
fld_list = arcpy.ListFields(photoTableLyr)
fld_names = [fld.name for fld in fld_list]

# Open the CSV file and write out field names and data
with open(photoTableRAW, 'w', newline="",encoding="utf-8") as csv_file:
  writer = csv.writer(csv_file, delimiter=csv_delimiter)
  writer.writerow(fld_names)
  with arcpy.da.SearchCursor(photoTableLyr, fld_names) as cursor:
    for row in cursor:
      writer.writerow(row)
  csv_file.close()

arcpy.AddMessage('PhotoTableRAW.csv Exported')

arcpy.management.RemoveJoin(photoTableLyr)
arcpy.AddMessage('Removing Join\n')


#---------------------
# #Export Photos

#Field Copy
arcpy.AddMessage('Exporting Photographs')
with da.SearchCursor(photoTableLyr, ['DATA', 'CONTENT_TYPE']) as cursor:
    for item in cursor:
        attachment = item[0]
        filename = item[1]
        open(fieldPhotoFolder + os.sep + filename, 'wb').write(attachment.tobytes())
        del item
        del attachment

copy_tree(fieldPhotoFolder, reportPhotoFolder)
copy_tree(fieldPhotoFolder, kmzPhotoFolder)

#---------------------
#Export Photograph to Photograph SHP
arcpy.env.workspace = geodb

# Dynamic Photofields Generation
photofields_list = []
photofields_list.append('OID1 "OID1" true true false 2 Short 0 0 ,First,#,Photograph,OBJECTID,-1,-1')
photofields_list.append('ReportNo "Report Photo # (Ignore if in the field)" true true false 50 Text 0 0 ,First,#,Photograph,ReportNo,-1,-1')
photofields_list.append('Category "Category (Ignore if in the field)" true true false 254 Text 0 0 ,First,#,Photograph,Category,-1,-1')
photofields_list.append('Excavator "Photographer" true true false 60 Text 0 0 ,First,#,Photograph,Excavator,-1,-1')
photofields_list.append('Ex_Other "Photographer (Other)" true true false 25 Text 0 0 ,First,#,Photograph,Ex_Other,-1,-1')

for i in range(1, MAX_PHOTOS + 1):
    photofields_list.append(f'P{i}Name "P{i}Name" true true false 50 Text 0 0 ,First,#,Photograph,P{i}Name,-1,-1')
    photofields_list.append(f'P{i}_Direc "Photo {i} Direction" true true false 254 Text 0 0 ,First,#,Photograph,P{i}_Direc,-1,-1')
    photofields_list.append(f'P{i}_Cat "Photo {i} Category" true true false 254 Text 0 0 ,First,#,Photograph,P{i}_Cat, -1,-1')
    photofields_list.append(f'P{i}_Descr "Photo {i} Description" true true false 254 Text 0 0 ,First,#,Photograph,P{i}_Descr,-1,-1')

photofields_list.append('ESRIGNSS_P "Position source type" true true false 2 Short 0 0 ,First,#,Photograph,ESRIGNSS_POSITIONSOURCETYPE,-1,-1')
photofields_list.append('ESRIGNSS_R "Receiver Name" true true false 50 Text 0 0 ,First,#,Photograph,ESRIGNSS_RECEIVER,-1,-1')
photofields_list.append('ESRIGNSS_L "Latitude" true true false 8 Double 0 0 ,First,#,Photograph,ESRIGNSS_LATITUDE,-1,-1')
photofields_list.append('ESRIGNSS_1 "Longitude" true true false 8 Double 0 0 ,First,#,Photograph,ESRIGNSS_LONGITUDE,-1,-1')
photofields_list.append('ESRIGNSS_A "Altitude" true true false 8 Double 0 0 ,First,#,Photograph,ESRIGNSS_ALTITUDE,-1,-1')
photofields_list.append('ESRIGNSS_H "Horizontal Accuracy (m)" true true false 8 Double 0 0 ,First,#,Photograph,ESRIGNSS_H_RMS,-1,-1')
photofields_list.append('ESRIGNSS_V "Vertical Accuracy (m)" true true false 8 Double 0 0 ,First,#,Photograph,ESRIGNSS_V_RMS,-1,-1')
photofields_list.append('ESRIGNSS_F "Fix Time" true true false 8 Date 0 0 ,First,#,Photograph,ESRIGNSS_FIXDATETIME,-1,-1')
photofields_list.append('ESRIGNSS_2 "Fix Type" true true false 2 Short 0 0 ,First,#,Photograph,ESRIGNSS_FIXTYPE,-1,-1')
photofields_list.append('ESRISNSR_A "Compass reading (°)" true true false 8 Double 0 0 ,First,#,Photograph,ESRISNSR_AZIMUTH,-1,-1')

photofields = ";".join(photofields_list)


arcpy.AddMessage('Exporting Photograph SHP')
photoNew = arcpy.conversion.FeatureClassToFeatureClass(in_features="Photograph", out_path=shpFolder, out_name="Photograph.shp", field_mapping=photofields)


#adding Northing/Easting
arcpy.AddMessage('Adding Northing/Eastin to Photograph SHP')
arcpy.management.AddField(photoNew, "Northing", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.management.AddField(photoNew, "Easting", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

#calculating WGS_84 Northing/East for KML purposes
arcpy.AddMessage('Calculating WGS_84 Northing/Eastin to Photograph SHP')
try:
    sr_wgs84 = arcpy.SpatialReference(4326)
    with arcpy.da.UpdateCursor(photoNew, ['SHAPE@', 'Northing', 'Easting']) as cursor:
        for row in cursor:
            if row[0]:
                geom = row[0]
                # Project geometry to WGS 1984
                projected_geom = geom.projectAs(sr_wgs84)
                # Get centroid coordinates (Y=Lat, X=Long)
                row[1] = projected_geom.centroid.Y
                row[2] = projected_geom.centroid.X
                cursor.updateRow(row)
except Exception as e:
	arcpy.AddMessage(f"Northing/Easting not calculated, THIS NEEDS FIXED FOR THE KMZ. Error: {str(e)}")
	pass

#---------------------
#Adding Photograph Names to PhotographSHP
photographSHP = exportFolder + '\\SHP\\Photograph.shp'

#Create Empty Photo Name Dictionaries
PhotoNameDic = {}

#Load the csv
photoCSV = open(workingFolder + '\\PhotoTableRAW.csv', mode='r',encoding="utf-8")

#Populate the Photograph Dictionary
for row in photoCSV:
    rowList = list(row.split(","))
    if len(rowList) < 8: continue # Basic safety check
    OID = rowList[7] #Photograph.OBJECTID
    PhotoNo = rowList[4] #Photograph__ATTACH.ATT_NAME
    PhotoNa = rowList[3] #Photograph__ATTACH.CONTENT_TYPE

    # Parse Photo Number
    match = re.search(r"Photo (\d+)\.jpg", PhotoNo)
    if match:
        p_num = int(match.group(1))
        if p_num <= MAX_PHOTOS:
            if int(OID) not in PhotoNameDic:
                PhotoNameDic[int(OID)] = {}
            PhotoNameDic[int(OID)][p_num] = PhotoNa


#Fields to relate and update
# Generate field list dynamically: ['OID1', 'P1Name', 'P2Name', ..., 'P{MAX}Name']
field1 = ['OID1'] + [f'P{i}Name' for i in range(1, MAX_PHOTOS + 1)]

#Relate OID IDs and insert corresponding Photograph Names into Photograph SHP
arcpy.AddMessage("Adding Photograph Names to Photograph SHP")

with arcpy.da.UpdateCursor(photographSHP, field1) as cursor:
    for row in cursor: #row[x] refers to the fied1 list
        oid = row[0]
        if oid in PhotoNameDic:
            for p_num, photo_name in PhotoNameDic[oid].items():
                if p_num <= MAX_PHOTOS:
                    # Index of P{p_num}Name is p_num (since OID is index 0)
                    row[p_num] = photo_name
            cursor.updateRow(row)


#Export PhotoTableRAW.csv
output_csv = workingFolder + "\\Photograph.csv"
csv_delimiter = ","

# Read in fields and get field names
fld_list = arcpy.ListFields(photographSHP)
fld_names = [fld.name for fld in fld_list]

# Open the CSV file and write out field names and data
with open(output_csv, 'w', newline="",encoding="utf-8") as csv_file:
  writer = csv.writer(csv_file, delimiter=csv_delimiter)
  writer.writerow(fld_names)
  with arcpy.da.SearchCursor(photographSHP, fld_names) as cursor:
    for row in cursor:
      writer.writerow(row)
  csv_file.close()

# All done.
arcpy.AddMessage('Exporting PhotoTableRAW.csv')

#---------------------------------
#create Photolog.csv
arcpy.AddMessage('Creating Photolog.csv\n')
photoLog = workingFolder +'\\Photolog.csv'

#creates Photolog.csv in WorkingFiles folder
with open(photoLog, 'w', newline="",encoding="utf-8") as photoLogCSV:
    csv_writer = csv.writer(photoLogCSV, delimiter = ',')
    #Writes header tuple
    photoLogTuple = ('Sort', 'Category', 'Field Photo #', 'Report Photo #', 'Site', 'Description', 'Direction', 'Photographer', 'Date')
    csv_writer.writerow(photoLogTuple)

    #load PhotoTableRAW.csv
    with open(photoTableRAW, 'r',encoding="utf-8") as csv_file:
        csv_reader = csv.DictReader(csv_file)
        #create photolog entry for each photograph
        for line in csv_reader:
            att_name = line.get('Photograph__ATTACH.ATT_NAME', '')
            match = re.search(r"Photo (\d+)\.jpg", att_name)
            if match:
                p_num = int(match.group(1))
                if p_num <= MAX_PHOTOS:
                    Sort = ''
                    Category = ''
                    FieldPhotoNo = line.get('Photograph__ATTACH.CONTENT_TYPE', '')
                    ReportPhotoNo = ''
                    Site = ''

                    # Dynamically get attributes, defaulting to empty string if field missing
                    p_cat = line.get(f'Photograph.P{p_num}_Cat', '')
                    p_descr = line.get(f'Photograph.P{p_num}_Descr', '')
                    p_direc = line.get(f'Photograph.P{p_num}_Direc', '')

                    Description = f"{p_cat}, {p_descr}"
                    Direction = p_direc
                    Photographer = line.get('Photograph.Excavator', '')
                    uDate = line.get('Photograph.ESRIGNSS_FIXDATETIME', '')

                    photoLogTuple = (Sort, Category, FieldPhotoNo, ReportPhotoNo, Site, Description, Direction, Photographer, uDate)
                    csv_writer.writerow(photoLogTuple)

# close the Photolog.csv
photoLogCSV.close()


df = pd.read_csv(output_csv)

df.replace("&", " and ", inplace = True)
df.replace('"', "'", inplace = True)
df.replace("<", " less than ", inplace = True)
df.replace(">", " greater than ", inplace = True)
df.replace("?", " ", inplace = True)
df.replace("  ", " ", inplace = True)

df.to_csv(output_csv, index = False, encoding="utf-8")

#=======================#
#KML Code

arcpy.AddMessage('Creating the KML')
inputFile = csv.DictReader(open(exportFolder + '\WorkingFiles\Photograph.csv',encoding="utf-8"))

kml = simplekml.Kml()
kml.parsetext(parse=False)

for row in inputFile:
    #replace special characters
    descriptions = []
    for i in range(1, MAX_PHOTOS + 1):
        if f'P{i}_Descr' in row:
            descriptions.append(f'P{i}_Descr')

    for descr in descriptions:
        row[descr] = row[descr].replace('&','and')
        row[descr] = row[descr].replace('<',' less than ')
        row[descr] = row[descr].replace('>',' greather than ')
        row[descr] = row[descr].replace('  ',' ')

    title = "OID " + row['OID1'] #Photo name without extension
    lat = row['Northing']
    long = row['Easting']

    #the description table
    full_description = ""
    for i in range(1, MAX_PHOTOS + 1):
        p_name_key = f'P{i}Name'
        if p_name_key in row and len(row[p_name_key]) > 4:
            p_name = row[p_name_key]
            p_cat = row.get(f'P{i}_Cat', '')
            p_descr = row.get(f'P{i}_Descr', '')

            # HTML generation
            desc_html = f'<img src="Photos Resized\\{p_name}" width="500px" border="0"></img><p>Photograph {p_name.replace(".jpg", "")}: {p_cat}, {p_descr}.</p>'
            full_description += desc_html

    pnt = kml.newpoint(name=title, coords=[(long, lat)])  # creates the basic point
    pnt.description = full_description
    pnt.snippet.maxlines = 0 #removes the snippet in google earth places

#print(kml.kml()) #prints the code to QA/QC
kml.save(exportFolder + '\\KMZ\\Field Photographs.kml')

#============================================
# Resize Photographs
arcpy.AddMessage('Resizing Photographs')

failed_photos = []

try:
    for file in os.listdir(kmzPhotoFolder):
        if 'Thumbs' not in file and file.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tif')):
            f_img = os.path.join(kmzPhotoFolder, file)
            f_img_resized = os.path.join(kmzResizedPhotoFolder, file)
            f_report_img_resized = os.path.join(reportResizedPhotoFolder, file)
            try:
                img = Image.open(f_img)
                width,height = img.size
                if width > 1100 or height > 1100:
                    # Use standard ANTIALIAS (LANCZOS) resampling for quality
                    img = img.resize((int(width*0.3), int(height*0.3)), Image.Resampling.LANCZOS)
                    img.save(f_img_resized)
                    img.save(f_report_img_resized)
                else:
                    # Just copy if it doesn't need resizing, to ensure consistency in the folder
                    img.save(f_img_resized)
                    img.save(f_report_img_resized)
            except Exception as e:
                failed_photos.append(f"{file} ({e})")
except Exception as e:
    arcpy.AddMessage(f'Error accessing photo folder: {e}')

if not failed_photos:
    arcpy.AddMessage('Resized all photos successfully')
else:
    arcpy.AddMessage('Failed to resize the following photos:')
    for failure in failed_photos:
        arcpy.AddMessage(failure)

arcpy.AddMessage('Making the KMZ')
shutil.make_archive(f'{reportfolder}\Field Photographs', format='zip', root_dir=kmzFolder)

zipfile = f'{reportfolder}\Field Photographs.zip'
kmzname = f'{reportfolder}\Field Photographs.kmz'
try:
	os.remove(kmzname)
except:
	pass

os.rename(zipfile, kmzname)
