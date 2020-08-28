# Data about COVID-19 created by the Grumets research group in CREAF (World, Spain, Catalonia)

This repository provides the daily updated results of transforming the World data (John Hopkins), Spanish data (Ministerio de Sanidad) and Catalan data (Departament de Salut; Generalitat de Catalunya) to geojson (see the datasets folder)

It also provides the code that we use to do so:  Some Python codes to transform some open data (World, Spain and Catalonia) about COVID 19 into embedded objects in a config.json that configures the MiraMon Map Browser. I use these codes every day to regularly update this map: http://datacube.uab.cat/covid19/ (see the code folder). The codes combine the capacity to read CSV, transform it into GeoJSON and manipulate sections of a preexisting JSON file (config.json) and creating geojson versions of the data.

To transform the data from CSV to geojson some centroids of the different areas are used to create a point features of each "place". This static geojson files are also provided (see the centroids folder)

See some press releases here:
* http://blog.creaf.cat/en/knowledge/open-data-policies-times-covid-19/
* https://www.uab.cat/web/newsroom/news-detail/map-navigator-shows-covid-19-s-evolution-1345668003610.html?noticiaid=1345822779560
* http://www.grumets.uab.cat/index_eng.htm?month=may-2020
