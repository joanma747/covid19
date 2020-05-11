# -*- coding: utf-8 -*-
"""
Import a COVID-19 csv file and edit a config.json to include this data in a vector capa

"""

import click
import logging
from pathlib import Path
import json
import sys
import copy


def sortConfigJSON(mmnfile, layer, name_section, i_item):
    ParamCtrl = json.load(mmnfile)
#https://stackoverflow.com/questions/8653516/python-list-of-dictionaries-search
    capa=next((item for item in ParamCtrl["capa"] if item["nom"] == layer), None)
    if capa==None:
        raise ValueError("I cannot find the capa in the map browser configuration file")
        
    if name_section:
        section=copy.copy(capa[name_section])
        capa[name_section]=[]
        for i_item_in_section in i_item:
            capa[name_section].append(section[i_item_in_section])
    return ParamCtrl


#https://click.palletsprojects.com/en/7.x/options/
@click.command()
@click.argument('layer')
@click.option('-mmn', help="Path of the config.json of the MiraMon Map Browser. If not specified, it will not be updates with the new dates")
@click.option('-section', default="atributs", help="Section to sort in a different way")
@click.option('-i-item', multiple=True, type=int, help="Order of the item in the property")
              
def main(layer, mmn, section, i_item):
    """
    Import a COVID-19 csv file and edit a config.json to include this data in a vector capa
    The csv need to have a fields with a name that is a date in fdate format. These fields contains
    the values of a single variable in time.
    The format used in https://github.com/CSSEGISandData/COVID-19/tree/master/csse_covid_19_data/csse_covid_19_time_series is directly supported
    
    Params: 
    <layer> name of the layer. It should be the same as the name of the folder in the server, the name of the REL5 and the name of the layer in the config.json.       
    
    Example:
    python sort_config_json.py world-covid-19 -mmn C:\inetpub\wwwroot\covid19 -section atributs -i-item 0 -i-item 1 -i-item 14 -i-item 2 -i-item 6 -i-item 10 -i-item 15 -i-item 3 -i-item 7 -i-item 11 -i-item 16 -i-item 17 -i-item 4 -i-item 5 -i-item 8 -i-item 9 -i-item 12 -i-item 13
    python sort_config_json.py spain-covid-19 -mmn C:\inetpub\wwwroot\covid19 -section atributs -i-item 0 -i-item 1 -i-item 22 -i-item 2 -i-item 6 -i-item 10 -i-item 23 -i-item 3 -i-item 7 -i-item 11 -i-item 24 -i-item 25 -i-item 4 -i-item 5 -i-item 8 -i-item 9 -i-item 12 -i-item 13 -i-item 14 -i-item 15 -i-item 16 -i-item 17 -i-item 18 -i-item 19 -i-item 20 -i-item 21
    
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
        
        if mmn is not None:
            mmnfile=open(pathmmn, "r", encoding='utf-8-sig')
            ParamCtrl=sortConfigJSON(mmnfile, layer, section, i_item)
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
