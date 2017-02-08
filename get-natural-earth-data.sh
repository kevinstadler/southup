#!/bin/sh

# choose natural earth data set resolution (1:110m, 1:50m or 1:10m)
RESOLUTION=50

download_and_unzip () {
  wget http://www.naturalearthdata.com/http//www.naturalearthdata.com/download/${RESOLUTION}m/$1
  unzip `basename $1` -x VERSION CHANGELOG README.md
}

mkdir data
cd data

# bounding box
download_and_unzip physical/ne_${RESOLUTION}m_wgs84_bounding_box.zip

# grid lines - available in intervals of 30, 20, 15, 10, 5 and 1
download_and_unzip physical/ne_${RESOLUTION}m_graticules_30.zip

# oceans+landmasses
download_and_unzip physical/ne_${RESOLUTION}m_ocean.zip
download_and_unzip physical/ne_${RESOLUTION}m_land.zip
# ocean floor
#download_and_unzip raster/OB_${RESOLUTION}M.zip

# cultural data
download_and_unzip cultural/ne_${RESOLUTION}m_admin_0_countries.zip

ls -l
echo "Done."
cd ..
