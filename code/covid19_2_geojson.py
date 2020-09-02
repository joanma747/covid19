# -*- coding: utf-8 -*-
"""
Import a COVID-19 csv file and edit a config.json to include this data in a vector capa

"""

import click
import logging
#https://docs.python.org/3/library/tempfile.html
import tempfile
#https://stackoverflow.com/questions/17960942/attributeerror-module-object-has-no-attribute-urlretrieve
import urllib.request
#https://docs.python.org/3/library/csv.html
from pathlib import Path
import csv
import json
import sys
import os
import copy
import datetime

#https://stackoverflow.com/questions/736043/checking-if-a-string-can-be-converted-to-float-in-python
def isfloat(value):
  try:
    float(value)
    return True
  except ValueError:
    return False

def isint(value):
  try:
    int(value)
    return True
  except ValueError:
    return False

def AccumulateDatesCsv(csvreader, geoid, date, fdate, accumulate, cond_field, cond_value, remove_field):

    #Removing all rows that does not respect the condition values. Rearranging date format.
    csvreader2=[]
    for row in csvreader:
        i=0
        different=False
        while i<len(cond_field):
            field=cond_field[i]
            if row[field]!=cond_value[i]:
                different=True;
                #if there is other possible values for the same field, I check the other values.
                ii=i+1
                while ii<len(cond_field) and field==cond_field[ii]:
                    if row[field]==cond_value[ii]:
                        different=False;
                        break;
                    ii+=1
                if different:
                    break
            i+=1
            while i<len(cond_field) and field==cond_field[i]:
                i+=1

        if different==False:
            csvreader2.append({})
            for varname, da in row.items():
                different=True
                for field in cond_field:
                    if (varname==field):
                        different=False
                        break
                if different==True:
                    if varname==date:
                        if fdate=="dd/mm/yyyy" and len(da)==10 and da.count('/')==2:
                            d=da.split('/')
                            csvreader2[-1][varname]="%04d-%02d-%02d" % (int(d[2]), int(d[1]), int(d[0]))
                        else:
                            csvreader2[-1][varname]=da
                    else:
                        csvreader2[-1][varname]=da
                        
    #determining the first and last date.
    csvreader2.sort(key=lambda row: (row[date]))
    initial_date=csvreader2[0][date];
    d=initial_date.split('-')
    initial_dt=datetime.datetime(int(d[0]), int(d[1]), int(d[2]))
    final_date=csvreader2[-1][date];
    d=final_date.split('-')
    final_dt=datetime.datetime(int(d[0]), int(d[1]), int(d[2]))
    
    #csvreader2.sort(key=lambda row: (row[idx] for in geoid, row[date]))
    csvreader2.sort(key=lambda row: (row[geoid], row[date]))
    
    #Removing all repetions in geoid and accumulate by date.
    csvreader3=[]
    total=0
    previous="$%ImpossibleName%$"
    next_dt = initial_dt
    for row in csvreader2:
        if row[geoid]!=previous:
            while next_dt<=final_dt and previous!="$%ImpossibleName%$":
                csvreader3[-1][next_dt.strftime("%Y")+"-"+next_dt.strftime("%m")+"-"+next_dt.strftime("%d")]=total
                next_dt += datetime.timedelta(days=1)
            csvreader3.append(copy.copy(row))
            del csvreader3[-1][accumulate]
            del csvreader3[-1][date]
            for rf in remove_field:
                del csvreader3[-1][rf]
            total=0
            previous=row[geoid]
            next_dt = initial_dt
        d=row[date].split('-')
        dt=datetime.datetime(int(d[0]), int(d[1]), int(d[2]))
        while next_dt<dt:
            csvreader3[-1][next_dt.strftime("%Y")+"-"+next_dt.strftime("%m")+"-"+next_dt.strftime("%d")]=total
            next_dt += datetime.timedelta(days=1)
        #This happens several times for the same date but this is not a problem because the last one is the right one.
        total+=int(row[accumulate])
        csvreader3[-1][row[date]]=total
        d=row[date].split('-')
        next_dt=datetime.datetime(int(d[0]), int(d[1]), int(d[2])) + datetime.timedelta(days=1)

    while next_dt<=final_dt and previous!="$%ImpossibleName%$":
        csvreader3[-1][next_dt.strftime("%Y")+"-"+next_dt.strftime("%m")+"-"+next_dt.strftime("%d")]=total
        next_dt += datetime.timedelta(days=1)

    return csvreader3

def ExtractDatesCsv(csvreader, geoid, date, fdate, extract_field):

    #Rearranging date format and maintaing only the field we are interested in
    csvreader2=[]
    for row in csvreader:
        csvreader2.append({})
        for varname, da in row.items():
            if varname==date:
                if fdate=="dd/mm/yyyy" and len(da)==10 and da.count('/')==2:
                    d=da.split('/')
                    csvreader2[-1][varname]="%04d-%02d-%02d" % (int(d[2]), int(d[1]), int(d[0]))
                else:
                    csvreader2[-1][varname]=da
            elif varname==extract_field or varname==geoid: 
                csvreader2[-1][varname]=da
                        
    #Determining the first and last date.
    csvreader2.sort(key=lambda row: (row[date]))
    initial_date=csvreader2[0][date];
    d=initial_date.split('-')
    initial_dt=datetime.datetime(int(d[0]), int(d[1]), int(d[2]))
    final_date=csvreader2[-1][date];
    d=final_date.split('-')
    final_dt=datetime.datetime(int(d[0]), int(d[1]), int(d[2]))
    
    #csvreader2.sort(key=lambda row: (row[idx] for in geoid, row[date]))
    csvreader2.sort(key=lambda row: (row[geoid], row[date]))
    
    #Transforming rows into date fields
    csvreader3=[]
    previous="$%ImpossibleName%$"
    next_dt = initial_dt
    for row in csvreader2:
        if row[geoid]!=previous:
            csvreader3.append({})
            csvreader3[-1][geoid]=row[geoid]
            while next_dt<=final_dt and previous!="$%ImpossibleName%$":
                csvreader3[-1][next_dt.strftime("%Y")+"-"+next_dt.strftime("%m")+"-"+next_dt.strftime("%d")]=row[extract_field]
                next_dt += datetime.timedelta(days=1)
            previous=row[geoid]
            next_dt = initial_dt
        d=row[date].split('-')
        dt=datetime.datetime(int(d[0]), int(d[1]), int(d[2]))
        while next_dt<dt:
            csvreader3[-1][next_dt.strftime("%Y")+"-"+next_dt.strftime("%m")+"-"+next_dt.strftime("%d")]=row[extract_field]
            next_dt += datetime.timedelta(days=1)
        csvreader3[-1][row[date]]=row[extract_field]
        d=row[date].split('-')
        next_dt=datetime.datetime(int(d[0]), int(d[1]), int(d[2])) + datetime.timedelta(days=1)

    while next_dt<=final_dt and previous!="$%ImpossibleName%$":
        csvreader3[-1][next_dt.strftime("%Y")+"-"+next_dt.strftime("%m")+"-"+next_dt.strftime("%d")]=row[extract_field]
        next_dt += datetime.timedelta(days=1)

    return csvreader3

def tranformDatesCsv(csvreader, prefix_var, fdate):
    csvreader2=[]
    for row in csvreader:
        csvreader2.append({})
        for varname, da in row.items():
            if fdate=="m/d/yy" and varname.count('/')==2:
                d=varname.split('/')
                v=prefix_var+ "20%02d-%02d-%02d" % (int(d[2]), int(d[0]), int(d[1]))
                csvreader2[-1][v]=da
            elif fdate=="yyyy-mm-dd" and len(varname)==10 and varname.count('-')==2:
                csvreader2[-1][prefix_var+varname]=da
            else:
                csvreader2[-1][varname]=da
    return csvreader2

def csv2geojson(csvreader, long, lat):
    data={"type": "FeatureCollection", "features": []}
    #l=0;
    for row in csvreader:
        data["features"].append({"type": "Feature", "geometry": { "type": "Point", "coordinates": [float(row[long]), float(row[lat])]}, "properties": {}})
        #data.features.append({"type": "Feature", "geometry": { "type": "Point", "coordinates": []}, "properties": {})
        for varname, da in row.items():
            if varname == long or varname == lat:
                continue
            if isint(da):
                data["features"][-1]["properties"][varname]=int(da)
            elif isfloat(da):
                data["features"][-1]["properties"][varname]=float(da)
            else:
                data["features"][-1]["properties"][varname]=da
        #l+=1
    return data

# def csv_geoid2geojson(csvreader, geojson, geoid, add_longlat, add_field):
#     data={"type": "FeatureCollection", "features": []}
#     for row in csvreader:
#         for obj in geojson["features"]:
#             if obj["properties"][geoid]==row[geoid]:
#                 data["features"].append({"type": "Feature", "geometry": { "type": "Point", "coordinates": [obj["geometry"]["coordinates"][0], obj["geometry"]["coordinates"][1]]}, "properties": {}})
#                 for varname, da in row.items():
#                     if isint(da):
#                         data["features"][-1]["properties"][varname]=int(da)
#                     elif isfloat(da):
#                         data["features"][-1]["properties"][varname]=float(da)
#                     else:
#                         data["features"][-1]["properties"][varname]=da
#                 break
#     return data    

def csv_multigeoid2geojson(csvreader, long, lat, geoid, geoid_type, geojson, geojsonid, add_longlat, add_field):
    data={"type": "FeatureCollection", "features": []}
    for row in csvreader:
        for obj in geojson["features"]:
            different=False
            #for nom in geoid:
            for idx, nom in enumerate(geoid):
                if len(geoid_type)>idx and geoid_type[idx]=="int":
                    if int(obj["properties"][geojsonid[idx]])!=int(row[nom]):
                        different=True
                        break
                else:
                    if obj["properties"][geojsonid[idx]]!=row[nom]:
                        different=True
                        break
            if different==False:
                data["features"].append({"type": "Feature", "geometry": { "type": "Point", "coordinates": []}, "properties": {}})
                if add_longlat:
                    data["features"][-1]["geometry"]["coordinates"].append(obj["geometry"]["coordinates"][0])
                    data["features"][-1]["geometry"]["coordinates"].append(obj["geometry"]["coordinates"][1])
                else:
                    data["features"][-1]["geometry"]["coordinates"].append(float(row[long]))
                    data["features"][-1]["geometry"]["coordinates"].append(float(row[lat]))
                for varname, da in row.items():
                    if add_longlat==False and (varname == long or varname == lat):
                        continue
                    if varname in geoid:
                        data["features"][-1]["properties"][varname]=da
                    elif da==None:
                        data["features"][-1]["properties"][varname]=""
                    elif isint(da):
                        data["features"][-1]["properties"][varname]=int(da)
                    elif isfloat(da):
                        data["features"][-1]["properties"][varname]=float(da)
                    else:
                        data["features"][-1]["properties"][varname]=da
                for nom in add_field:
                    if nom in obj["properties"]:
                        data["features"][-1]["properties"][nom]=obj["properties"][nom]
                break
    return data    

def updateConfigJSON(mmnfile, layer, prefix_var, objectes, atrib, estil, dies, add_var, layer_geoid, obj_geoid, geoid_type):
    ParamCtrl = json.load(mmnfile)
#https://stackoverflow.com/questions/8653516/python-list-of-dictionaries-search
    capa=next((item for item in ParamCtrl["capa"] if item["nom"] == layer), None)
    if capa==None:
        raise ValueError("I cannot find the capa in the map browser configuration file")
    if add_var:
        capa["estil"].extend(estil)
        if (objectes!=None):
            for obj in objectes["features"]:
                already_present=False
                for capa_obj in capa["objectes"]["features"]:
                    different=False
                    for idx, nom in enumerate(obj_geoid):
                        #if obj["properties"][geojsonid[idx]]!=row[nom]:
                        if not layer_geoid[idx] in capa_obj["properties"]:
                            different=True
                            break
                        if len(geoid_type)>idx and geoid_type[idx]=="int":
                            if int(capa_obj["properties"][layer_geoid[idx]])!=int(obj["properties"][nom]):
                                different=True
                                break
                        else:
                            if capa_obj["properties"][layer_geoid[idx]]!=obj["properties"][nom]:
                                different=True
                                break
                    # for varname, da in obj["properties"].items():
                    #     if len(varname)==len(prefix_var) + 10 and varname.count('-')==2:
                    #         continue
                    #     #https://stackoverflow.com/questions/1323410/should-i-use-has-key-or-in-on-python-dicts                      
                    #     if not varname in capa_obj["properties"] or capa_obj["properties"][varname]!=da:
                    #         different=True
                    #         break
                    if different==False:
                        already_present=True
                        #only adding the temporal properties
                        for varname, da in obj["properties"].items():
                            if len(varname)==len(prefix_var) + 10 and varname.count('-')==2:
                                capa_obj["properties"][varname]=da
                        break
                if (already_present==False):
                    #adding the object altogether
                    capa["objectes"]["features"].append(obj);
        #for atr in atrib:
            #if "serieTemporal" in atr:
                #capa["atributs"].append(atr)
        capa["atributs"].extend(atrib)
        for dia in dies:
            i_data=0;
            already_present=False
            for capa_dia in capa["data"]:
                if dia["year"]<capa_dia["year"]:
                    break;
                if dia["year"]>capa_dia["year"]:
                    i_data+=1
                    continue
                if dia["month"]<capa_dia["month"]:
                    break
                if dia["month"]>capa_dia["month"]:
                    i_data+=1
                    continue
                if dia["day"]<capa_dia["day"]:
                    break
                if dia["day"]>capa_dia["day"]:
                   i_data+=1
                   continue
                already_present=True
                break;
            if already_present==False:
                if i_data==len(capa["data"]):
                    capa["data"].append(dia)
                else:
                    capa["data"].insert(i_data, dia)
    else:
        capa["objectes"]=objectes
        capa["atributs"]=atrib
        capa["estil"]=estil
        capa["data"]=dies
    return ParamCtrl

def rgb_string_to_hex(rgb):
    c=rgb.split(',')
    return '#%02x%02x%02x' % (int(c[0]),int(c[1]),int(c[2]))

def delayTimeTemplate(s, delay):
    #tname.replace("{time?f=ISO}", "{time?f=ISO&day=+2}")
    inici=0
    while -1!=s[inici:].find('{time'):
        inici+=s[inici:].find('{time')+5;
        s2=s[inici:]
        if -1==s2.find('}'):
            break;
        fi=inici+s2.find('}')
        s2=s[inici:fi]
        found=False
        if len(s2)>0 and s2[0]=='?':
            s2=s[inici+1:fi]
            kvp=s2.split('&')
            for idx, pair in enumerate(kvp):
                s_pair=pair.split('=')
                if s_pair[0]=="day" and len(s_pair)==2:
                    d=int(s_pair[1])+delay
                    if d<0:
                        kvp[idx]="day="+str(d)
                    elif delay>0:
                        kvp[idx]="day=+"+str(d)
                    else:
                        kvp.pop(idx);
                    found=True
                    break
        else:
            kvp=[]
        if found==False:
            if delay<0:
                kvp.append("day="+str(delay))
            elif delay>0:
                kvp.append("day=+"+str(delay))
        if len(kvp)>0:
            s=s[0:inici]+"?"+'&'.join(kvp)+s[fi:]
            inici+=1+len('&'.join(kvp))+1
        else:                         
            s=s[0:inici]+s[fi:]
            inici+=1
    return s
        
#https://click.palletsprojects.com/en/7.x/options/
@click.command()
@click.argument('href')
@click.argument('layer')
@click.option('-href-enc', default='ansi', help="Encoding of the remote file")
@click.option('-href-type', default='href', type=click.Choice(['href', 'local', 'formula']), help="Type of href. For debuging purposes it can be 'file' to indicate a local file. A 'formula' can be provided to create atributs and estil based on preexisting property values; use ` instead of '.")
@click.option('-href-delimiter', default=',', help="href parameter is a CSV file. This parameter specifies CSV delimiter")
@click.option('-mmn', help="Path of the config.json of the MiraMon Map Browser. If not specified, it will not be updates with the new dates")
@click.option('-is-acc/-is-not-acc', default=True, help="-is-acc (default) indicates the resulting variable is an accumation in time. -is-not-acc indicates that the resulting variable is a daily value (it is not an accumulation and will not be accumulated; possible if -extract-field' is provided or if '-date' is NOT provided')")
@click.option('-add-var/-no-add-var', default=False, help="-no-add-var (default) removes all other variables. -add-var add a variable and reviews the dates")
@click.option('-prefix-var', default="cfr", help="Prefix to add to temporal field")
@click.option('-desc-var', default="Confirmed cases", help="Description of the variable")
@click.option('-color', default="255,0,0", help="Color of the cercles and lines in diagrams")
@click.option('-long', default="Long", help="Name of the longitude field in the CSV. If -add-longlat is used it is ignored and the long lat in the input geojson is used instead")
@click.option('-lat', default="Lat", help="Name of the latitude field in the CSV. If -add-longlat is used it is ignored and the long lat in the input geojson is used instead")
@click.option('-geoid', multiple=True, default="[cod_ine]", help="Name of the id field in the CSV that connects with a property name geojsonid in the input geojson (When -add-var==False it is strongly recommenced that the name in the geojson and the name in the CSV are the same and will become the name in the objctes in the config.json)")
@click.option('-geoid-type', multiple=True, help="Type of comparison for the field in the CSV that connects with a property name geojsonid in the input geojson. (By default comparison are done as strings, use 'int' to force comparisons as integers)")
@click.option('-geojson', help="Name of the GeoJSON file that has the long lat values and other files that are no in the CSV. use -add-longlat and -add-field to control what to add")
@click.option('-geojsonid', multiple=True, help="Name of the id field in the geojson that connects with a property name geoid in the input CSV (If not provided the it is considered equal to geoid. When add-var the name in geojsonid should be the name used in the objectes in the config.json)")
@click.option('-add-longlat/-no-add-longlat', default=False, help="Add the lat and long from the input geojson into the config.json")
@click.option('-add-field', multiple=True, help="Name of the field in the input geojson that needs to be added to the config.json")
@click.option('-fdate', default="yyyy-mm-dd", help="Format of the date fields in the CSV")
@click.option('-date', help="Name of the field containing dates in the CSV. If not specified, we assume that all fields with the fdate format contain dates. In addition, this field is used fo accumulation. If it is not specified, data is supposed to be already accumulated")
#@click.option('-initial-date', default="2020-02-02", help="Initial date to accumulate. Dates with nodata are added as a repetion of the previous date")
@click.option('-extract-field', help="Name of the field to extract from the CSV as a temporal series. It requeres date to be declared")
@click.option('-accumulate', default="NumCasos", help="Name of the field with numbers to accumulate CSV")
@click.option('-cond-field', multiple=True, help="Name of the field that should be equal to -cond-value to be considered")
@click.option('-cond-value', multiple=True, help="Value towards the field values should be equal to, to be considered. All field should be equal to at least one value. If more than one value for the same field needs to be provided, the -cond-field will  be repeated consecutively")
@click.option('-remove-field', multiple=True, help="Fields that shuold be removed. Used only if -date is provided")
@click.option('-population', help="Name of the field containing the population.")
@click.option('-area', help="Name of the field containing the area in square meters.")
@click.option('-a-circle', default=0.05, type=float, help="Area of the circle that is used as the bases for the circle radious")
@click.option('-export-geojson', help="Name of the file to export the geojson result as an additional result.")

              
def main(href, layer, href_enc, href_type, href_delimiter, mmn, is_acc, add_var, prefix_var, desc_var, color, long, lat, geoid, geoid_type, geojson, geojsonid, add_longlat, add_field, fdate, date, extract_field, accumulate, cond_field, cond_value, remove_field, population, area, a_circle, export_geojson):
    """
    Import a COVID-19 csv file and edit a config.json to include this data in a vector capa
    The csv need to have a fields with a name that is a date in fdate format. These fields contains
    the values of a single variable in time.
    Additional field can be added from a input geojson file in the vector capa if -add-longlat and -add-field are indicated) 
    The format used in https://github.com/CSSEGISandData/COVID-19/tree/master/csse_covid_19_data/csse_covid_19_time_series is directly supported
    
    Params: 
    <href> Base URL to download the csv data.
    <folder> folder of the layer in the MiraMon Map server. The rel5 should existe inside.
    <layer> name of the layer. It should be the same as the name of the folder in the server, the name of the REL5 and the name of the layer in the config.json.       
    
    Example:
    copy C:\inetpub\wwwroot\covid19\config.json C:\inetpub\wwwroot\covid19\config_yesterday.json /y
    python covid19_2_geojson.py https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv world-covid-19 -mmn C:\inetpub\wwwroot\covid19 -fdate m/d/yy -geojson D:\datacube\covid-19\centroidesWorld.geojson -geoid "Province/State" -geoid "Country/Region" -add-field Population -add-field "Urban Population" -add-field "Land Area" -population Population -area "Land Area"
    python covid19_2_geojson.py https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv world-covid-19 -mmn C:\inetpub\wwwroot\covid19 -add-var -prefix-var dead -desc-var Deaths -geoid "Province/State" -geoid "Country/Region" -color 50,50,50 -fdate m/d/yy -population Population -area "Land Area"
    python covid19_2_geojson.py https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_recovered_global.csv world-covid-19 -mmn C:\inetpub\wwwroot\covid19 -add-var -prefix-var rcv -desc-var "Recovered reported" -geoid "Province/State" -geoid "Country/Region" -color 0,128,0 -fdate m/d/yy -population Population -area "Land Area" -export-geojson D:\datacube\covid-19\github-covid19\datasets\covid19-world-john-jopkins.geojson
    python covid19_2_geojson.py "p['cfr{time?f=ISO&day=-15}']-p['dead{time?f=ISO}']" -href-type formula world-covid-19 -mmn C:\inetpub\wwwroot\covid19 -add-var -prefix-var ree -desc-var "Recovered estimated" -color 0,128,0 -population Population -area "Land Area"
    python covid19_2_geojson.py "p['cfr{time?f=ISO}']-p['dead{time?f=ISO}']-p['rcv{time?f=ISO}']" -href-type formula world-covid-19 -mmn C:\inetpub\wwwroot\covid19 -add-var -prefix-var acr -desc-var "Active reported" -color 215,54,0 -population Population -area "Land Area"
    python covid19_2_geojson.py "p['cfr{time?f=ISO}']-p['cfr{time?f=ISO&day=-15}']" -href-type formula world-covid-19 -mmn C:\inetpub\wwwroot\covid19 -add-var -prefix-var ace -desc-var "Active estimated" -color 215,54,0 -population Population -area "Land Area"
    python sort_config_json.py world-covid-19 -mmn C:\inetpub\wwwroot\covid19 -section atributs -i-item 0 -i-item 1 -i-item 2 -i-item 3 -i-item 4 -i-item 5 -i-item 37 -i-item 38 -i-item 36 -i-item 31 -i-item 32 -i-item 30 -i-item 7 -i-item 8 -i-item 6 -i-item 13 -i-item 14 -i-item 12 -i-item 25 -i-item 26 -i-item 24 -i-item 19 -i-item 20 -i-item 18 -i-item 39 -i-item 33 -i-item 9 -i-item 15 -i-item 27 -i-item 21 -i-item 40 -i-item 34 -i-item 10 -i-item 16 -i-item 28 -i-item 22 -i-item 41 -i-item 35 -i-item 11 -i-item 17 -i-item 29 -i-item 23 -i-item 42
    
    python covid19_2_geojson.py "https://cnecovid.isciii.es/covid19/resources/datos_provincias.csv" prov-spain-covid-19 -href-enc utf8 -mmn C:\inetpub\wwwroot\covid19 -geojson "D:\datacube\covid-19\centroidesProvSpain.geojson" -geoid provincia_iso -add-longlat -add-field PROV -add-field CCAA -add-field Population -add-field "Land Area" -accumulate "num_casos" -fdate dd/mm/yyyy -date fecha -remove-field num_casos_prueba_pcr -remove-field num_casos_prueba_test_ac -remove-field num_casos_prueba_otras -remove-field num_casos_prueba_desconocida -a-circle 0.3 -population Population -area "Land Area" -export-geojson D:\datacube\covid-19\github-covid19\datasets\covid19-prov-spain.geojson
    python covid19_2_geojson.py "p['cfr{time?f=ISO}']-p['cfr{time?f=ISO&day=-15}']" -href-type formula prov-spain-covid-19 -mmn C:\inetpub\wwwroot\covid19 -add-var -prefix-var ace -desc-var "Active estimated" -color 215,54,0 -population Population -area "Land Area"
    fart c:\inetpub\wwwroot\covid19\config.json "\"descripcio\": \"provincia_iso\"" "\"descripcio\": \"C\xC3\xB3digo de Provincia\"" --c-style
    fart c:\inetpub\wwwroot\covid19\config.json "\"descripcio\": \"PROV\"" "\"descripcio\": \"Provincia\"" --c-style
    fart c:\inetpub\wwwroot\covid19\config.json "\"descripcio\": \"CCAA\"" "\"descripcio\": \"Comunidad aut\xC3\xB3noma\"" --c-style
    python sort_config_json.py prov-spain-covid-19 -mmn C:\inetpub\wwwroot\covid19 -section atributs -i-item 0 -i-item 1 -i-item 2 -i-item 3 -i-item 4 -i-item 5 -i-item 13 -i-item 14 -i-item 12 -i-item 7 -i-item 8 -i-item 6 -i-item 15 -i-item 9 -i-item 16 -i-item 10 -i-item 17 -i-item 11 -i-item 18 

    python covid19_2_geojson.py "D:\docs\Recerca\covid-19\España\ActualizacionCovidAgregat.csv" ccaa-spain-covid-19 -href-type local -href-delimiter ";" -mmn C:\inetpub\wwwroot\covid19 -geojson "D:\datacube\covid-19\centroides17CCAA.geojson" -geoid cod_ine -date Fecha -extract-field "CasosAcc" -add-longlat -add-field CCAA -add-field Population -add-field "Land Area" -a-circle 0.3 -population Population -area "Land Area"
    python covid19_2_geojson.py "D:\docs\Recerca\covid-19\España\ActualizacionCovidAgregat.csv" ccaa-spain-covid-19 -href-type local -href-delimiter ";" -mmn C:\inetpub\wwwroot\covid19 -geojson "D:\datacube\covid-19\centroides17CCAA.geojson" -geoid cod_ine -date Fecha -extract-field "IngresadosAcc" -prefix-var hsp -desc-var "Hospitalized" -color 255,230,0 -a-circle 0.3 -add-var -add-longlat -population Population -area "Land Area"
    python covid19_2_geojson.py "D:\docs\Recerca\covid-19\España\ActualizacionCovidAgregat.csv" ccaa-spain-covid-19 -href-type local -href-delimiter ";" -mmn C:\inetpub\wwwroot\covid19 -geojson "D:\datacube\covid-19\centroides17CCAA.geojson" -geoid cod_ine -date Fecha -extract-field "UCIAcc" -prefix-var uci -desc-var "Intensive Care" -color 200,127,50 -a-circle 0.3 -add-var -add-longlat -population Population -area "Land Area"
    python covid19_2_geojson.py "D:\docs\Recerca\covid-19\España\ActualizacionCovidAgregat.csv" ccaa-spain-covid-19 -href-type local -href-delimiter ";" -mmn C:\inetpub\wwwroot\covid19 -geojson "D:\datacube\covid-19\centroides17CCAA.geojson" -geoid cod_ine -date Fecha -extract-field "FallecidosAcc" -prefix-var dead -desc-var Deaths -color 50,50,50 -a-circle 0.3 -add-var -add-longlat -population Population -area "Land Area"
    python covid19_2_geojson.py "p['cfr{time?f=ISO&day=-15}']-p['dead{time?f=ISO}']" -href-type formula ccaa-spain-covid-19 -mmn C:\inetpub\wwwroot\covid19 -add-var -prefix-var ree -desc-var "Recovered estimated" -color 0,128,0 -population Population -area "Land Area"
    python covid19_2_geojson.py "p['cfr{time?f=ISO}']-p['cfr{time?f=ISO&day=-15}']" -href-type formula ccaa-spain-covid-19 -mmn C:\inetpub\wwwroot\covid19 -add-var -prefix-var ace -desc-var "Active estimated" -color 215,54,0 -population Population -area "Land Area"
    python covid19_2_geojson.py "D:\docs\Recerca\covid-19\España\ActualizacionCovidAgregat.csv" ccaa-spain-covid-19 -href-type local -href-delimiter ";" -mmn C:\inetpub\wwwroot\covid19 -geojson "D:\datacube\covid-19\centroides17CCAA.geojson" -geoid cod_ine -date Fecha -extract-field "PCRDia" -prefix-var pcr -desc-var "Daily PCRs" -is-not-acc -color 50,50,50 -a-circle 0.3 -add-var -add-longlat -population Population -area "Land Area"
    python covid19_2_geojson.py "D:\docs\Recerca\covid-19\España\ActualizacionCovidAgregat.csv" ccaa-spain-covid-19 -href-type local -href-delimiter ";" -mmn C:\inetpub\wwwroot\covid19 -geojson "D:\datacube\covid-19\centroides17CCAA.geojson" -geoid cod_ine -date Fecha -extract-field "Ingresados" -prefix-var chsp -desc-var "Currently Hospitalized" -is-not-acc -color 255,230,0 -a-circle 0.3 -add-var -add-longlat -population Population -area "Land Area"
    python covid19_2_geojson.py "D:\docs\Recerca\covid-19\España\ActualizacionCovidAgregat.csv" ccaa-spain-covid-19 -href-type local -href-delimiter ";" -mmn C:\inetpub\wwwroot\covid19 -geojson "D:\datacube\covid-19\centroides17CCAA.geojson" -geoid cod_ine -date Fecha -extract-field "UCI" -prefix-var cuci -desc-var "Currently in Intensive Care" -is-not-acc -color 200,127,50 -a-circle 0.3 -add-var -add-longlat -population Population -area "Land Area"
    python covid19_2_geojson.py "D:\docs\Recerca\covid-19\España\ActualizacionCovidAgregat.csv" ccaa-spain-covid-19 -href-type local -href-delimiter ";" -mmn C:\inetpub\wwwroot\covid19 -geojson "D:\datacube\covid-19\centroides17CCAA.geojson" -geoid cod_ine -date Fecha -extract-field "PorcenCamas" -prefix-var beds -desc-var "Current Occupied Beds Ratio" -is-not-acc -color 255,180,0 -a-circle 0.3 -add-var -add-longlat -population Population -area "Land Area"
    python covid19_2_geojson.py "D:\docs\Recerca\covid-19\España\ActualizacionCovidAgregat.csv" ccaa-spain-covid-19 -href-type local -href-delimiter ";" -mmn C:\inetpub\wwwroot\covid19 -geojson "D:\datacube\covid-19\centroides17CCAA.geojson" -geoid cod_ine -date Fecha -extract-field "Ingressos24h" -prefix-var adm -desc-var "Daily Admitted" -is-not-acc -color "128,0,0" -a-circle 0.3 -add-var -add-longlat -population Population -area "Land Area"
    python covid19_2_geojson.py "D:\docs\Recerca\covid-19\España\ActualizacionCovidAgregat.csv" ccaa-spain-covid-19 -href-type local -href-delimiter ";" -mmn C:\inetpub\wwwroot\covid19 -geojson "D:\datacube\covid-19\centroides17CCAA.geojson" -geoid cod_ine -date Fecha -extract-field "Altas24h" -prefix-var dis -desc-var "Daily Discharged" -is-not-acc -color 0,128,0 -a-circle 0.3 -add-var -add-longlat -population Population -area "Land Area" -export-geojson D:\datacube\covid-19\github-covid19\datasets\covid19-ccaa-spain.geojson
    python covid19_2_geojson.py "p['adm{time?f=ISO}']-p['dis{time?f=ISO}']" -href-type formula ccaa-spain-covid-19 -mmn C:\inetpub\wwwroot\covid19 -add-var -is-not-acc -prefix-var hfl -desc-var "Daily Hospitalization Flow" -color 80,80,80 -population Population -area "Land Area"
    python sort_config_json.py ccaa-spain-covid-19 -mmn C:\inetpub\wwwroot\covid19 -section atributs -i-item 0 -i-item 1 -i-item 2 -i-item 3 -i-item 4 -i-item 36 -i-item 37 -i-item 35 -i-item 6 -i-item 7 -i-item 5 -i-item 24 -i-item 25 -i-item 23 -i-item 30 -i-item 31 -i-item 29 -i-item 12 -i-item 13 -i-item 11 -i-item 18 -i-item 19 -i-item 17 -i-item 20 -i-item 38 -i-item 8 -i-item 26 -i-item 32 -i-item 14 -i-item 21 -i-item 39 -i-item 9 -i-item 27 -i-item 33 -i-item 15 -i-item 22 -i-item 40 -i-item 10 -i-item 28 -i-item 34 -i-item 16 -i-item 51 -i-item 61 -i-item 62 -i-item 60 -i-item 55 -i-item 56 -i-item 54 -i-item 58 -i-item 59 -i-item 57 -i-item 46 -i-item 47 -i-item 45 -i-item 49 -i-item 50 -i-item 48 -i-item 43 -i-item 44 -i-item 42 -i-item 41 

    python covid19_2_geojson.py "https://analisi.transparenciacatalunya.cat/api/views/xuwf-dxjd/rows.csv?accessType=DOWNLOAD&sorting=true" rs-cat-covid-19 -href-enc utf8 -mmn C:\inetpub\wwwroot\covid19 -geojson "D:\datacube\covid-19\centroidesRS_CAT.geojson" -geoid RegioSanitariaCodi -add-longlat -add-field Population -add-field "Land Area" -accumulate "NumCasos" -fdate dd/mm/yyyy -date TipusCasData -cond-field "TipusCasDescripcio" -cond-value "Positiu PCR" -cond-field "TipusCasDescripcio" -cond-value "Positiu per Test Ràpid" -cond-field "TipusCasDescripcio" -cond-value "Positiu per ELISA" -remove-field "SexeCodi" -remove-field "SexeDescripcio" -remove-field ABSCodi -remove-field ABSDescripcio -remove-field SectorSanitariCodi -remove-field SectorSanitariDescripcio -a-circle 0.3 -population Population -area "Land Area" -export-geojson D:\datacube\covid-19\github-covid19\datasets\covid19-rs-catalonia.geojson
    python covid19_2_geojson.py "p['cfr{time?f=ISO}']-p['cfr{time?f=ISO&day=-15}']" -href-type formula rs-cat-covid-19 -mmn C:\inetpub\wwwroot\covid19 -add-var -prefix-var ace -desc-var "Active estimated" -color 215,54,0 -population Population -area "Land Area"
    python covid19_2_geojson.py "https://analisi.transparenciacatalunya.cat/api/views/xuwf-dxjd/rows.csv?accessType=DOWNLOAD&sorting=true" ss-cat-covid-19 -href-enc utf8 -mmn C:\inetpub\wwwroot\covid19 -geojson "D:\datacube\covid-19\centroidesSS_CAT.geojson" -geoid SectorSanitariCodi -add-longlat -add-field Population -add-field "Land Area" -accumulate "NumCasos" -fdate dd/mm/yyyy -date TipusCasData -cond-field "TipusCasDescripcio" -cond-value "Positiu PCR" -cond-field "TipusCasDescripcio" -cond-value "Positiu per Test Ràpid" -cond-field "TipusCasDescripcio" -cond-value "Positiu per ELISA" -remove-field "SexeCodi" -remove-field "SexeDescripcio" -remove-field ABSCodi -remove-field ABSDescripcio -a-circle 1 -population Population -area "Land Area" -export-geojson D:\datacube\covid-19\github-covid19\datasets\covid19-ss-catalonia.geojson
    python covid19_2_geojson.py "p['cfr{time?f=ISO}']-p['cfr{time?f=ISO&day=-15}']" -href-type formula ss-cat-covid-19 -mmn C:\inetpub\wwwroot\covid19 -add-var -prefix-var ace -desc-var "Active estimated" -color 215,54,0 -population Population -area "Land Area"
    python covid19_2_geojson.py "https://analisi.transparenciacatalunya.cat/api/views/xuwf-dxjd/rows.csv?accessType=DOWNLOAD&sorting=true" abs-cat-covid-19 -href-enc utf8 -mmn C:\inetpub\wwwroot\covid19 -geojson "D:\datacube\covid-19\centroidesABS.geojson" -geoid ABSCodi -add-longlat -add-field Population -add-field "Land Area" -accumulate "NumCasos" -fdate dd/mm/yyyy -date TipusCasData -cond-field "TipusCasDescripcio" -cond-value "Positiu PCR" -cond-field "TipusCasDescripcio" -cond-value "Positiu per Test Ràpid" -cond-field "TipusCasDescripcio" -cond-value "Positiu per ELISA" -remove-field "SexeCodi" -remove-field "SexeDescripcio"  -a-circle 1.5 -population Population -area "Land Area" -export-geojson D:\datacube\covid-19\github-covid19\datasets\covid19-abs-catalonia.geojson
    python covid19_2_geojson.py "p['cfr{time?f=ISO}']-p['cfr{time?f=ISO&day=-15}']" -href-type formula abs-cat-covid-19 -mmn C:\inetpub\wwwroot\covid19 -add-var -prefix-var ace -desc-var "Active estimated" -color 215,54,0 -population Population -area "Land Area"
    python covid19_2_geojson.py "https://analisi.transparenciacatalunya.cat/api/views/jj6z-iyrp/rows.csv?accessType=DOWNLOAD&sorting=true" coma-cat-covid-19 -href-enc utf8 -mmn C:\inetpub\wwwroot\covid19 -geojson "D:\datacube\covid-19\centroidesComaCat.geojson" -geoid ComarcaCodi -add-longlat -add-field Population -add-field "Land Area" -accumulate "NumCasos" -fdate dd/mm/yyyy -date TipusCasData -cond-field "TipusCasDescripcio" -cond-value "Positiu PCR" -cond-field "TipusCasDescripcio" -cond-value "Positiu per Test Ràpid" -remove-field "MunicipiCodi" -remove-field "MunicipiDescripcio" -remove-field "SexeCodi" -remove-field "SexeDescripcio"  -a-circle 1 -population Population -area "Land Area"
    python covid19_2_geojson.py "https://analisi.transparenciacatalunya.cat/api/views/uqk7-bf9s/rows.csv?accessType=DOWNLOAD&sorting=true" coma-cat-covid-19 -href-enc utf8 -mmn C:\inetpub\wwwroot\covid19 -geojson "D:\datacube\covid-19\centroidesComaCat.geojson" -geoid "Codi Comarca" -geoid-type int -geojsonid ComarcaCodi -add-longlat -add-var -prefix-var dead -desc-var Deaths -accumulate "Nombre defuncions" -fdate dd/mm/yyyy -date "Data defunció" -remove-field "Codi Sexe" -remove-field "Sexe"  -a-circle 1 -color 50,50,50 -population Population -area "Land Area" -export-geojson D:\datacube\covid-19\github-covid19\datasets\covid19-comarca-catalonia.geojson
    fart c:\inetpub\wwwroot\covid19\config.json "\"descripcio\": \"RegioSanitariaCodi\"" "\"descripcio\": \"Codi de Regi\xC3\xB3 Sanit\xC3\xA0ria\"" --c-style
    fart c:\inetpub\wwwroot\covid19\config.json "\"descripcio\": \"SectorSanitariCodi\"" "\"descripcio\": \"Codi de Sector Sanitari\"" --c-style
    fart c:\inetpub\wwwroot\covid19\config.json "\"descripcio\": \"SectorSanitariDescripcio\"" "\"descripcio\": \"Sector Sanitari\"" --c-style
    fart c:\inetpub\wwwroot\covid19\config.json "\"descripcio\": \"RegioSanitariaDescripcio\"" "\"descripcio\": \"Regi\xC3\xB3 Sanit\xC3\xA0ria\"" --c-style
    fart c:\inetpub\wwwroot\covid19\config.json "\"descripcio\": \"ABSCodi\"" "\"descripcio\": \"Codi d\'ABS\"" --c-style
    fart c:\inetpub\wwwroot\covid19\config.json "\"descripcio\": \"ABSDescripcio\"" "\"descripcio\": \"ABS\""
    python sort_config_json.py rs-cat-covid-19 -mmn C:\inetpub\wwwroot\covid19 -section atributs -i-item 0 -i-item 1 -i-item 2 -i-item 3 -i-item 4 -i-item 12 -i-item 13 -i-item 11 -i-item 6 -i-item 7 -i-item 5 -i-item 14 -i-item 8 -i-item 15 -i-item 9 -i-item 16 -i-item 10 -i-item 17
    python sort_config_json.py ss-cat-covid-19 -mmn C:\inetpub\wwwroot\covid19 -section atributs -i-item 0 -i-item 1 -i-item 2 -i-item 3 -i-item 4 -i-item 5 -i-item 6 -i-item 14 -i-item 15 -i-item 13 -i-item 8 -i-item 9 -i-item 7 -i-item 16 -i-item 10 -i-item 17 -i-item 11 -i-item 18 -i-item 12 -i-item 19
    python sort_config_json.py abs-cat-covid-19 -mmn C:\inetpub\wwwroot\covid19 -section atributs -i-item 0 -i-item 1 -i-item 2 -i-item 3 -i-item 4 -i-item 5 -i-item 6 -i-item 7 -i-item 8 -i-item 17 -i-item 16 -i-item 15 -i-item 10 -i-item 11 -i-item 9 -i-item 18 -i-item 12 -i-item 19 -i-item 13 -i-item 20 -i-item 14 -i-item 21


    copy C:\inetpub\wwwroot\covid19\config.json \\158.109.46.20\c$\inetpub\wwwroot\covid19\.
  
    Velles que no serveixen

    //El datadista va deixar d'actualitzar les dades el dia 21-05-2020
    python covid19_2_geojson.py https://raw.githubusercontent.com/datadista/datasets/master/COVID%2019/ccaa_covid19_casos.csv spain-covid-19 -href-enc utf8 -mmn C:\inetpub\wwwroot\covid19 -geojson D:\datacube\covid-19\centroides17CCAA.geojson -add-longlat -geoid cod_ine -add-field Population -add-field "Land Area" -population Population -area "Land Area"
    python covid19_2_geojson.py https://raw.githubusercontent.com/datadista/datasets/master/COVID%2019/ccaa_covid19_fallecidos.csv spain-covid-19 -href-enc utf8 -mmn C:\inetpub\wwwroot\covid19 -geojson D:\datacube\covid-19\centroides17CCAA.geojson -add-longlat -geoid cod_ine -add-var -prefix-var dead -desc-var Deaths -color 50,50,50 -population Population -area "Land Area"
    python covid19_2_geojson.py https://raw.githubusercontent.com/datadista/datasets/master/COVID%2019/ccaa_covid19_altas.csv spain-covid-19 -href-enc utf8 -mmn C:\inetpub\wwwroot\covid19 -geojson D:\datacube\covid-19\centroides17CCAA.geojson -add-longlat -geoid cod_ine -add-var -prefix-var rcv -desc-var "Recovered recorded" -color 0,128,0 -population Population -area "Land Area"
    python covid19_2_geojson.py "p['cfr{time?f=ISO&day=-15}']-p['dead{time?f=ISO}']" -href-type formula spain-covid-19 -mmn C:\inetpub\wwwroot\covid19 -add-var -prefix-var ree -desc-var "Recovered estimated" -color 0,128,0 -population Population -area "Land Area"
    python covid19_2_geojson.py https://raw.githubusercontent.com/datadista/datasets/master/COVID%2019/ccaa_covid19_hospitalizados.csv spain-covid-19 -href-enc utf8 -mmn C:\inetpub\wwwroot\covid19 -geojson D:\datacube\covid-19\centroides17CCAA.geojson -add-longlat -geoid cod_ine -add-var -prefix-var hsp -desc-var Hospitalized -color 255,230,0 -population Population -area "Land Area"
    python covid19_2_geojson.py https://raw.githubusercontent.com/datadista/datasets/master/COVID%2019/ccaa_covid19_uci.csv spain-covid-19 -href-enc utf8 -mmn C:\inetpub\wwwroot\covid19 -geojson D:\datacube\covid-19\centroides17CCAA.geojson -add-longlat -geoid cod_ine -add-var -prefix-var uci -desc-var "Intensive care" -color 200,127,50 -population Population -area "Land Area"
    python covid19_2_geojson.py "p['cfr{time?f=ISO}']-p['dead{time?f=ISO}']-p['rcv{time?f=ISO}']" -href-type formula spain-covid-19 -mmn C:\inetpub\wwwroot\covid19 -add-var -prefix-var acr -desc-var Active -color 215,54,0 -population Population -area "Land Area"
    python covid19_2_geojson.py "p['cfr{time?f=ISO}']-p['cfr{time?f=ISO&day=-15}']" -href-type formula spain-covid-19 -mmn C:\inetpub\wwwroot\covid19 -add-var -prefix-var ace -desc-var "Active estimated" -color 215,54,0 -population Population -area "Land Area"
    fart c:\inetpub\wwwroot\covid19\config.json "Catalu\u00f1a" "Catalunya"
    fart c:\inetpub\wwwroot\covid19\config.json "Baleares" "Illes Balears"
    fart c:\inetpub\wwwroot\covid19\config.json "Pa\u00eds Vasco" "Euskadi"
    python sort_config_json.py spain-covid-19 -mmn C:\inetpub\wwwroot\covid19 -section atributs -i-item 0 -i-item 1 -i-item 2 -i-item 3 -i-item 4 -i-item 48 -i-item 49 -i-item 47 -i-item 42 -i-item 43 -i-item 41 -i-item 6 -i-item 7 -i-item 5 -i-item 12 -i-item 13 -i-item 11 -i-item 24 -i-item 25 -i-item 23 -i-item 18 -i-item 19 -i-item 17 -i-item 30 -i-item 31 -i-item 29 -i-item 36 -i-item 37 -i-item 35 -i-item 50 -i-item 44 -i-item 8 -i-item 14 -i-item 26 -i-item 20 -i-item 32 -i-item 38 -i-item 51 -i-item 45 -i-item 9 -i-item 15 -i-item 27 -i-item 21 -i-item 33 -i-item 39 -i-item 52 -i-item 46 -i-item 10 -i-item 16 -i-item 28 -i-item 22 -i-item 34 -i-item 40 -i-item 53 


    fart c:\inetpub\wwwroot\covid19\config.json "ABSDescripci\u00f3" "ABSDescripcio"

    python covid19_2_geojson.py "https://analisi.transparenciacatalunya.cat/api/views/xuwf-dxjd/rows.csv?accessType=DOWNLOAD&sorting=true" rs-cat-covid-19 -href-enc utf8 -mmn C:\inetpub\wwwroot\covid19 -geojson "D:\datacube\covid-19\centroidesRS_CAT.geojson" -add-longlat -geoid RegioSanitariaCodi -accumulate "NumCasos / NumberCases" -fdate dd/mm/yyyy -date TipusCasData -cond-field "TipusCasDescripcio / TipoCasoDescripcion / CaseTypeDescription" -cond-value Positiu -remove-field "SexeCodi / SexoCodigo / GenderCode" -remove-field "SexeDescripcio / SexoDescripcion / GenderDescription" -remove-field ABSCodi -remove-field ABSDescripcio -remove-field SectorSanitariCodi -remove-field SectorSanitariDescripcio -a-circle 0.3
    python covid19_2_geojson.py "https://analisi.transparenciacatalunya.cat/api/views/xuwf-dxjd/rows.csv?accessType=DOWNLOAD&sorting=true" ss-cat-covid-19 -href-enc utf8 -mmn C:\inetpub\wwwroot\covid19 -geojson "D:\datacube\covid-19\centroidesSS_CAT.geojson" -add-longlat -geoid SectorSanitariCodi -accumulate "NumCasos / NumberCases" -fdate dd/mm/yyyy -date TipusCasData -cond-field "TipusCasDescripcio / TipoCasoDescripcion / CaseTypeDescription" -cond-value Positiu -remove-field "SexeCodi / SexoCodigo / GenderCode" -remove-field "SexeDescripcio / SexoDescripcion / GenderDescription" -remove-field ABSCodi -remove-field ABSDescripcio -a-circle 1
    python covid19_2_geojson.py "https://analisi.transparenciacatalunya.cat/api/views/xuwf-dxjd/rows.csv?accessType=DOWNLOAD&sorting=true" abs-cat-covid-19 -href-enc utf8 -mmn C:\inetpub\wwwroot\covid19 -geojson "D:\datacube\covid-19\centroidesABS.geojson" -add-longlat -geoid ABSCodi -accumulate "NumCasos / NumberCases" -fdate dd/mm/yyyy -date TipusCasData -cond-field "TipusCasDescripcio / TipoCasoDescripcion / CaseTypeDescription" -cond-value Positiu -remove-field "SexeCodi / SexoCodigo / GenderCode" -remove-field "SexeDescripcio / SexoDescripcion / GenderDescription"  -a-circle 1.5

    python covid19_2_geojson.py "https://analisi.transparenciacatalunya.cat/api/views/xuwf-dxjd/rows.csv?accessType=DOWNLOAD&sorting=true" rs-cat-covid-19 -href-enc utf8 -mmn C:\inetpub\wwwroot\covid19 -geojson "D:\datacube\covid-19\centroidesRS_CAT.geojson" -add-longlat -geoid RegioSanitariaCodi -fdate dd/mm/yyyy -date TipusCasData -cond-field TipusCasDescripcio -cond-value Positiu -remove-field SexeCodi -remove-field SexeDescripcio -remove-field ABSCodi -remove-field ABSDescripcio -remove-field SectorSanitariCodi -remove-field SectorSanitariDescripcio -a-circle 0.3
    python covid19_2_geojson.py "https://analisi.transparenciacatalunya.cat/api/views/xuwf-dxjd/rows.csv?accessType=DOWNLOAD&sorting=true" ss-cat-covid-19 -href-enc utf8 -mmn C:\inetpub\wwwroot\covid19 -geojson "D:\datacube\covid-19\centroidesSS_CAT.geojson" -add-longlat -geoid SectorSanitariCodi -fdate dd/mm/yyyy -date TipusCasData -cond-field TipusCasDescripcio -cond-value Positiu -remove-field SexeCodi -remove-field SexeDescripcio -remove-field ABSCodi -remove-field ABSDescripcio -a-circle 1
    python covid19_2_geojson.py "https://analisi.transparenciacatalunya.cat/api/views/xuwf-dxjd/rows.csv?accessType=DOWNLOAD&sorting=true" abs-cat-covid-19 -href-enc utf8 -mmn C:\inetpub\wwwroot\covid19 -geojson "D:\datacube\covid-19\centroidesABS.geojson" -add-longlat -geoid ABSCodi -fdate dd/mm/yyyy -date TipusCasData -cond-field TipusCasDescripcio -cond-value Positiu -remove-field SexeCodi -remove-field SexeDescripcio -a-circle 1.5

    python covid19_2_geojson.py "https://analisi.transparenciacatalunya.cat/api/views/xuwf-dxjd/rows.csv?accessType=DOWNLOAD&sorting=true" rs-cat-covid-19 -href-enc utf8 -mmn C:\inetpub\wwwroot\covid19 -geojson "D:\datacube\covid-19\centroidesRS_CAT.geojson" -add-longlat -geoid RegioSanitariaCodi -fdate dd/mm/yyyy -date Data -cond-field ResultatCovidCodi -cond-value 1 -remove-field SexeCodi -remove-field SexeDescripcio -remove-field ResultatCovidDescripcio -remove-field ABSCodi -remove-field ABSDescripcio -remove-field SectorSanitariCodi -remove-field SectorSanitariDescripcio
    python covid19_2_geojson.py "https://analisi.transparenciacatalunya.cat/api/views/xuwf-dxjd/rows.csv?accessType=DOWNLOAD&sorting=true" ss-cat-covid-19 -href-enc utf8 -mmn C:\inetpub\wwwroot\covid19 -geojson "D:\datacube\covid-19\centroidesSS_CAT.geojson" -add-longlat -geoid SectorSanitariCodi -fdate dd/mm/yyyy -date Data -cond-field ResultatCovidCodi -cond-value 1 -remove-field SexeCodi -remove-field SexeDescripcio -remove-field ResultatCovidDescripcio -remove-field ABSCodi -remove-field ABSDescripcio -a-circle 2
    python covid19_2_geojson.py "https://analisi.transparenciacatalunya.cat/api/views/xuwf-dxjd/rows.csv?accessType=DOWNLOAD&sorting=true" abs-cat-covid-19 -href-enc utf8 -mmn C:\inetpub\wwwroot\covid19 -geojson "D:\datacube\covid-19\centroidesABS.geojson" -add-longlat -geoid ABSCodi -fdate dd/mm/yyyy -date Data -cond-field ResultatCovidCodi -cond-value 1 -remove-field SexeCodi -remove-field SexeDescripcio -remove-field ResultatCovidDescripcio -a-circle 10
    
    python sort_config_json.py world-covid-19 -mmn C:\inetpub\wwwroot\covid19 -section atributs -i-item 0 -i-item 1 -i-item 2 -i-item 3 -i-item 4 -i-item 17 -i-item 5 -i-item 9 -i-item 13 -i-item 18 -i-item 6 -i-item 10 -i-item 14 -i-item 19 -i-item 20 -i-item 7 -i-item 8 -i-item 11 -i-item 12 -i-item 15 -i-item 16 -i-item 21
    python sort_config_json.py spain-covid-19 -mmn C:\inetpub\wwwroot\covid19 -section atributs -i-item 0 -i-item 1 -i-item 2 -i-item 3 -i-item 24 -i-item 4 -i-item 8 -i-item 12 -i-item 25 -i-item 5 -i-item 9 -i-item 13 -i-item 26 -i-item 27 -i-item 6 -i-item 7 -i-item 10 -i-item 11 -i-item 14 -i-item 15 -i-item 16 -i-item 17 -i-item 18 -i-item 19 -i-item 20 -i-item 21 -i-item 22 -i-item 23 -i-item 28
    
    debug python covid19_2_geojson.py "D:\docs\Recerca\covid-19\AreesBasiquesSalut\Registre_de_test_de_COVID-19_realitzats_a_Catalunya._Segregaci__per_sexe_i__rea_b_sica_de_salut__ABS_.csv" -href-type local abs-cat-covid-19 -href-enc utf8 -mmn C:\inetpub\wwwroot\covid19 -geojson "D:\datacube\covid-19\centroidesABS.geojson" -add-longlat -geoid ABSCodi -fdate dd/mm/yyyy -date Data -cond-field ResultatCovidCodi -cond-value 1 -remove-field SexeCodi -remove-field SexeDescripcio -remove-field ResultatCovidDescripcio -a-circle 10
    """
    #logging.basicConfig(level=logging.WARNING) no puc posar això per culpa d'un error en le tractament del NetCDF i el v4 i el v5
    logging.basicConfig(level=logging.ERROR)
    log = logging.getLogger('cd-covid19_2_geojson')
    try: 
        if mmn is not None:
            pathmmn = Path(mmn).joinpath("config.json")
            if pathmmn.exists()==False:
                raise RuntimeError("Map browser configuration file does not exist {}".format(str(pathmmn)))

        if href_type=="href":
            #download the first csv
            tf = tempfile.NamedTemporaryFile(delete=False)
            tname=tf.name  # retrieve the name of the temp file just created
            tf.close()
            #https://stackoverflow.com/questions/19602931/basic-http-file-downloading-and-saving-to-disk-in-python
        
            urllib.request.urlretrieve(href, tname)
        elif href_type=="formula":
            tname=href.replace("`", "'")
        else:
            tname=href
        #transform the csv into a GeoJSON
        
        if href_type=="formula":
            objectes=None
        else:
            if href_enc is None:
                csvfile=open(tname, newline='')
            elif href_enc=="utf8":
                csvfile=open(tname, newline='', encoding='utf-8-sig')
            else:
                csvfile=open(tname, newline='', encoding=href_enc)
                
            csvreader = csv.DictReader(csvfile, delimiter=href_delimiter)
            if (date is None):
                csvreader = tranformDatesCsv(csvreader, prefix_var, fdate)
            elif extract_field is not None:
                csvreader = ExtractDatesCsv(csvreader, geoid[0], date, fdate, extract_field)
                csvreader = tranformDatesCsv(csvreader, prefix_var, "yyyy-mm-dd")
            else:
                if len(geoid)!=1:
                    raise ValueError("Geoid is required. More than one geoid not suported")
                csvreader = AccumulateDatesCsv(csvreader, geoid[0], date, fdate, accumulate, cond_field, cond_value, remove_field)
                csvreader = tranformDatesCsv(csvreader, prefix_var, "yyyy-mm-dd")
                
            if geojson is None:
                objectes=csv2geojson(csvreader, long, lat)
            else:
                pathgeojson = Path(geojson)
                if pathgeojson.exists()==False:
                    raise RuntimeError("GeoJSON file does not exist {}".format(str(pathgeojson)))
                geojsonfile=open(pathgeojson, "r", encoding='utf-8-sig')
                geojsondata = json.load(geojsonfile)
                geojsonfile.close()
                if len(geojsonid)>0 and len(geoid)!=len(geojsonid):
                    raise ValueError("geoid and geojsonid has to have the same number of values")
                # if len(geoid)==1:
                #     objectes=csv_geoid2geojson(csvreader, geojson, geoid, add_longlat, add_field)
                # else:
                #     objectes=csv_multigeoid2geojson(csvreader, geojson, geoid, add_longlat, add_field)
                objectes=csv_multigeoid2geojson(csvreader, long, lat, geoid, geoid_type, geojsondata, geojsonid if len(geojsonid) else geoid, add_longlat, add_field)
            
            csvfile.close()
            
            if href_type=="href":          
                os.remove(tname)

        #mmnfile=open("d:\\covid19.geojson", "w", encoding='utf-8-sig')
        #json.dump(objectes, mmnfile, indent="\t")
        #mmnfile.close()
        atrib=[]
        estil=[]
        dies=[]
        if href_type!="formula":
            for varname, da in objectes["features"][0]["properties"].items():            
                if len(varname)==len(prefix_var) + 10 and varname.count('-')==2:  #https://www.geeksforgeeks.org/python-count-occurrences-of-a-character-in-string/
                    d=varname[len(prefix_var):].split('-')
                    dies.append({"year": int(d[0]), "month": int(d[1]), "day": int(d[2])})
                elif add_var==False:
                    atrib.append({"nom": varname, "descripcio": varname, "mostrar": "si"})
                    if area is not None and varname==area:
                        atrib[-1]["unitats"]="m<sup>2</sup>"
            
            if add_var==False:
                if area is not None:
                    atrib.append({"nom": "LandAreaKm",  "descripcio": area, "FormulaConsulta": "(p['"+area+"']/1000000)",					"unitats": "km<sup>2</sup>", 					"NDecimals": 3, "mostrar": "si"})
        
            nameAtrib=prefix_var+"{time?f=ISO}"
            atrib.append({"nom": nameAtrib, 
                          "descripcio": desc_var, 
                          "mostrar": "si",
                          "serieTemporal": {"color": rgb_string_to_hex(color)}
                    })
            #lastDay="p['"+prefix_var+"{time?f=ISO}']"
            #beforeLastDay="p['"+prefix_var+"{time?f=ISO&day=-1}']"
            #beforeBeforeLastDay="p['"+prefix_var+"{time?f=ISO&day=-2}']"
            t6="p['"+prefix_var+"{time?f=ISO&day=+2}']"
            t5="p['"+prefix_var+"{time?f=ISO&day=+1}']"
            t4="p['"+prefix_var+"{time?f=ISO}']"
            t3="p['"+prefix_var+"{time?f=ISO&day=-1}']"
            t2="p['"+prefix_var+"{time?f=ISO&day=-2}']"
            t1="p['"+prefix_var+"{time?f=ISO&day=-3}']"
            t0="p['"+prefix_var+"{time?f=ISO&day=-4}']"
            tc="p['"+prefix_var+"{time?f=ISO&day=-5}']"
            tr="p['"+prefix_var+"{time?f=ISO&day=-10}']"
        else:
            nameAtrib=prefix_var
            #lastDay="("+tname+")"
            #beforeLastDay="("+tname.replace("{time?f=ISO}", "{time?f=ISO&day=-1}")+")"
            #beforeBeforeLastDay="("+tname.replace("{time?f=ISO}", "{time?f=ISO&day=-2}")+")"
            t6="("+delayTimeTemplate(tname,2)+")"
            t5="("+delayTimeTemplate(tname,1)+")"
            t4="("+tname+")"
            t3="("+delayTimeTemplate(tname,-1)+")"
            t2="("+delayTimeTemplate(tname,-2)+")"
            t1="("+delayTimeTemplate(tname,-3)+")"
            t0="("+delayTimeTemplate(tname,-4)+")"
            tc="("+delayTimeTemplate(tname,-5)+")"
            tr="("+delayTimeTemplate(tname,-10)+")"
            atrib.append({"nom": nameAtrib, 
                          "descripcio": desc_var, 
                          "FormulaConsulta": t4,
                          "mostrar": "si",
                          "serieTemporal": {"color": rgb_string_to_hex(color)}
                    })
        if population is not None:
            atrib.append({
					"nom": nameAtrib+"Pop",
					"descripcio": desc_var+" per 100000 hab.",
					"FormulaConsulta": "("+t4+"/p['"+population+"']*100000)",
					"NDecimals": 2,
					"mostrar": "si"
				})
        if area is not None:
            atrib.append({
					"nom": nameAtrib+"Area",
					"descripcio": desc_var+" per area",
					"FormulaConsulta": "("+t4+"/p['"+area+"']*1000000)",
					"unitats": "hab./km<sup>2</sup>",
					"NDecimals": 3,
					"mostrar": "si"
				})

        estil.extend([{"nom": None, "desc": ("Count of " if is_acc else "")+desc_var, 
                        "DescItems": desc_var,
              		    "TipusObj": "P",
                		"ItemLleg":	[
              				{"color": rgb_string_to_hex(color), "DescColor": desc_var}
              			],
              			"ncol": 1,
              			"simbols": [{							
          					"NomCampFEscala": nameAtrib,
          					"simbol":
          					[{
          							"icona":{
          								"type": "circle",
          								"a": a_circle
          							}
      						}]
              			}],
              			"vora":{
              				"paleta": {"colors": [rgb_string_to_hex(color)]}
              			},
              			"interior":{
              				"paleta": {"colors": ["rgba("+color+",0.4)"]}
              			},			
              			"fonts": {
              				"NomCampText": nameAtrib,
              				"aspecte": [{
              					"font": {
                                      "font": "12px Verdana", "color": "#B50000", "align": "center", "i": 0, "j": -5
                                }
              				}]
              			}
              		},
                     {"nom": None, "desc": ("Count of " if is_acc else "")+desc_var+"/100000 hab", 
                        "DescItems": desc_var,
              		    "TipusObj": "P",
                		"ItemLleg":	[
              				{"color": rgb_string_to_hex(color), "DescColor": desc_var}
              			],
              			"ncol": 1,
              			"simbols": [{							
          					"NomCampFEscala": nameAtrib+"Pop",
          					"simbol":
          					[{
          							"icona":{
          								"type": "circle",
          								"a": a_circle*(200 if a_circle<0.1 else 20 if a_circle<1 else 0.5)
          							}
      						}]
              			}],
              			"vora":{
              				"paleta": {"colors": [rgb_string_to_hex(color)]}
              			},
              			"interior":{
              				"paleta": {"colors": ["rgba("+color+",0.4)"]}
              			},			
              			"fonts": {
              				"NomCampText": nameAtrib+"Pop",
              				"aspecte": [{
              					"font": {
                                      "font": "12px Verdana", "color": "#B50000", "align": "center", "i": 0, "j": -5
                                }
              				}]
              			}
              		}
                ])
        if is_acc:
            atrib.extend([
#             {"nom": prefix_var+"NewCases",
# 				"descripcio": "New "+desc_var+" in a day",
# 				"FormulaConsulta": "("+lastDay+"-"+beforeLastDay+")",
#                 "NDecimals": 0,
# 				"mostrar": "si",
#                 "serieTemporal": {"color": rgb_string_to_hex(color)}
#             },{"nom": prefix_var+"PercentCumulCases",
# 				"descripcio": "Increase in cumulated "+desc_var,
# 				"FormulaConsulta": "(("+lastDay+"-"+beforeLastDay+")/"+beforeLastDay+"*100)",
# 				"NDecimals": 2,
#                 "unitats": "%",
# 				"mostrar": "si",
#                 "serieTemporal": {"color": rgb_string_to_hex(color)}
# 			},{"nom": prefix_var+"Acceleration",
# 				"descripcio": "Last day Acceleration in "+desc_var,
#                 "unitats": "cases/day²",
# 				"FormulaConsulta": "("+lastDay+"-2*"+beforeLastDay+"+"+beforeBeforeLastDay+")",
# 				"NDecimals": 2,
# 				"mostrar": "si",
#                 "serieTemporal": {"color": rgb_string_to_hex(color)}
# 			},{"nom": prefix_var+"PercentAccel",
# 				"descripcio": "Last day Percentual Acceleration in "+desc_var,
# 				"FormulaConsulta": "(("+lastDay+"-2*"+beforeLastDay+"+"+beforeBeforeLastDay+")/("+beforeLastDay+"-"+beforeBeforeLastDay+")*100)",
# 				"NDecimals": 2,
#                 "unitats": "%",
# 				"mostrar": "si",
#                 "serieTemporal": {"color": rgb_string_to_hex(color)}
# 			},
            {"nom": prefix_var+"NewCases5",
				"descripcio": "New "+desc_var+" in a day (av. 5)",
				"FormulaConsulta": "(isNaN("+t6+") ? "+t4+"-"+t3+" : ("+t6+"-"+t1+")/5)",
                "NDecimals": 0,
				"mostrar": "si",
                "serieTemporal": {"color": rgb_string_to_hex(color)}
            },{"nom": prefix_var+"PercentCumulCases5",
				"descripcio": "Increase in cumulated "+desc_var+ " (av. 5)",
				"FormulaConsulta": "(isNaN("+t6+") ? ("+t4+"-"+t3+")/"+t3+"*100 : ("+t6+"-"+t1+")/("+t5+"+"+t4+"+"+t3+"+"+t2+"+"+t1+")*100)",
				"NDecimals": 2,
                "unitats": "%",
				"mostrar": "si",
                "serieTemporal": {"color": rgb_string_to_hex(color)}
			},{"nom": prefix_var+"Acceleration5",
				"descripcio": "Last day Acceleration in "+desc_var+ " (av. 5)",
                "unitats": "cases/day²",
				"FormulaConsulta": "(isNaN("+t6+") ? "+t4+"-2*"+t3+"+"+t2+" : ("+t6+"-"+t5+"+"+t0+"-"+t1+")/5)",
				"NDecimals": 2,
				"mostrar": "si",
                "serieTemporal": {"color": rgb_string_to_hex(color)}
			}
#       ,{"nom": prefix_var+"PercentAccel5",
# 				"descripcio": "Last day Percentual Acceleration in "+desc_var+" (av. 5)",
# 				"FormulaConsulta": "(("+t6+"-"+t5+"+"+t0+"-"+t1+")/("+t5+"-"+t0+")*100)",
# 				"NDecimals": 2,
#                 "unitats": "%",
# 				"mostrar": "si",
#                 "serieTemporal": {"color": rgb_string_to_hex(color)}
# 			}
      
            ])
            estil.extend([                      
                        {"nom": None, "desc": "New "+desc_var+" in a day (av.5)", 
      		                "TipusObj": "P",
                    		"ItemLleg":	[
                  				{"color": rgb_string_to_hex(color), "DescColor": desc_var}
                  			],
                  			"ncol": 1,
                  			"simbols": [{							
              					"NomCampFEscala": prefix_var+"NewCases5",
              					"simbol":
              					[{
              							"icona":{
              								"type": "circle",
              								"a": a_circle*40
              							}
          						}]
                  			}],
                  			"vora":{
                  				"paleta": {"colors": [rgb_string_to_hex(color)]}
                  			},
                  			"interior":{
                  				"paleta": {"colors": ["rgba("+color+",0.4)"]}
                  			},			
                  			"fonts": {
                  				"NomCampText": prefix_var+"NewCases5",
                  				"aspecte": [{
                  					"font": {
                                          "font": "12px Verdana", "color": "#B50000", "align": "center", "i": 0, "j": -5
                                    }
                  				}]
                  			}
                  		}
                    ])
        if prefix_var=="ace" and is_acc:
            atrib.append({
    				"nom": prefix_var+"AccelTerna",
    				"descripcio": "Acceleration Ternary",
    				#"FormulaConsulta": "(("+beforeLastDay+"==0)?0:((("+lastDay+"-"+beforeLastDay+")/"+beforeLastDay+">0.05 && "+lastDay+"-2*"+beforeLastDay+"+"+beforeBeforeLastDay+">0)?7:((("+lastDay+"-"+beforeLastDay+")/"+beforeLastDay+">0.05 && "+lastDay+"-2*"+beforeLastDay+"+"+beforeBeforeLastDay+"<=0)?6:((("+lastDay+"-"+beforeLastDay+")/"+beforeLastDay+">0)?5:((("+lastDay+"-"+beforeLastDay+")/"+beforeLastDay+"==0)?4:((("+lastDay+"-"+beforeLastDay+")/"+beforeLastDay+">-0.05)?3:(("+lastDay+"-2*"+beforeLastDay+"+"+beforeBeforeLastDay+">=0)?2:1)))))))",
                    #"FormulaConsulta": "(("+beforeLastDay+"-"+beforeBeforeLastDay+"==0)?0:((("+lastDay+"-2*"+beforeLastDay+"+"+beforeBeforeLastDay+")/("+beforeLastDay+"-"+beforeBeforeLastDay+")>0.05&&"+lastDay+"-2*"+beforeLastDay+"+"+beforeBeforeLastDay+">0)?7:((("+lastDay+"-2*"+beforeLastDay+"+"+beforeBeforeLastDay+")/("+beforeLastDay+"-"+beforeBeforeLastDay+")>0.05&&"+lastDay+"-2*"+beforeLastDay+"+"+beforeBeforeLastDay+"<=0)?6:((("+lastDay+"-2*"+beforeLastDay+"+"+beforeBeforeLastDay+")/("+beforeLastDay+"-"+beforeBeforeLastDay+")>0)?5:((("+lastDay+"-2*"+beforeLastDay+"+"+beforeBeforeLastDay+")/("+beforeLastDay+"-"+beforeBeforeLastDay+")==0)?4:((("+lastDay+"-2*"+beforeLastDay+"+"+beforeBeforeLastDay+")/("+beforeLastDay+"-"+beforeBeforeLastDay+")>-0.05)?3:(("+lastDay+"-2*"+beforeLastDay+"+"+beforeBeforeLastDay+">=0)?2:1)))))))",
                    "FormulaConsulta": "(isNaN("+t4+")?6:(("+t4+">"+tr+"+("+t4+"+"+tr+")*0.03)?(("+tc+"<("+t4+"+"+tr+")/2-("+t4+"-"+tr+")*0.05)?0:1):(("+t4+"<"+tr+"-("+t4+"+"+tr+")*0.03)?(("+tc+">("+t4+"+"+tr+")/2+("+t4+"-"+tr+")*0.05)?3:4):(("+t4+"<700)?5:2))))",
    				"mostrar": "no"
    			})
            estil.append({"nom": None,
                			"desc":	"Last days Trend",
                			"DescItems": None,
                			"TipusObj": "S",
                			"ItemLleg":	[
                				# {"color": "propies/arrows/up3.png", "DescColor": "Increase>5% and Acceleration>0"},
                    #             {"color": "propies/arrows/up2.png", "DescColor": "Increase>5% and Acceleration<=0"},
                    #             {"color": "propies/arrows/up.png", "DescColor": "Increase between 0 and 5% (0 excluded)"},
                    #             {"color": "propies/arrows/down.png", "DescColor": "Increase between -5 and 0 % (0 excluded)"},
                    #             {"color": "propies/arrows/down2.png", "DescColor": "Increase<-5% and Acceleration>=0"},
                    #             {"color": "propies/arrows/down3.png", "DescColor": "Increase<-5% and Acceleration<0"},
                    #             {"color": "propies/arrows/stable.png", "DescColor": "Increase=0 or without data"}
                				{"color": "propies/arrows/up3.png", "DescColor": "Increase and Acceleration"},
                                {"color": "propies/arrows/up2.png", "DescColor": "Increase and Deceleration"},
                                {"color": "propies/arrows/top.png", "DescColor": "Stable at high"},
                                {"color": "propies/arrows/down2.png", "DescColor": "Decrease and Acceleration"},
                                {"color": "propies/arrows/down3.png", "DescColor": "Decrease and Deceleration"},
                                {"color": "propies/arrows/low.png", "DescColor": "Stable at low"},
                                {"color": "propies/arrows/nodata.png", "DescColor": "No data"}
                			],
                			"ncol": 1,
                			"simbols": [
                				{							
                					"NomCamp": prefix_var+"AccelTerna",
                					"simbol":
                					[
                						{
                							"ValorCamp": 0,
                							"icona":
                							{
                								"icona": "propies/arrows/up3.png",
                								"ncol": 36,
                								"nfil": 36,
                								"i": 18,
                								"j": 18
                							}
                						},
                						{
                							"ValorCamp": 1,
                							"icona":
                							{
                								"icona": "propies/arrows/up2.png",
                								"ncol": 27,
                								"nfil": 27,
                								"i": 14,
                								"j": 14
                							}
                						},
                						# {
                						# 	"ValorCamp": 5,
                						# 	"icona":
                						# 	{
                						# 		"icona": "propies/arrows/up.png",
                						# 		"ncol": 23,
                						# 		"nfil": 23,
                						# 		"i": 12,
                						# 		"j": 12
                						# 	}
                						# },
                						{
                							"ValorCamp": 2,
                							"icona":
                							{
                								"icona": "propies/arrows/top.png",
                								"ncol": 23,
                								"nfil": 23,
                								"i": 12,
                								"j": 12
                							}
                						},
                						# {
                						# 	"ValorCamp": 3,
                						# 	"icona":
                						# 	{
                						# 		"icona": "propies/arrows/down.png",
                						# 		"ncol": 23,
                						# 		"nfil": 23,
                						# 		"i": 12,
                						# 		"j": 12
                						# 	}
                						# },                                        
                						{
                							"ValorCamp": 3,
                							"icona":
                							{
                								"icona": "propies/arrows/down2.png",
                								"ncol": 27,
                								"nfil": 27,
                								"i": 14,
                								"j": 14
                							}
                						},
                						{
                							"ValorCamp": 4,
                							"icona":
                							{
                								"icona": "propies/arrows/down3.png",
                								"ncol": 36,
                								"nfil": 36,
                								"i": 18,
                								"j": 18
                							}
                						},
                						{
                							"ValorCamp": 5,
                							"icona":
                							{
                								"icona": "propies/arrows/low.png",
                								"ncol": 19,
                								"nfil": 19,
                								"i": 10,
                								"j": 10
                							}
                						},
                                        {
                							"ValorCamp": 6,
                							"icona":
                							{
                								"icona": "propies/arrows/nodata.png",
                								"ncol": 19,
                								"nfil": 19,
                								"i": 10,
                								"j": 10
                							}
                						}
                					]
                				}
                            ]}) 
        #mmnfile=open("d:\\covid19_atrib.geojson", "w", encoding='utf-8-sig')
        #json.dump(atrib, mmnfile, indent="\t")
        #mmnfile.close()
        
        if mmn is not None:
            #include it into the config.json
            mmnfile=open(pathmmn, "r", encoding='utf-8-sig')
            ParamCtrl=updateConfigJSON(mmnfile, layer, prefix_var, objectes, atrib, estil, dies, add_var, geojsonid if len(geojsonid) else geoid, geoid, geoid_type)
            mmnfile.close()
            mmnfile=open(pathmmn, "w", encoding='utf-8-sig')
            json.dump(ParamCtrl, mmnfile, indent="\t")
            mmnfile.close()
        if export_geojson is not None:
            #Export only the objects as a geojson file
            capa=next((item for item in ParamCtrl["capa"] if item["nom"] == layer), None)
            mmnfile=open(export_geojson, "w", encoding='utf-8-sig')
            json.dump(capa["objectes"], mmnfile, indent="\t")
            mmnfile.close()            
        
    except:
        log.exception('Exception from main():')
        sys.exit(1) 
        return 1

if __name__ == '__main__':
    main()
