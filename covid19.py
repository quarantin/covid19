#!/usr/bin/env python

import os
import sys
import json
import hashlib
import requests
import traceback
from datetime import datetime
from collections import deque

# Worldwide
ww = 'WW'

jsondir = 'json'
htmldir = 'html'

json_url = 'https://opendata.ecdc.europa.eu/covid19/casedistribution/json/'

country_errors = {
	'Cote_dIvoire': 'Côte_d\'Ivoire',
}

""" Create specified folder if needed.
"""
def mkdir(dirpath):
	if not os.path.exists(dirpath):
		os.mkdir(dirpath, mode=0o755)

""" Write content to specified file.
"""
def write_file(filepath, content):

	fout = open(filepath, 'w')
	fout.write(content)
	fout.close()

""" Read content from specified file.
"""
def read_file(filepath):

	fin = open(filepath, 'r')
	content = fin.read()
	fin.close()

	return content

""" Read content from specified JSON file.
"""
def parse_json(filepath):
	return json.loads(read_file(filepath))

""" Parse daily data.
"""
def parse_daily(dataset):

	daily = {}
	daily[ww] = {}

	for record in dataset['records']:

		year  = record['year']
		month = record['month']
		day   = record['day']

		cc = record['geoId']

		date = '%s/%02d/%02d' % (year, int(month), int(day))

		if cc not in daily:
			daily[cc] = {}

		if date not in daily[ww]:
			daily[ww][date] = {
				'geoId': ww,
				'countriesAndTerritories': 'Worldwide',
				'cases': 0,
				'deaths': 0,
			}

		for key in [ 'cases', 'deaths' ]:
			record[key] = abs(int(record[key]))

		daily[cc][date] = record
		daily[ww][date]['cases']  += record['cases']
		daily[ww][date]['deaths'] += record['deaths']

	return daily

""" Parse cumulative data.
"""
def parse_cumulative(daily):

	cumul = {}

	for cc, data in sorted(daily.items()):

		cumul_cases = 0
		cumul_deaths = 0

		for date, record in sorted(data.items()):
			cumul_cases += record['cases']
			cumul_deaths += record['deaths']
			if cc not in cumul:
				cumul[cc] = {}

			cumul[cc][date] = dict(record)
			cumul[cc][date]['cases'] = cumul_cases
			cumul[cc][date]['deaths'] = cumul_deaths

	return cumul

""" Generate daily data to use with Chart.js.
"""
def generate_country_daily(dataset):

	cases  = []
	deaths = []
	labels = []
	country = 'Unknown'

	for date, record in sorted(dataset.items()):

		country_code = record['geoId']
		country_name = record['countriesAndTerritories']

		labels.append('"%s"' % date)
		cases.append(str(record['cases']))
		deaths.append(str(record['deaths']))

	return country_code, country_name, labels, cases, deaths

""" Genrate cumulative data to use with Chart.js.
"""
def generate_country_cumul(daily):

	cases  = []
	deaths = []
	labels = []
	country = 'Unknown'

	for date, record in sorted(daily.items()):

		if 'geoId' not in record:
			print(json.dumps(record, indent=4))
			raise Exception('Error 1')

		country_code = record['geoId']
		country_name = record['countriesAndTerritories']

		labels.append('"%s"' % date)
		cases.append(str(record['cases']))
		deaths.append(str(record['deaths']))

	return country_code, country_name, labels, cases, deaths

""" Generate trend data to use with Chart.js.
def generate_trend(values, days=5):

	trend = [ '0' ] * days
	stack = deque(maxlen=days)

	for value in values:
		if len(stack) == days:
			trend.append(str(sum(stack) / days))
		stack.append(int(value))

	return trend
"""

""" Generate HTML file for country.
"""
def generate_html_country(daily, cumul, template_file='templates/country.html'):

	cc_daily, country_daily, labels_daily, cases_daily, deaths_daily = generate_country_daily(daily)
	cc_cumul, country_cumul, labels_cumul, cases_cumul, deaths_cumul = generate_country_cumul(cumul)

	template = read_file(template_file)

	prefix = cc_daily != ww and 'for ' or ''

	if country_daily in country_errors:
		country_daily = country_errors[country_daily]

	country = '%s%s' % (prefix, country_daily.replace('_', ' '))

	template = template.replace('COUNTRY',             country)

	template = template.replace('CASES_CUMUL_VALUES',  ','.join(cases_cumul))
	template = template.replace('DEATHS_CUMUL_VALUES', ','.join(deaths_cumul))

	template = template.replace('CASES_DAILY_VALUES',  ','.join(cases_daily))
	template = template.replace('DEATHS_DAILY_VALUES', ','.join(deaths_daily))

	template = template.replace('LABELS_DAILY',        ','.join(labels_daily).replace('"', ''))
	template = template.replace('LABELS_CUMUL',        ','.join(labels_cumul).replace('"', ''))

	filepath = '%s/%s.html' % (htmldir, cc_daily.lower())
	write_file(filepath, template)

""" Generate HTML file for index.
"""
def generate_html_index(ccs, template_file='templates/index.html'):

	now = datetime.now().strftime('%A %d %B - %H:%M:%S')
	template = read_file(template_file).replace('UPDATED', now)

	filepath = '%s/index.html' % htmldir
	write_file(filepath, template)

""" Generate all HTML files.
"""
def generate_html(jsonfile):

	dataset = parse_json(jsonfile)
	daily   = parse_daily(dataset)
	cumul   = parse_cumulative(daily)

	for cc in daily:
		generate_html_country(daily[cc], cumul[cc])

	generate_html_index(list(daily))

""" Download supplied URL to location.
"""
def download(filename, url):

	response = requests.get(url)
	response.raise_for_status()

	data = response.content

	# Strip UTF-8 BOM if present
	if data.startswith(b'\xef\xbb\xbf'):
		data = data[3:]

	# Compute new checksum
	new_checksum = 'SHA512:%s' % hashlib.sha512(data).hexdigest()

	checkfile = filename + '.checksum'
	if os.path.exists(checkfile):
		old_checksum = read_file(checkfile)
		if old_checksum == new_checksum:
			return False

	fout = open(filename, 'wb')
	fout.write(data)
	fout.close()

	fout = open(filename + '.checksum', 'w')
	fout.write(new_checksum)
	fout.close()

	return True

""" Main entry point.
"""
def main():

	mkdir(jsondir)
	mkdir(htmldir)

	import shutil
	shutil.copy('templates/charts.js', htmldir)

	today = datetime.now().strftime('%Y%m%d')
	filepath = '%s/%s' % (jsondir, today)

	json_status = False

	try:
		json_status = download(filepath + '.json', json_url)

	except Exception as err:
		print(err)
		print(traceback.format_exc())

	if json_status or '-f' in sys.argv or '--force' in sys.argv:
		generate_html(filepath + '.json')

	else:
		print('Data already up-to-date, quitting.', file=sys.stdout)

if __name__ == '__main__':
	main()
