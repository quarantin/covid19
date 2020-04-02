#!/usr/bin/env python3

import os
import sys
import json
import shutil
import hashlib
import requests
import traceback
from datetime import datetime

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

DEBUG = False

ENCODING_ERRORS = {
	'Ã§a': 'ç',
}

def download(filename, url):

	print('DOWNLOAD: %s' % url)

	response = requests.get(url)
	response.raise_for_status()

	data = response.content
	if data.startswith(b'\xef\xbb\xbf'):
		data = data[3:]

	new_checksum = 'SHA512:%s' % hashlib.sha512(data).hexdigest()
	try:
		fin = open(filename + '.checksum', 'r')
		old_checksum = fin.read()
		fin.close()

		if old_checksum == new_checksum:
			return False
	except:
		pass

	fout = open(filename, 'wb')
	fout.write(data)
	fout.close()

	fout = open(filename + '.checksum', 'w')
	fout.write(new_checksum)
	fout.close()

	return True

def accumulate(data):

	cumul = {}

	for cc, country_data in data.items():

		if cc == 'total':
			continue

		if cc not in cumul:
			cumul[cc] = {}

		cases = 0
		deaths = 0
		population = 0

		for date, item in sorted(country_data.items(), key=lambda x: x[0]):

			cases += item['cases']
			deaths += item['deaths']
			population += item['population']

			cumul[cc][date] = {
				'country': item['country'],
				'cases': cases,
				'deaths': deaths,
				'population': population,
			}

	return cumul

def extract_data(data, row):

	if type(row) is tuple:

		day        = int(row[1])
		month      = int(row[2])
		year       = int(row[3])
		cases      = int(row[4])
		deaths     = int(row[5])
		country    = row[6]
		cc         = row[7]
		population = row[9] and int(row[9]) or 0

	elif type(row) is dict:

		day        = int(row['day'])
		month      = int(row['month'])
		year       = int(row['year'])
		cases      = int(row['cases'])
		deaths     = int(row['deaths'])
		country    = row['countriesAndTerritories']
		cc         = row['geoId']
		population = row['popData2018'] and int(row['popData2018']) or 0

	else:
		raise Exception('Unsupported type for input: %s' % type(row))


	if 'ww' not in data:
		data['ww'] = {}

	cc = cc.lower()
	if cc not in data:
		data[cc] = {}

	date = datetime(year=int(year), month=int(month), day=int(day)).strftime('%Y-%m-%d')
	if date not in data[cc]:
		data[cc][date] = {
			'country': country,
			'cases': cases,
			'deaths': deaths,
			'population': population,
		}

	if date not in data['ww']:
		data['ww'][date] = {
			'country': 'Worldwide',
			'cases': 0,
			'deaths': 0,
			'population': 0,
		}

	data['ww'][date]['cases'] += cases
	data['ww'][date]['deaths'] += deaths
	data['ww'][date]['population'] += population

	if 'total' not in data:
		data['total'] = {
			'country': 'Total',
			'cases': 0,
			'deaths': 0,
			'population': 0,
		}

	data['total']['cases'] += cases
	data['total']['deaths'] += deaths
	data['total']['population'] += population


def parse_xlsx(filename):

	data = {}

	import openpyxl
	workbook = openpyxl.load_workbook(filename)
	for sheet in workbook:
		rows = iter(sheet.values)
		next(rows)
		for row in rows:
			extract_data(data, row)

	return data, accumulate(data)

def parse_json(filename):

	data = {}

	fin = open(filename, 'r')
	jsondata = json.loads(fin.read())
	fin.close()

	for row in jsondata['records']:
		extract_data(data, row)

	return data, accumulate(data)

def plot(covid19_country, covid19_data, log=False):

	dates = []
	cases = []
	deaths = []

	max_cases = 0
	country_name = None
	country_pop = 'Unknown'
	for date, entry in sorted(list(covid19_data.items()), key=lambda x: x[0], reverse=False):

		# Ignore days with no case and no death
		#if entry['cases'] == 0 and entry['deaths'] == 0:
		#	continue

		if entry['cases'] > max_cases:
			max_cases = entry['cases']

		dates.append('\n'.join(date.split('-')))
		cases.append(entry['cases'])
		deaths.append(entry['deaths'])
		if not country_name:
			country_name = entry['country'].replace('_', ' ')
			country_pop = entry['population']

	print("Plotting %s" % country_name, file=sys.stdout)
	mpl.rcParams.update({ 'font.size': 7 })
	if covid19_country == 'ww':
		plt.figure(figsize=(24.0, 9.0))
	else:
		plt.figure(figsize=(18.0, 9.0))

	plt.suptitle(log and 'Cumulative' or 'Per Day', fontsize=26)
	plt.title('Population: %s' % '{:,d}'.format(country_pop).replace(',', ' '), fontweight='bold')

	plt.xlabel('Days', fontsize=20)
	plt.ylabel('Count', fontsize=20)

	step = 100
	if covid19_country == 'ww':
		step = 10000
	elif covid19_country == 'ch':
		step = 1000
	elif max_cases < step:
		step = 10

	div, rem = divmod(max_cases, step)
	limit = div * step
	if rem > 0:
		limit += step

	for y in range(0, limit, step):
		plt.axhline(y=y, color='0.65', linewidth=0.4)

	filename = '%s.png' % covid19_country
	if log is True:
		plt.yscale('log')
		filename = '%s-log.png' % covid19_country

	cases_bar = plt.bar(dates, cases, color='blue', width=0.8, align='center')
	deaths_bar = plt.bar(dates, deaths, color='red', width=0.6, align='center')

	for cases_rect, deaths_rect in zip(cases_bar, deaths_bar):

		cases_x = cases_rect.get_x()
		cases_w = cases_rect.get_width()
		cases_h = cases_rect.get_height()

		deaths_x = deaths_rect.get_x()
		deaths_w = deaths_rect.get_width()
		deaths_h = deaths_rect.get_height()

		death_rate = -1
		if cases_h != 0:
			death_rate = (deaths_h / cases_h) * 100

		cases_repr = '%d' % int(cases_h)
		deaths_repr = '%d' % int(deaths_h)

		death_rate_repr = death_rate == -1 and '-' or '%.01f%%' % death_rate
		if death_rate != -1 and death_rate - int(death_rate) == 0:
			death_rate_repr = '%d%%' % death_rate

		plt.text(cases_x  + cases_w  / 2.0, cases_h,      cases_repr,  ha='center', va='bottom',    color='blue')
		plt.text(deaths_x + deaths_w / 2.0, deaths_h,    deaths_repr,  ha='center', va='bottom',    color='red',   fontweight='bold')
		#plt.text(cases_x  + cases_w  / 2.0, cases_h, death_rate_repr,  ha='center', va='bottom', color='black', fontweight='bold', fontsize=7)


	red_patch = mpatches.Patch(color='red', label='Deaths')
	blue_patch = mpatches.Patch(color='blue', label='Cases')

	plt.legend(handles=[ blue_patch, red_patch ], loc='upper left')

	plt.savefig(filename)
	#plt.show()
	plt.close('all')
	return filename, country_name

def write_html_header(fout, page_title):

	fout.write('<html>\n')
	fout.write('\t<head>\n')
	fout.write('\t\t<meta charset="UTF-8">\n')
	fout.write('\t\t<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate" />\n')
	fout.write('\t\t<meta http-equiv="Pragma" content="no-cache" />\n')
	fout.write('\t\t<meta http-equiv="Expires" content="0" />\n')
	fout.write('\t\t<style>\n')
	fout.write('div.cell {\n')
	fout.write('  width: 200px;\n')
	fout.write('  max-width: 11%;\n')
	fout.write('  display: table-cell;\n')
	fout.write('}\n')
	fout.write('\t\t</style>\n')
	fout.write('\t</head>\n')
	fout.write('\t<body>\n')
	fout.write('\t\t<h1>%s</h1>\n' % page_title)

def write_html_footer(fout):

	fout.write('\t</body>\n')
	fout.write('</html>\n')
	fout.close()

def generate_html_country(country, country_name):

	cur_filename = '%s.html'     % country
	tmp_filename = '%s.html.new' % country

	fout = open(tmp_filename, 'w')

	for_str = country != 'ww' and 'for ' or ''
	write_html_header(fout, 'COVID-19 Geographic Distribution %s%s' % (for_str, country_name))

	png1 = '%s.png' % country
	png2 = '%s-log.png' % country

	png1_latest = datetime.fromtimestamp(os.stat(png1).st_mtime).strftime('%Y%m%d%H%M%S')
	png2_latest = datetime.fromtimestamp(os.stat(png2).st_mtime).strftime('%Y%m%d%H%M%S')

	fout.write('\t\t<div>\n')
	fout.write('\t\t\t<img src="%s?%s"/>\n' % (png1, png1_latest))
	fout.write('\t\t\t<img src="%s?%s"/>\n' % (png2, png2_latest))
	fout.write('\t\t</div>\n')

	write_html_footer(fout)

	os.rename(tmp_filename, cur_filename)

def get_country_list(countries):

	lines = []
	visited = {}

	for code, country in sorted(countries, key=lambda x: x[1]):

		for error, replace in ENCODING_ERRORS.items():
			if error in country:
				country = country.replace(error, replace)

		letter = country[0].upper()
		if letter not in visited:
			visited[letter] = True
			lines.append('\t\t\t\t\t</br>\n')
			lines.append('\t\t\t\t\t<h3>%s</h3>\n' % letter)

		lines.append('\t\t\t\t\t<a href="/covid19/%s.html">%s</a><br>\n' % (code, country))

	return lines[1:]

def generate_html(countries):

	github_url = 'https://github.com/quarantin/covid19'
	source_url = 'https://www.ecdc.europa.eu/en/publications-data/download-todays-data-geographic-distribution-covid-19-cases-worldwide'

	cur_filename = 'index.html'
	tmp_filename = 'index.html.new'

	fout = open(tmp_filename, 'w')

	write_html_header(fout, 'COVID-19 Geographic Distribution Worldwide')

	fout.write('\t\t<div id="info">\n')
	fout.write('\t\t\tSource: <a href="%s">%s</a></br>\n' % (source_url, source_url))
	fout.write('\t\t\tCode source: <a href="%s">%s</a></br>\n' % (github_url, github_url))
	fout.write('\t\t\tUpdated: <b>%s</b>\n' % datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
	fout.write('\t\t</div><!-- div#info -->\n')
	fout.write('\t\t<div id="content">\n')
	fout.write('\t\t\t<h2>Countries</h2>\n')

	fout.write('\t\t\t<div style="display: table-row">\n')

	i = 0
	lines = get_country_list(countries)
	for line in lines:

		if i % 30 == 0:
			if i != 0:
				fout.write('\t\t\t\t</div><!-- div.cell -->\n')
			fout.write('\t\t\t\t<div class="cell">\n')

		fout.write(line)
		i += 1

	fout.write('\t\t\t</div><!-- div.table-row -->\n')

	for code, country in countries:
		generate_html_country(code, country)

	fout.write('\t\t</div><!-- div#content -->\n')

	write_html_footer(fout)

	os.rename(tmp_filename, cur_filename)

def dummy_plot(code, data, log=False):
	for date, item in data.items():
		return None, item['country'].replace('_', ' ')

def process(covid19_data, log=False, debug=False):

	toc = []
	items = []

	for code, data in covid19_data.items():

		if code == 'total':
			continue

		plotfn = debug and dummy_plot or plot
		plotfile, country = plotfn(code, data, log=log)

		toc.append((code, country))

		items.append((code, country, plotfile))

	return toc, items

if __name__ == '__main__':

	today = datetime.now().strftime('%Y-%m-%d')
	filename = 'COVID-19-geographic-disbtribution-worldwide-%s' % today
	json_url = 'https://opendata.ecdc.europa.eu/covid19/casedistribution/json/'
	xlsx_url = 'https://www.ecdc.europa.eu/sites/default/files/documents/' + filename + '.xlsx'

	try:
		json_status = download(filename + '.json', json_url)
		if not json_status:
			print('No update found for JSON.', file=sys.stdout)

		xlsx_status = download(filename + '.xlsx', xlsx_url)
		if not xlsx_status:
			print('No update found for XLSX.', file=sys.stdout)

		if not json_status and not xlsx_status:
			print('No updates found.', file=sys.stdout)
			sys.exit(0)

	except Exception as err:
		print('File not found, quitting.', file=sys.stdout)
		sys.exit(0)

	outdir = 'html'
	if not os.path.exists(outdir):
		os.mkdir(outdir, mode=0o755)

	if json_status and xlsx_status:
		covid19_data,  covid19_data_cumul  = parse_json(filename + '.json')
		covid19_data2, covid19_data_cumul2 = parse_xlsx(filename + '.xlsx')

		covid19_data.update(covid19_data2)
		covid19_data_cumul.update(covid19_data_cumul2)

	elif json_status:
		covid19_data, covid19_data_cumul = parse_json(filename + '.json')

	elif xlsx_status:
		covid19_data, covid19_data_cumul = parse_xlsx(filename + '.xlsx')

	else:
		raise Exception('This should never happen')

	os.chdir(outdir)

	if DEBUG:
		toc, items = process(covid19_data,       log=False, debug=True)

	else:
		toc, items = process(covid19_data,       log=False)
		toc, items = process(covid19_data_cumul, log=True)

	generate_html(toc)
