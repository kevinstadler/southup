#!/usr/bin/env python2
# -*- coding: utf-8 -*-

# hide redefined mapnik python bindings warning on import
import warnings
warnings.simplefilter("ignore")
from mapnik import *
warnings.resetwarnings()

import xml.dom.minidom as xml
from colorsys import hsv_to_rgb
from random import randint
import os.path 
import subprocess

from argparse import ArgumentParser
parser = ArgumentParser(description='south up! (and other custom maps made easy)')

parser.add_argument('output', help='output filename')

# input
input = parser.add_argument_group('input file options')
input.add_argument('--prefix', default='data/ne_50m',
	help='Natural earth data set prefix (default: "%(default)s")')

# rendering
rendering = parser.add_argument_group('visualisation options')
rendering.add_argument('--raster', help='path to raster file to be used as base layer')
rendering.add_argument('--colors', '-cols', choices=[7, 8, 9, 13], nargs='?',
	type=int, const=7, help='number of fill colours to use for country polygons')
rendering.add_argument('--names', action='store_true', help='add country names')
rendering.add_argument('--grid', '-g', choices=[30, 20, 15, 10, 5, 1], nargs='?',
	type=int, const=30, help='overlay meridian/parallel grid at given spacing')
rendering.add_argument('--xml', '-x', default='southup.xml',
	help='mapnik style file (default: %(default)s)')

# geography
projection = parser.add_argument_group('projection options')
projection.add_argument('--srs', default='+proj=moll +axis=wsu +ellps=WGS84 +no_defs',
	help='map projection to be used (proj.4 string, default: "%(default)s")')
projection.add_argument('--scale', '-s', default=None, type=float,
	help='map scale denominator (i.e. render map as 1:x)')

# output
output = parser.add_argument_group('output/rendering options')
output.add_argument('-f', '--format', default='a3l',
	help='Cairo target page format (default: "%(default)s")')
output.add_argument('-m', '--margin', type=float, default=0.0,
	help='page margin in meters (default: %(default)s)')
output.add_argument('--dpi', type=float, default=72,
	help='output dpi (default: %(default)s)')

output.add_argument('--width', type=int, default=0,
	help='output width in pixels (for raster output only)')
output.add_argument('--height', type=int, default=0,
	help='output height in pixels (for raster output only)')

args = vars(parser.parse_args())

x = xml.parse(args['xml'])

# look at raster base picture first
if args['raster']:
	reprojected = args['raster'] + args['srs'] + '.tif'
	if os.path.isfile(reprojected):
		print 're-using existing reprojected raster image: ' + reprojected
	elif subprocess.call(['gdalwarp', '-s_srs', '+init=epsg:4236',
		'-t_srs', args['srs'] + ' +wktext', # to make +axis work
		'-multi','-te', str(-hbox.x), str(-vbox.y), str(hbox.x), str(vbox.y), 
		args['raster'], reprojected]) == 0:
		print 'stored in ' + reprojected
	else:
		warnings.warn('raster image reprojection failed, attempting to render in original projection')
#		args['raster'] = None


# add dynamic styles
if args['colors']:
	# pale rainbow
	colors = map(lambda rgb: Color(int(256*rgb[0]), int(256*rgb[1]), int(256*rgb[2])),
		[hsv_to_rgb(i / float(args['colors']+1), 0.5, 0.7) for i in range(args['colors'])])
	# random
	colors = [Color(randint(0, 255), randint(0, 255), randint(0, 255), 70 if args['raster'] else 255)
		for i in range(args['colors'])]
	land = next(style for style in x.getElementsByTagName('Style') if style.getAttribute('name') == 'land')
	rule = land.removeChild(land.getElementsByTagName('Rule')[0])
	for i in range(args['colors']):
		colrule = rule.cloneNode(True)
		colfilter = x.createElement('Filter')
		colfilter.appendChild(x.createTextNode('[mapcolor' + str(args['colors']) + '] = ' + str(i+1)))
		colrule.appendChild(colfilter)
		colrule.getElementsByTagName('PolygonSymbolizer')[0].setAttribute('fill', str(colors[i]))
		land.appendChild(colrule)


# initialise map with styles from xml, then add layers

# figure out map proportions that suit the projection
p = Projection(args['srs'])
hbox = p.forward(Coord(180, 0))
vbox = p.forward(Coord(0, 90))
prop = hbox.x / vbox.y

if args['width'] == 0:
	if args['height'] == 0:
		args['width'] = int(hbox.x)
		args['height'] = int(vbox.y)
	else:
		args['width'] = int(args['height'] * prop)

if args['height'] == 0:
	args['height'] = int(args['width'] / prop)

m = Map(args['width'], args['height'], args['srs'])

load_map_from_string(m, x.toxml('utf8'))

def addlayer(name, shapefile, style=None):
	l = Layer(name)
	l.datasource = Shapefile(file=shapefile)
	l.styles.append(style or name)
	m.layers.append(l)

if args['raster']:
	rl = Layer('raster')
	rl.datasource = Gdal(file=reprojected)
	rl.srs = args['srs'] # suppress reprojection
	rl.styles.append('raster')
	m.layers.append(rl)

addlayer('ocean', args['prefix'] + '_ocean.shp')

addlayer('land', args['prefix'] + '_admin_0_countries.shp') #_land.shp

if args['grid']:
	addlayer('grid', args['prefix'] + '_graticules_' + str(args['grid']) + '.shp', 'line')

# horizon/earth outline/bounding box
bbox = Layer('bbox')
bbox.datasource =  Shapefile(file=args['prefix'] + '_wgs84_bounding_box.shp')
bbox.styles.append('line')
m.layers.append(bbox)

if args['names']:
	names = Layer('names')
	names.datasource = Shapefile(file=args['prefix'] + '_admin_0_countries.shp')
	names.styles.append('name')
	m.layers.append(names)

m.zoom_all()
if args['scale'] != None:
	m.zoom(args['scale'] / m.scale_denominator())


print 'writing map to', args['output']

if os.path.splitext(args['output'])[1].lower() == '.pdf':
	import cairo
	pagesize = printing.pagesizes[args['format']]
	surface = printing.PDFPrinter(pagesize=pagesize, margin=args['margin'],
		resolution=args['dpi'], centering=printing.centering.both)
	surface.render_map(m, args['output'])
	#surface.render_scale(m)
	surface.finish()
else:
	render_to_file(m, args['output'])
