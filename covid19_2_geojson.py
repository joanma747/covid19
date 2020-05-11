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
        for field in cond_field:
            if row[field]!=cond_value[i]:
                different=True;
                break
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

def csv_geoid2geojson(csvreader, geojson, geoid):
    data={"type": "FeatureCollection", "features": []}
    for row in csvreader:
        for obj in geojson["features"]:
            if obj["properties"][geoid]==row[geoid]:
                data["features"].append({"type": "Feature", "geometry": { "type": "Point", "coordinates": [obj["geometry"]["coordinates"][0], obj["geometry"]["coordinates"][1]]}, "properties": {}})
                for varname, da in row.items():
                    if isint(da):
                        data["features"][-1]["properties"][varname]=int(da)
                    elif isfloat(da):
                        data["features"][-1]["properties"][varname]=float(da)
                    else:
                        data["features"][-1]["properties"][varname]=da
                break;
    return data    

def updateConfigJSON(mmnfile, layer, add_var, prefix_var, objectes, atrib, estil, dies):
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
                    for varname, da in obj["properties"].items():
                        if len(varname)==len(prefix_var) + 10 and varname.count('-')==2:
                            continue
                        #https://stackoverflow.com/questions/1323410/should-i-use-has-key-or-in-on-python-dicts                      
                        if not varname in capa_obj["properties"] or capa_obj["properties"][varname]!=da:
                            different=True
                            break
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

#https://click.palletsprojects.com/en/7.x/options/
@click.command()
@click.argument('href')
@click.argument('layer')
@click.option('-href-enc', default='ansi', help="Encoding of the remote file")
@click.option('-href-type', default='href', type=click.Choice(['href', 'local', 'formula']), help="Type of href. For debuging purposes it can be 'file' to indicate a local file. A 'formula' can be provided to create atributs and estil based on preexisting property values; use ` instead of '.")
@click.option('-mmn', help="Path of the config.json of the MiraMon Map Browser. If not specified, it will not be updates with the new dates")
@click.option('-add-var/-no-add-var', default=False, help="-no-add-var (default) removes all other variables. -add-var add a variable and reviews the dates")
@click.option('-prefix-var', default="cfr", help="Prefix to add to temporal field")
@click.option('-desc-var', default="Confirmed cases", help="Description of the variable")
@click.option('-color', default="255,0,0", help="Color of the cercles and lines in diagrams")
@click.option('-long', default="Long", help="Name of the longitude field in the CSV")
@click.option('-lat', default="Lat", help="Name of the latitude field in the CSV")
@click.option('-longlat', help="Name of the GeoJSON file that has the long lat values (that are no in the CSV)")
@click.option('-geoid', default="cod_ine", help="Name of the id field in the CSV that connects with the the geojson that has the long lat values (this id name is the same in both the CSV and the GeoJSON)")
@click.option('-fdate', default="yyyy-mm-dd", help="Format of the date fields in the CSV")
@click.option('-date', help="Name of the field containing dates in the CSV. If not specified, we assume that all fields with the fdate format contain dates")
#@click.option('-initial-date', default="2020-02-02", help="Initial date to accumulate. Dates with nodata are added as a repetion of the previous date")
@click.option('-accumulate', default="NumCasos", help="Name of the field with numbers to accumulate CSV")
@click.option('-cond-field', multiple=True, help="Name of the field that should be equal to -cond-value to be considered")
@click.option('-cond-value', multiple=True, help="Value towards the field values should be equal to, to be considered")
@click.option('-remove-field', multiple=True, help="Fields that shuold be removed. Used only if -date is provided")
@click.option('-a-circle', default="0.05", help="Area of the circle that is used as the bases for the circle radious")
              
def main(href, layer, href_enc, href_type, mmn, add_var, prefix_var, desc_var, color, long, lat, longlat, geoid, fdate, date, accumulate, cond_field, cond_value, remove_field, a_circle):
    """
    Import a COVID-19 csv file and edit a config.json to include this data in a vector capa
    The csv need to have a fields with a name that is a date in fdate format. These fields contains
    the values of a single variable in time.
    The format used in https://github.com/CSSEGISandData/COVID-19/tree/master/csse_covid_19_data/csse_covid_19_time_series is directly supported
    
    Params: 
    <href> Base URL to download the csv data.
    <folder> folder of the layer in the MiraMon Map server. The rel5 should existe inside.
    <layer> name of the layer. It should be the same as the name of the folder in the server, the name of the REL5 and the name of the layer in the config.json.       
    
    Example:
    python covid19_2_geojson.py https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv world-covid-19 -mmn C:\inetpub\wwwroot\covid19 -fdate m/d/yy 
    python covid19_2_geojson.py https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv world-covid-19 -mmn C:\inetpub\wwwroot\covid19 -add-var -prefix-var dead -desc-var Deaths -color 50,50,50 -fdate m/d/yy 
    python covid19_2_geojson.py https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_recovered_global.csv world-covid-19 -mmn C:\inetpub\wwwroot\covid19 -add-var -prefix-var rcv -desc-var Recovered -color 0,128,0 -fdate m/d/yy 
    python covid19_2_geojson.py "p['cfr{time?f=ISO}']-p['dead{time?f=ISO}']-p['rcv{time?f=ISO}']" -href-type formula world-covid-19 -mmn C:\inetpub\wwwroot\covid19 -add-var -prefix-var act -desc-var Active -color 215,54,0
    python covid19_2_geojson.py https://raw.githubusercontent.com/datadista/datasets/master/COVID%2019/ccaa_covid19_casos.csv spain-covid-19 -href-enc utf8 -mmn C:\inetpub\wwwroot\covid19 -longlat D:\datacube\covid-19\centroides17CCAA.geojson
    python covid19_2_geojson.py https://raw.githubusercontent.com/datadista/datasets/master/COVID%2019/ccaa_covid19_fallecidos.csv spain-covid-19 -href-enc utf8 -mmn C:\inetpub\wwwroot\covid19 -longlat D:\datacube\covid-19\centroides17CCAA.geojson -add-var -prefix-var dead -desc-var Deaths -color 50,50,50
    python covid19_2_geojson.py https://raw.githubusercontent.com/datadista/datasets/master/COVID%2019/ccaa_covid19_altas.csv spain-covid-19 -href-enc utf8 -mmn C:\inetpub\wwwroot\covid19 -longlat D:\datacube\covid-19\centroides17CCAA.geojson -add-var -prefix-var rcv -desc-var Recovered -color 0,128,0
    python covid19_2_geojson.py https://raw.githubusercontent.com/datadista/datasets/master/COVID%2019/ccaa_covid19_hospitalizados.csv spain-covid-19 -href-enc utf8 -mmn C:\inetpub\wwwroot\covid19 -longlat D:\datacube\covid-19\centroides17CCAA.geojson -add-var -prefix-var hsp -desc-var Hospitalized -color 255,230,0
    python covid19_2_geojson.py https://raw.githubusercontent.com/datadista/datasets/master/COVID%2019/ccaa_covid19_uci.csv spain-covid-19 -href-enc utf8 -mmn C:\inetpub\wwwroot\covid19 -longlat D:\datacube\covid-19\centroides17CCAA.geojson -add-var -prefix-var uci -desc-var "Intensive care" -color 200,127,50
    python covid19_2_geojson.py "p['cfr{time?f=ISO}']-p['dead{time?f=ISO}']-p['rcv{time?f=ISO}']" -href-type formula spain-covid-19 -mmn C:\inetpub\wwwroot\covid19 -add-var -prefix-var act -desc-var Active -color 215,54,0
    python covid19_2_geojson.py "https://analisi.transparenciacatalunya.cat/api/views/xuwf-dxjd/rows.csv?accessType=DOWNLOAD&sorting=true" rs-cat-covid-19 -href-enc utf8 -mmn C:\inetpub\wwwroot\covid19 -longlat "D:\datacube\covid-19\centroidesRS_CAT.geojson" -geoid RegioSanitariaCodi -accumulate "NumCasos / NumberCases" -fdate dd/mm/yyyy -date TipusCasData -cond-field "TipusCasDescripcio / TipoCasoDescripcion / CaseTypeDescription" -cond-value Positiu -remove-field "SexeCodi / SexoCodigo / GenderCode" -remove-field "SexeDescripcio / SexoDescripcion / GenderDescription" -remove-field ABSCodi -remove-field ABSDescripcio -remove-field SectorSanitariCodi -remove-field SectorSanitariDescripcio -a-circle 0.3
    python covid19_2_geojson.py "https://analisi.transparenciacatalunya.cat/api/views/xuwf-dxjd/rows.csv?accessType=DOWNLOAD&sorting=true" ss-cat-covid-19 -href-enc utf8 -mmn C:\inetpub\wwwroot\covid19 -longlat "D:\datacube\covid-19\centroidesSS_CAT.geojson" -geoid SectorSanitariCodi -accumulate "NumCasos / NumberCases" -fdate dd/mm/yyyy -date TipusCasData -cond-field "TipusCasDescripcio / TipoCasoDescripcion / CaseTypeDescription" -cond-value Positiu -remove-field "SexeCodi / SexoCodigo / GenderCode" -remove-field "SexeDescripcio / SexoDescripcion / GenderDescription" -remove-field ABSCodi -remove-field ABSDescripcio -a-circle 1
    python covid19_2_geojson.py "https://analisi.transparenciacatalunya.cat/api/views/xuwf-dxjd/rows.csv?accessType=DOWNLOAD&sorting=true" abs-cat-covid-19 -href-enc utf8 -mmn C:\inetpub\wwwroot\covid19 -longlat "D:\datacube\covid-19\centroidesABS.geojson" -geoid ABSCodi -accumulate "NumCasos / NumberCases" -fdate dd/mm/yyyy -date TipusCasData -cond-field "TipusCasDescripcio / TipoCasoDescripcion / CaseTypeDescription" -cond-value Positiu -remove-field "SexeCodi / SexoCodigo / GenderCode" -remove-field "SexeDescripcio / SexoDescripcion / GenderDescription"  -a-circle 1.5
    fart c:\inetpub\wwwroot\covid19\config.json "Catalu\u00f1a" "Catalunya"
    fart c:\inetpub\wwwroot\covid19\config.json "Baleares" "Illes Balears"
    fart c:\inetpub\wwwroot\covid19\config.json "Pa\u00eds Vasco" "Euskadi"
    fart c:\inetpub\wwwroot\covid19\config.json "\"descripcio\": \"RegioSanitariaCodi\"" "\"descripcio\": \"Codi de Regi\xC3\xB3 Sanit\xC3\xA0ria\"" --c-style
    fart c:\inetpub\wwwroot\covid19\config.json "\"descripcio\": \"SectorSanitariCodi\"" "\"descripcio\": \"Codi de Sector Sanitari\"" --c-style
    fart c:\inetpub\wwwroot\covid19\config.json "\"descripcio\": \"SectorSanitariDescripcio\"" "\"descripcio\": \"Sector Sanitari\"" --c-style
    fart c:\inetpub\wwwroot\covid19\config.json "\"descripcio\": \"RegioSanitariaDescripcio\"" "\"descripcio\": \"Regi\xC3\xB3 Sanit\xC3\xA0ria\"" --c-style
    fart c:\inetpub\wwwroot\covid19\config.json "\"descripcio\": \"ABSCodi\"" "\"descripcio\": \"Codi d\'ABS\"" --c-style
    fart c:\inetpub\wwwroot\covid19\config.json "\"descripcio\": \"ABSDescripcio\"" "\"descripcio\": \"ABS\""
    python sort_config_json.py world-covid-19 -mmn C:\inetpub\wwwroot\covid19 -section atributs -i-item 0 -i-item 1 -i-item 14 -i-item 2 -i-item 6 -i-item 10 -i-item 15 -i-item 3 -i-item 7 -i-item 11 -i-item 16 -i-item 17 -i-item 4 -i-item 5 -i-item 8 -i-item 9 -i-item 12 -i-item 13 -i-item 18
    python sort_config_json.py spain-covid-19 -mmn C:\inetpub\wwwroot\covid19 -section atributs -i-item 0 -i-item 1 -i-item 22 -i-item 2 -i-item 6 -i-item 10 -i-item 23 -i-item 3 -i-item 7 -i-item 11 -i-item 24 -i-item 25 -i-item 4 -i-item 5 -i-item 8 -i-item 9 -i-item 12 -i-item 13 -i-item 14 -i-item 15 -i-item 16 -i-item 17 -i-item 18 -i-item 19 -i-item 20 -i-item 21 -i-item 26
    
    Velles que no serveixen
    fart c:\inetpub\wwwroot\covid19\config.json "ABSDescripci\u00f3" "ABSDescripcio"

    python covid19_2_geojson.py "https://analisi.transparenciacatalunya.cat/api/views/xuwf-dxjd/rows.csv?accessType=DOWNLOAD&sorting=true" rs-cat-covid-19 -href-enc utf8 -mmn C:\inetpub\wwwroot\covid19 -longlat "D:\datacube\covid-19\centroidesRS_CAT.geojson" -geoid RegioSanitariaCodi -fdate dd/mm/yyyy -date TipusCasData -cond-field TipusCasDescripcio -cond-value Positiu -remove-field SexeCodi -remove-field SexeDescripcio -remove-field ABSCodi -remove-field ABSDescripcio -remove-field SectorSanitariCodi -remove-field SectorSanitariDescripcio -a-circle 0.3
    python covid19_2_geojson.py "https://analisi.transparenciacatalunya.cat/api/views/xuwf-dxjd/rows.csv?accessType=DOWNLOAD&sorting=true" ss-cat-covid-19 -href-enc utf8 -mmn C:\inetpub\wwwroot\covid19 -longlat "D:\datacube\covid-19\centroidesSS_CAT.geojson" -geoid SectorSanitariCodi -fdate dd/mm/yyyy -date TipusCasData -cond-field TipusCasDescripcio -cond-value Positiu -remove-field SexeCodi -remove-field SexeDescripcio -remove-field ABSCodi -remove-field ABSDescripcio -a-circle 1
    python covid19_2_geojson.py "https://analisi.transparenciacatalunya.cat/api/views/xuwf-dxjd/rows.csv?accessType=DOWNLOAD&sorting=true" abs-cat-covid-19 -href-enc utf8 -mmn C:\inetpub\wwwroot\covid19 -longlat "D:\datacube\covid-19\centroidesABS.geojson" -geoid ABSCodi -fdate dd/mm/yyyy -date TipusCasData -cond-field TipusCasDescripcio -cond-value Positiu -remove-field SexeCodi -remove-field SexeDescripcio -a-circle 1.5

    python covid19_2_geojson.py "https://analisi.transparenciacatalunya.cat/api/views/xuwf-dxjd/rows.csv?accessType=DOWNLOAD&sorting=true" rs-cat-covid-19 -href-enc utf8 -mmn C:\inetpub\wwwroot\covid19 -longlat "D:\datacube\covid-19\centroidesRS_CAT.geojson" -geoid RegioSanitariaCodi -fdate dd/mm/yyyy -date Data -cond-field ResultatCovidCodi -cond-value 1 -remove-field SexeCodi -remove-field SexeDescripcio -remove-field ResultatCovidDescripcio -remove-field ABSCodi -remove-field ABSDescripcio -remove-field SectorSanitariCodi -remove-field SectorSanitariDescripcio
    python covid19_2_geojson.py "https://analisi.transparenciacatalunya.cat/api/views/xuwf-dxjd/rows.csv?accessType=DOWNLOAD&sorting=true" ss-cat-covid-19 -href-enc utf8 -mmn C:\inetpub\wwwroot\covid19 -longlat "D:\datacube\covid-19\centroidesSS_CAT.geojson" -geoid SectorSanitariCodi -fdate dd/mm/yyyy -date Data -cond-field ResultatCovidCodi -cond-value 1 -remove-field SexeCodi -remove-field SexeDescripcio -remove-field ResultatCovidDescripcio -remove-field ABSCodi -remove-field ABSDescripcio -a-circle 2
    python covid19_2_geojson.py "https://analisi.transparenciacatalunya.cat/api/views/xuwf-dxjd/rows.csv?accessType=DOWNLOAD&sorting=true" abs-cat-covid-19 -href-enc utf8 -mmn C:\inetpub\wwwroot\covid19 -longlat "D:\datacube\covid-19\centroidesABS.geojson" -geoid ABSCodi -fdate dd/mm/yyyy -date Data -cond-field ResultatCovidCodi -cond-value 1 -remove-field SexeCodi -remove-field SexeDescripcio -remove-field ResultatCovidDescripcio -a-circle 10
    
    debug python covid19_2_geojson.py "D:\docs\Recerca\covid-19\AreesBasiquesSalut\Registre_de_test_de_COVID-19_realitzats_a_Catalunya._Segregaci__per_sexe_i__rea_b_sica_de_salut__ABS_.csv" -href-type local abs-cat-covid-19 -href-enc utf8 -mmn C:\inetpub\wwwroot\covid19 -longlat "D:\datacube\covid-19\centroidesABS.geojson" -geoid ABSCodi -fdate dd/mm/yyyy -date Data -cond-field ResultatCovidCodi -cond-value 1 -remove-field SexeCodi -remove-field SexeDescripcio -remove-field ResultatCovidDescripcio -a-circle 10
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
                
            csvreader = csv.DictReader(csvfile)
            if (date is None):
                csvreader = tranformDatesCsv(csvreader, prefix_var, fdate)
            else:
                csvreader = AccumulateDatesCsv(csvreader, geoid, date, fdate, accumulate, cond_field, cond_value, remove_field)
                csvreader = tranformDatesCsv(csvreader, prefix_var, "yyyy-mm-dd")
                
            if longlat is None:
                objectes=csv2geojson(csvreader, long, lat)
            else:
                pathlonglat = Path(longlat)
                if pathlonglat.exists()==False:
                    raise RuntimeError("GeoJSON file does not exist {}".format(str(pathlonglat)))
                geojsonfile=open(pathlonglat, "r", encoding='utf-8-sig')
                geojson = json.load(geojsonfile)
                geojsonfile.close()
                objectes=csv_geoid2geojson(csvreader, geojson, geoid)
            
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
            # tt10="p['"+prefix_var+"{time?f=ISO&day=+4}']"
            # tt9="p['"+prefix_var+"{time?f=ISO&day=+3}']"
            # tt8="p['"+prefix_var+"{time?f=ISO&day=+2}']"
            # tt7="p['"+prefix_var+"{time?f=ISO&day=+1}']"
            # tt6="p['"+prefix_var+"{time?f=ISO}']"
            # tt5="p['"+prefix_var+"{time?f=ISO&day=-1}']"
            # tt4="p['"+prefix_var+"{time?f=ISO&day=-2}']"
            # tt3="p['"+prefix_var+"{time?f=ISO&day=-3}']"
            # tt2="p['"+prefix_var+"{time?f=ISO&day=-4}']"
            # tt1="p['"+prefix_var+"{time?f=ISO&day=-5}']"
            # tt0="p['"+prefix_var+"{time?f=ISO&day=-6}']"
        else:
            nameAtrib=prefix_var
            #lastDay="("+tname+")"
            #beforeLastDay="("+tname.replace("{time?f=ISO}", "{time?f=ISO&day=-1}")+")"
            #beforeBeforeLastDay="("+tname.replace("{time?f=ISO}", "{time?f=ISO&day=-2}")+")"
            t6="("+tname.replace("{time?f=ISO}", "{time?f=ISO&day=+2}")+")"
            t5="("+tname.replace("{time?f=ISO}", "{time?f=ISO&day=+1}")+")"
            t4="("+tname+")"
            t3="("+tname.replace("{time?f=ISO}", "{time?f=ISO&day=-1}")+")"
            t2="("+tname.replace("{time?f=ISO}", "{time?f=ISO&day=-2}")+")"
            t1="("+tname.replace("{time?f=ISO}", "{time?f=ISO&day=-3}")+")"
            t0="("+tname.replace("{time?f=ISO}", "{time?f=ISO&day=-4}")+")"
            tc="("+tname.replace("{time?f=ISO}", "{time?f=ISO&day=-5}")+")"
            tr="("+tname.replace("{time?f=ISO}", "{time?f=ISO&day=-10}")+")"
            # tt10="("+tname.replace("{time?f=ISO}", "{time?f=ISO&day=+4}")+")"
            # tt9="("+tname.replace("{time?f=ISO}", "{time?f=ISO&day=+3}")+")"
            # tt8="("+tname.replace("{time?f=ISO}", "{time?f=ISO&day=+2}")+")"
            # tt7="("+tname.replace("{time?f=ISO}", "{time?f=ISO&day=+1}")+")"
            # tt6="("+tname+")"
            # tt5="("+tname.replace("{time?f=ISO}", "{time?f=ISO&day=-1}")+")"
            # tt4="("+tname.replace("{time?f=ISO}", "{time?f=ISO&day=-2}")+")"
            # tt3="("+tname.replace("{time?f=ISO}", "{time?f=ISO&day=-3}")+")"
            # tt2="("+tname.replace("{time?f=ISO}", "{time?f=ISO&day=-4}")+")"
            # tt1="("+tname.replace("{time?f=ISO}", "{time?f=ISO&day=-5}")+")"
            # tt0="("+tname.replace("{time?f=ISO}", "{time?f=ISO&day=-6}")+")"
            atrib.append({"nom": nameAtrib, 
                          "descripcio": desc_var, 
                          "FormulaConsulta": t4,
                          "mostrar": "si",
                          "serieTemporal": {"color": rgb_string_to_hex(color)}
                    })
        estil.append({"nom": None, "desc": "Count of "+desc_var, 
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
          								"a": float(a_circle)
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
              		})
            
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
                "NDecimals": 2,
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
      
#             ,{"nom": prefix_var+"NewCases9",
# 				"descripcio": "New "+desc_var+" in a day (av. 9)",
# 				"FormulaConsulta": "(("+tt10+"-"+tt1+")/9)",
# 				"mostrar": "si",
#                 "serieTemporal": {"color": rgb_string_to_hex(color)}
#             },{"nom": prefix_var+"PercentCumulCases9",
# 				"descripcio": "Increase in cumulated "+desc_var+ " (av. 9)",
# 				"FormulaConsulta": "(("+tt10+"-"+tt1+")/("+tt9+"+"+tt8+"+"+tt7+"+"+tt6+"+"+tt5+"+"+tt4+"+"+tt3+"+"+tt2+"+"+tt1+")*100)",
# 				"NDecimals": 2,
#                 "unitats": "%",
# 				"mostrar": "si",
#                 "serieTemporal": {"color": rgb_string_to_hex(color)}
# 			},{"nom": prefix_var+"Acceleration9",
# 				"descripcio": "Last day Acceleration in "+desc_var+ " (av. 9)",
#                 "unitats": "cases/day²",
# 				"FormulaConsulta": "(("+tt10+"-"+tt9+"+"+tt0+"-"+tt1+")/9)",
# 				"NDecimals": 2,
# 				"mostrar": "si",
#                 "serieTemporal": {"color": rgb_string_to_hex(color)}
# 			},{"nom": prefix_var+"PercentAccel9",
# 				"descripcio": "Last day Percentual Acceleration in "+desc_var+" (av. 9)",
# 				"FormulaConsulta": "(("+tt10+"-"+tt9+"+"+tt0+"-"+tt1+")/("+tt9+"-"+tt0+")*100)",
# 				"NDecimals": 2,
#                 "unitats": "%",
# 				"mostrar": "si",
#                 "serieTemporal": {"color": rgb_string_to_hex(color)}
#			}
      ])
        estil.extend([
            # {"nom": None, "desc": "New "+desc_var+" in a day", 
      		    #             "TipusObj": "P",
            #         		"ItemLleg":	[
            #       				{"color": rgb_string_to_hex(color), "DescColor": desc_var}
            #       			],
            #       			"ncol": 1,
            #       			"simbols": [{							
            #   					"NomCampFEscala": prefix_var+"NewCases",
            #   					"simbol":
            #   					[{
            #   							"icona":{
            #   								"type": "circle",
            #   								"a": float(a_circle)
            #   							}
          		# 				}]
            #       			}],
            #       			"vora":{
            #       				"paleta": {"colors": [rgb_string_to_hex(color)]}
            #       			},
            #       			"interior":{
            #       				"paleta": {"colors": ["rgba("+color+",0.4)"]}
            #       			},			
            #       			"fonts": {
            #       				"NomCampText": prefix_var+"NewCases",
            #       				"aspecte": [{
            #       					"font": {
            #                               "font": "12px Verdana", "color": "#B50000", "align": "center", "i": 0, "j": -5
            #                         }
            #       				}]
            #       			}
            #       		},{"nom": None, "desc": "Increase in cumulated "+desc_var+" (%)", 
            # 				"DescItems": "%",
      		    #             "TipusObj": "P",
            #         		"ItemLleg":	[
            #       				{"color": rgb_string_to_hex(color), "DescColor": desc_var}
            #       			],
            #       			"ncol": 1,
            #       			"simbols": [{							
            #   					"NomCampFEscala": prefix_var+"PercentCumulCases",
            #   					"simbol":
            #   					[{
            #   							"icona":{
            #   								"type": "circle",
            #   								"a": 20
            #   							}
          		# 				}]
            #       			}],
            #       			"vora":{
            #       				"paleta": {"colors": [rgb_string_to_hex(color)]}
            #       			},
            #       			"interior":{
            #       				"paleta": {"colors": ["rgba("+color+",0.4)"]}
            #       			},			
            #       			"fonts": {
            #       				"NomCampText": prefix_var+"PercentCumulCases",
            #       				"aspecte": [{
            #       					"font": {
            #                               "font": "12px Verdana", "color": "#B50000", "align": "center", "i": 0, "j": -5
            #                         }
            #       				}]
            #       			}
            #       		},{"nom": None, "desc": "Last day Acceleration in "+desc_var+" (cases/day<sup>2</sup>)", 
            # 				"DescItems": "cases/day<sup>2</sup>",
      		    #             "TipusObj": "P",
            #         		"ItemLleg":	[\
            #       				{"color": rgb_string_to_hex(color), "DescColor": desc_var}
            #       			],
            #       			"ncol": 1,
            #       			"simbols": [{							
            #   					"NomCampFEscala": prefix_var+"Acceleration",
            #   					"simbol":
            #   					[{
            #   							"icona":{
            #   								"type": "circle",
            #   								"a": float(a_circle)*5
            #   							}
          		# 				}]
            #       			}],
            #       			"vora":{
            #       				"paleta": {"colors": [rgb_string_to_hex(color)]}
            #       			},
            #       			"interior":{
            #       				"paleta": {"colors": ["rgba("+color+",0.4)"]}
            #       			},			
                              
            #       			"fonts": {
            #       				"NomCampText": prefix_var+"Acceleration",
            #       				"aspecte": [{
            #       					"font": {
            #                               "font": "12px Verdana", "color": "#B50000", "align": "center", "i": 0, "j": -5
            #                         }
            #       				}]
            #       			}
            #       		},{"nom": None, "desc": "Percentual Accel. "+desc_var+" (%)", 
            # 				"DescItems": "%",
      		    #             "TipusObj": "P",
            #         		"ItemLleg":	[\
            #       				{"color": rgb_string_to_hex(color), "DescColor": desc_var}
            #       			],
            #       			"ncol": 1,
            #       			"simbols": [{							
            #   					"NomCampFEscala": prefix_var+"PercentAccel",
            #   					"simbol":
            #   					[{
            #   							"icona":{
            #   								"type": "circle",
            #   								"a": 5
            #   							}
          		# 				}]
            #       			}],
            #       			"vora":{
            #       				"paleta": {"colors": [rgb_string_to_hex(color)]}
            #       			},
            #       			"interior":{
            #       				"paleta": {"colors": ["rgba("+color+",0.4)"]}
            #       			},			
            #       			"fonts": {
            #       				"NomCampText": prefix_var+"PercentAccel",
            #       				"aspecte": [{
            #       					"font": {
            #                               "font": "12px Verdana", "color": "#B50000", "align": "center", "i": 0, "j": -5
            #                         }
            #       				}]
            #       			}
            #       		},
                       
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
              								"a": float(a_circle)*10
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
                # Removed on 2020/05/08 as it has to many small or negative values
                #         {"nom": None, "desc": "Increase in cumulated "+desc_var+" (av.5) (%)", 
            				# "DescItems": "%",
      		        #         "TipusObj": "P",
                #     		"ItemLleg":	[
                #   				{"color": rgb_string_to_hex(color), "DescColor": desc_var}
                #   			],
                #   			"ncol": 1,
                #   			"simbols": [{							
              		# 			"NomCampFEscala": prefix_var+"PercentCumulCases5",
              		# 			"simbol":
              		# 			[{
              		# 					"icona":{
              		# 						"type": "circle",
              		# 						"a": 20
              		# 					}
          						# }]
                #   			}],
                #   			"vora":{
                #   				"paleta": {"colors": [rgb_string_to_hex(color)]}
                #   			},
                #   			"interior":{
                #   				"paleta": {"colors": ["rgba("+color+",0.4)"]}
                #   			},			
                #   			"fonts": {
                #   				"NomCampText": prefix_var+"PercentCumulCases5",
                #   				"aspecte": [{
                #   					"font": {
                #                           "font": "12px Verdana", "color": "#B50000", "align": "center", "i": 0, "j": -5
                #                     }
                #   				}]
                #   			}
                #   		},
                # Removed on 2020/05/08 as it has to many small or negative values
                #{"nom": None, "desc": "Last day Acceleration in "+desc_var+" (av.5) (cases/day<sup>2</sup>)", 
            				# "DescItems": "cases/day<sup>2</sup>",
      		        #         "TipusObj": "P",
                #     		"ItemLleg":	[\
                #   				{"color": rgb_string_to_hex(color), "DescColor": desc_var}
                #   			],
                #   			"ncol": 1,
                #   			"simbols": [{							
              		# 			"NomCampFEscala": prefix_var+"Acceleration5",
              		# 			"simbol":
              		# 			[{
              		# 					"icona":{
              		# 						"type": "circle",
              		# 						"a": float(a_circle)*5
              		# 					}
          						# }]
                #   			}],
                #   			"vora":{
                #   				"paleta": {"colors": [rgb_string_to_hex(color)]}
                #   			},
                #   			"interior":{
                #   				"paleta": {"colors": ["rgba("+color+",0.4)"]}
                #   			},			
                              
                #   			"fonts": {
                #   				"NomCampText": prefix_var+"Acceleration5",
                #   				"aspecte": [{
                #   					"font": {
                #                           "font": "12px Verdana", "color": "#B50000", "align": "center", "i": 0, "j": -5
                #                     }
                #   				}]
                #   			}
                #   		}
                # Removed on 2020/04/28 as it is difficult to understand
                #        ,{"nom": None, "desc": "Percentual Accel. "+desc_var+" (av.5) (%)", 
            				# "DescItems": "%",
      		        #         "TipusObj": "P",
                #     		"ItemLleg":	[\
                #   				{"color": rgb_string_to_hex(color), "DescColor": desc_var}
                #   			],
                #   			"ncol": 1,
                #   			"simbols": [{							
              		# 			"NomCampFEscala": prefix_var+"PercentAccel5",
              		# 			"simbol":
              		# 			[{
              		# 					"icona":{
              		# 						"type": "circle",
              		# 						"a": 5
              		# 					}
          						# }]
                #   			}],
                #   			"vora":{
                #   				"paleta": {"colors": [rgb_string_to_hex(color)]}
                #   			},
                #   			"interior":{
                #   				"paleta": {"colors": ["rgba("+color+",0.4)"]}
                #   			},			
                #   			"fonts": {
                #   				"NomCampText": prefix_var+"PercentAccel5",
                #   				"aspecte": [{
                #   					"font": {
                #                           "font": "12px Verdana", "color": "#B50000", "align": "center", "i": 0, "j": -5
                #                     }
                #   				}]
                #   			}
                #   		}                        
                ])
        if prefix_var=="act":
            atrib.append({
    				"nom": prefix_var+"AccelTerna",
    				"descripcio": "Acceleration Ternary",
    				#"FormulaConsulta": "(("+beforeLastDay+"==0)?0:((("+lastDay+"-"+beforeLastDay+")/"+beforeLastDay+">0.05 && "+lastDay+"-2*"+beforeLastDay+"+"+beforeBeforeLastDay+">0)?7:((("+lastDay+"-"+beforeLastDay+")/"+beforeLastDay+">0.05 && "+lastDay+"-2*"+beforeLastDay+"+"+beforeBeforeLastDay+"<=0)?6:((("+lastDay+"-"+beforeLastDay+")/"+beforeLastDay+">0)?5:((("+lastDay+"-"+beforeLastDay+")/"+beforeLastDay+"==0)?4:((("+lastDay+"-"+beforeLastDay+")/"+beforeLastDay+">-0.05)?3:(("+lastDay+"-2*"+beforeLastDay+"+"+beforeBeforeLastDay+">=0)?2:1)))))))",
                    #"FormulaConsulta": "(("+beforeLastDay+"-"+beforeBeforeLastDay+"==0)?0:((("+lastDay+"-2*"+beforeLastDay+"+"+beforeBeforeLastDay+")/("+beforeLastDay+"-"+beforeBeforeLastDay+")>0.05&&"+lastDay+"-2*"+beforeLastDay+"+"+beforeBeforeLastDay+">0)?7:((("+lastDay+"-2*"+beforeLastDay+"+"+beforeBeforeLastDay+")/("+beforeLastDay+"-"+beforeBeforeLastDay+")>0.05&&"+lastDay+"-2*"+beforeLastDay+"+"+beforeBeforeLastDay+"<=0)?6:((("+lastDay+"-2*"+beforeLastDay+"+"+beforeBeforeLastDay+")/("+beforeLastDay+"-"+beforeBeforeLastDay+")>0)?5:((("+lastDay+"-2*"+beforeLastDay+"+"+beforeBeforeLastDay+")/("+beforeLastDay+"-"+beforeBeforeLastDay+")==0)?4:((("+lastDay+"-2*"+beforeLastDay+"+"+beforeBeforeLastDay+")/("+beforeLastDay+"-"+beforeBeforeLastDay+")>-0.05)?3:(("+lastDay+"-2*"+beforeLastDay+"+"+beforeBeforeLastDay+">=0)?2:1)))))))",
                    "FormulaConsulta": "(isNaN("+t4+")?6:(("+t4+">"+tr+"+("+t4+"+"+tr+")*0.03)?(("+tc+"<("+t4+"+"+tr+")/2-("+t4+"-"+tr+")*0.05)?0:1):(("+t4+"<"+tr+"-("+t4+"+"+tr+")*0.03)?(("+tc+">("+t4+"+"+tr+")/2+("+t4+"-"+tr+")*0.05)?3:4):(("+t4+"<700)?5:2))))",
    				"mostrar": "no"
    			})
            estil.append({"nom": None,
                			"desc":	"Last days Tendency",
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
            mmnfile=open(pathmmn, "r", encoding='utf-8-sig')
            ParamCtrl=updateConfigJSON(mmnfile, layer, add_var, prefix_var, objectes, atrib, estil, dies)
            mmnfile.close()
            mmnfile=open(pathmmn, "w", encoding='utf-8-sig')
            json.dump(ParamCtrl, mmnfile, indent="\t")
            mmnfile.close()
            
        #include it into the config.json
        
    except:
        log.exception('Exception from main():')
        sys.exit(1) 
        return 1

if __name__ == '__main__':
    main()
