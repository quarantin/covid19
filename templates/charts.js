class MovingAverage {

	constructor(days) {
		this._days = days;
		this._store = [];
	}

	push(item) {
		if (this._store.length >= this._days)
			this._store.shift();
		this._store.push(parseInt(item));
	}

	sum() {
		return this._store.reduce((a, b) => a + b, 0);
	}

	average() {

		//var sum = 0;
		//for (var i = 0; i < this._store.length; i++)
		//	sum += this._store[i];

		return this.sum() / this._days;
	}

	get full() {
		return this._store.length == this._days;
	}
}

function input2array(element) {
	return document.getElementById(element).value.split(',')
}

function generate_trend(values, win, shift) {

	var trend = [];
	var stack = new MovingAverage(win)

	for (var i = 0; i < shift; i++)
		trend.push('0')

	for (var i = 0; i < values.length; i++) {

		if (stack.full)
			trend.push(stack.average());

		stack.push(values[i]);
	}

	return trend;
}

function generate_chart(type, title, win, shift, scale, average) {

	var label = win + ' days moving average';

	var cases = input2array(type + '-cases');
	var deaths = input2array(type + '-deaths');
	var labels = input2array(type + '-labels');

	var datasets = [];

	datasets.push({
		label: 'Cases',
		data: cases,
		backgroundColor: 'rgba(54, 162, 235, 0.2)',
		borderColor: 'rgba(54, 162, 235, 1)',
		borderWidth: 1,
	});

	if (average == true)
		datasets.push({
			label: label,
			data: generate_trend(cases, win, shift),
			backgroundColor: 'rgba(54, 162, 255, 0.2)',
			borderColor: 'rgba(54, 162, 255, 1)',
			type: 'line',
		});

	datasets.push({
		label: 'Deaths',
		data: deaths,
		backgroundColor: 'rgba(235, 54, 54, 0.2)',
		borderColor: 'rgba(235, 54, 54, 1)',
		borderWidth: 1,
	});

	if (average == true)
		datasets.push({
			label: label,
			data: generate_trend(deaths, win, shift),
			backgroundColor: 'rgba(255, 54, 54, 0.2)',
			borderColor: 'rgba(255, 54, 54, 1)',
			type: 'line',
		});

	var ctx = document.getElementById(type + '-canvas').getContext('2d');
	var canvas = new Chart(ctx, {
		type: 'bar',
		data: {
			labels: labels,
			datasets: datasets,
		},
		options: {
			title: {
				display: true,
				text: title + ' View',
			},
			scales: {
				yAxes: [{
					type: scale,
					ticks: {
						beginAtZero: true,
					},
				}],
			},
		},
	});
}

function generateCharts() {
	var win = parseInt(document.getElementById('window').value);
	var shift = parseInt(document.getElementById('shift').value);
	generate_chart('daily', 'Daily',      win, shift, 'linear',      true);
	generate_chart('cumul', 'Cumulative', win, shift, 'logarithmic', false);
}
