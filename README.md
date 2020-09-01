# Data about COVID-19 created by the Grumets research group in CREAF (World, Spain, Catalonia)

This repository provides the daily updated results of transforming the World data (John Hopkins from https://github.com/CSSEGISandData/COVID-19/tree/master/csse_covid_19_data), Spanish data (Ministerio de Sanidad; from https://github.com/datadista/datasets/tree/master/COVID%2019 and https://www.mscbs.gob.es/en/profesionales/saludPublica/ccayes/alertasActual/nCov/situacionActual.htm) and Catalan data (Departament de Salut; Generalitat de Catalunya: https://analisi.transparenciacatalunya.cat/browse?q=covid&sortBy=relevance) to geojson (see the datasets folder).

This way the data can be immediately seen in a modern GIS system. Some attributes in the data ends with a date allowing for immediate representation of a time series as we do in http://www.datacube.uab.cat/covid19 map viewer

It also provides the code that we use to do so:  Some Python codes to transform some open data (World, Spain and Catalonia) about COVID 19 into embedded objects in a config.json that configures the MiraMon Map Browser. We use these codes every day to regularly update this map: http://datacube.uab.cat/covid19/ (see the code folder). The codes combine the capacity to read CSV, transform it into GeoJSON and manipulate sections of a preexisting JSON file (config.json) as well as and creating geojson versions of the data availble here in the datasets folder.

To transform the data from CSV to geojson some centroids of the different areas are used to create point features of each "place". This static geojson files are also provided (see the centroids folder)

See some press releases here:
* http://blog.creaf.cat/en/knowledge/open-data-policies-times-covid-19/
* https://www.uab.cat/web/newsroom/news-detail/map-navigator-shows-covid-19-s-evolution-1345668003610.html?noticiaid=1345822779560
* http://www.grumets.uab.cat/index_eng.htm?month=may-2020

## Comments
### Data from Spain
The Datadista series (https://github.com/datadista/datasets/tree/master/COVID%2019) is made from the Open Data created by the Ministerio de Sanidad (https://datos.gob.es/es/catalogo/e05070101-evolucion-de-enfermedad-por-el-coronavirus-covid-19). We also use it to create the Spanish provinces dataset (datasets\covid19-prov-spain.geojson). Unfortunately the Ministerio updates this data irregularly aout every 10 days and it has at least 5 days delay or more. We believe we cannot wait so long to show the status of the pandemic so, recently, we decided to manually extract data at CCAA level from the "Actualización nºXXX: enfermedad por SARS-CoV-2 (COVID-19) files" that are PDF reports generated every day (except weekends) by the Ministerio and that are collected by the datadista GitHub. From the PDF we extract the data at the Autonomous Communities level of detail and create a more up to date datasets\covid19-ccaa-spain.geojson. For the moment we have about a month of data but we will continue enriching it with old and new PDF reports.

**NOTA (2020-08-20)** Interesting new data has been added to the PDF reports. Now, we are able to extract new attributes: Number of PCR done in a day (PCRDia); Number of people currently in hospitals (Ingresados), number of people in intensive case (UCI), Ratio of beds in hospitals with COVID patients (PorcenCamas), Admitted to hospital in the last day (Ingressos24h), Discharged from hospitals in the last 24h (Altas24h)
