#!/usr/bin/env python3

import os
import sys
import traceback
from datetime import datetime

def download_spreadsheet(filename, url):

	import requests
	response = requests.get(url + filename)
	response.raise_for_status()

	fout = open(filename, 'wb')
	fout.write(response.content)
	fout.close()

def accumulate(data):

	accu = {}

	for cc, country_data in data.items():

		if cc == 'total':
			continue

		if cc not in accu:
			accu[cc] = {}

		cases = 0
		deaths = 0

		for date, item in sorted(country_data.items(), key=lambda x: x[0]):

			cases += item['cases']
			deaths += item['deaths']

			accu[cc][date] = {
				'country': item['country'],
				'cases': cases,
				'deaths': deaths,
			}

	return accu

def parse_spreadsheet(filename):

	data = {}

	import openpyxl
	workbook = openpyxl.load_workbook(filename)
	for sheet in workbook:
		rows = iter(sheet.values)
		next(rows)
		for row in rows:

			day     = row[1]
			month   = row[2]
			year    = row[3]
			cases   = row[4]
			deaths  = row[5]
			country = row[6]
			cc      = row[7]

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
				}

			if date not in data['ww']:
				data['ww'][date] = {
					'country': 'Worldwide',
					'cases': 0,
					'deaths': 0,
				}

			data['ww'][date]['cases'] += cases
			data['ww'][date]['deaths'] += deaths

			if 'total' not in data:
				data['total'] = {
					'country': 'Total',
					'cases': 0,
					'deaths': 0,
				}

			data['total']['cases'] += cases
			data['total']['deaths'] += deaths

	return data, accumulate(data)

def plot(covid19_country, covid19_data, log=False):

	import matplotlib as mpl
	import matplotlib.pyplot as plt
	import matplotlib.patches as mpatches

	dates = []
	cases = []
	deaths = []

	letter = covid19_country[0].lower()
	if not os.path.exists(letter):
		os.mkdir(letter)

	max_cases = 0
	country_name = None
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

	print("Plotting %s" % country_name, file=sys.stdout)
	mpl.rcParams.update({ 'font.size': 7 })
	if covid19_country == 'ww':
		plt.figure(figsize=(24.0, 9.0))
	else:
		plt.figure(figsize=(14.0, 9.0))

	plt.suptitle(log and 'Accumulated' or 'Per Day', fontsize=26)

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

		if abs(cases_h - deaths_h) < 50:
			cases_repr = '%d   ' % int(cases_h)
			deaths_repr = '   %d' % int(deaths_h)
		else:
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

	filename = '%s/%s.png' % (letter, covid19_country)
	if log is True:
		plt.yscale('log')
		filename = '%s/%s-log.png' % (letter, covid19_country)

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
	fout.write('\t</head>\n')
	fout.write('\t<body>\n')
	fout.write('\t\t<h1>%s</h1>\n' % page_title)

def write_html_footer(fout):

	fout.write('\t</body>\n')
	fout.write('</html>\n')
	fout.close()

def generate_html_country(country, country_name):

	letter = country[0].lower()

	cur_filename = '%s/%s.html'     % (letter, country)
	tmp_filename = '%s/%s.html.new' % (letter, country)

	fout = open(tmp_filename, 'w')

	for_str = country != 'ww' and 'for ' or ''
	write_html_header(fout, 'COVID-19 Geographic Distribution %s%s' % (for_str, country_name))

	fout.write('\t\t<div>\n')
	fout.write('\t\t\t<img src="%s.png"/>\n' % country)
	fout.write('\t\t\t<img src="%s-log.png"/>\n' % country)
	fout.write('\t\t</div>\n')

	write_html_footer(fout)

	os.rename(tmp_filename, cur_filename)

def generate_html(toc, url):

	github_url = 'https://github.com/quarantin/covid19'

	cur_filename = 'index.html'
	tmp_filename = 'index.html.new'

	fout = open(tmp_filename, 'w')

	write_html_header(fout, 'COVID-19 Geographic Distribution Worldwide')

	fout.write('\t\t<div id="info">\n')
	fout.write('\t\t\tSource: <a href="%s">%s</a></br>\n' % (url, url))
	fout.write('\t\t\tCode source: <a href="%s">%s</a></br>\n' % (github_url, github_url))
	fout.write('\t\t\tUpdated: <b>%s</b>\n' % datetime.now().strftime('%Y-%m-%d'))
	fout.write('\t\t</div><!-- div#info -->\n')
	fout.write('\t\t<div id="content">\n')
	fout.write('\t\t\t<h2>Countries</h2>\n')

	for code, country in toc:
		href = '%s/%s.html' % (code[0].lower(), code)
		fout.write('\t\t\t<a href="%s">%s</a></br>\n' % (href, country))
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

	url = 'https://www.ecdc.europa.eu/sites/default/files/documents/'
	filename = 'COVID-19-geographic-disbtribution-worldwide.xlsx'

	try:
		download_spreadsheet(filename, url)

	except Exception as err:
		print(err, file=sys.stderr)
		print(traceback.format_exc())
		sys.exit(0)

	covid19_data, covid19_data_accu = parse_spreadsheet(filename)

	toc, items = process(covid19_data,      log=False)
	toc, items = process(covid19_data_accu, log=True)

	generate_html(toc, url + filename)
