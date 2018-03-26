#TODO: remove this and print statements
import sys
# print('this', file=sys.stderr)

from backend import Call, CallSet
import datetime
from operator import attrgetter, methodcaller
from mapbox import Geocoder
from collections import Counter
from csv import reader as csvReader
import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go
from dash.dependencies import Input, Output

DATA_PATH = 'sfpd_dispatch_data_subset.csv'

# contains zipcodes in sorted order and their populations
POPULATIONDATA_PATH = '2010+Census+Population+By+Zipcode+(ZCTA).csv'

MAPBOX_APITOKEN = 'pk.eyJ1IjoibWFzYWxhbXVuY2giLCJhIjoiY2plb3Z3eGlxMDdtZTJ4dGhqcTdxbzR4ZyJ9.RMPRt_WY-z-KEmW2nxW-cw'

# restricts how many characters the user can put into a textbox
MAX_INPUTLENGTH = 3000

WEBAPP_TITLE = 'SF Emergency Call Data Visualizations'
CSS_URL = 'https://codepen.io/chriddyp/pen/bWLwgP.css'

# unique string IDs for UI elements
RESPONSETIMEPICKER_ID = '0'
ADDRESSINPUT_ID = '1'
TIMEINPUT_ID = '2'
PERCAPITACHECKBOX_ID = '3'
UNITPROBABILITIES_ID = '4'
RESPONSETIMESLIDER_ID = '5'
RESPONSETIMEZIP_ID = '6'
RESPONSETIMEUNIT_ID = '7'
RESPONSETIMEMAP_ID = '8'
EMERGENCYCHECKBOX_ID = '9'
FREQUENCYTIMEGRAPH_ID = '10'

# defines the appearance of bars in bar graphs
BARGRAPH_MARKER = {
	'color' : 'rgba(246, 78, 139, 0.6)',
	'line' : {
		'color' : 'rgba(246, 78, 139, 1.0)',
		'width' : 3,
		}
	}

BARGRAPH_XAXISFONTSIZE = 12

INITIAL_INPUTS = {
	RESPONSETIMEPICKER_ID : 'dispatchTimedelta',
	ADDRESSINPUT_ID : '1100 Fillmore St',
	TIMEINPUT_ID : '1:00pm',
	PERCAPITACHECKBOX_ID : [], # doesn't show Per capita by default
	RESPONSETIMESLIDER_ID : [2, 22], # 2am-10pm
	EMERGENCYCHECKBOX_ID : ['emergency', 'non-emergency'],
}

# defines the non-interactive aspects of the web app
INITIAL_LAYOUT = html.Div(children=[

	dcc.Markdown('''

# About

Visualizations of emergency call data from the
San Francisco Fire Department, built in 14 days for a
[MindSumo challenge](https://www.mindsumo.com/contests/sfpd-dispatch).
See the source code [here](https://github.com/MasalaMunch/emergencycallsMindSumo).

		'''),

	dcc.Markdown('''

# Response Times

Shows response times on a heatmap, by ZIP code, and by unit type.
Use the "Include..." checkboxes to customize which calls are shown.
Use the "Minutes until..." options to customize what measurement of response time is used.
Use the blue range slider to customize the time of day.
On the heatmap, the ZIP codes are listed on the left.
To hide or show a ZIP code, click it once.
To isolate a ZIP code, click it twice.

		'''),

	dcc.Checklist(
		id=EMERGENCYCHECKBOX_ID,
		options=[
	        {'label': 'Include Emergencies', 'value': 'emergency'},
	        {'label': 'Include Non-Emergencies', 'value': 'non-emergency'},
		],
		values=INITIAL_INPUTS[EMERGENCYCHECKBOX_ID],
		),

	dcc.RadioItems(
		id=RESPONSETIMEPICKER_ID,
		options=[
	        {'label': 'Minutes until Dispatch', 'value': 'dispatchTimedelta'},
	        {'label': 'Minutes until Departure', 'value': 'departureTimedelta'},
	        {'label': 'Minutes until Arrival', 'value': 'arrivalTimedelta'},
		],
		value=INITIAL_INPUTS[RESPONSETIMEPICKER_ID],
		),

	html.Div(children=[

		dcc.RangeSlider(
			id=RESPONSETIMESLIDER_ID,
			marks= dict(
						{0:'12am',12:'12pm',24:'12am'}.items()
						| {i:'{}am'.format(i) for i in range(2,12,2)}.items()
						| {j:'{}pm'.format(j-12) for j in range(14,24,2)}.items()
						),
			count=1,
			min=0,
			max=24,
			step=0.01,
			value=INITIAL_INPUTS[RESPONSETIMESLIDER_ID],
			),

		# adds a blank space to prevent rangeSlider marks
		# from being cut off by the element below
		dcc.Markdown('''

&nbsp;  

			''')
		], style={'width':'96%'}),
		# 'width' prevents the rangeslider's rightmost mark
		# from being cut off

	dcc.Graph(
		id=RESPONSETIMEMAP_ID,
		config=dict(displayModeBar=False),
		),

	dcc.Graph(
		id=RESPONSETIMEZIP_ID,
		config=dict(displayModeBar=False),
		),

	dcc.Graph(
		id=RESPONSETIMEUNIT_ID,
		config=dict(displayModeBar=False),
		),

	dcc.Markdown('''

# Call Predictor

Given an address and a time, tries to predict
what unit type will need to be dispatched. If not
enough data exists near the address, it looks
at the entire San Francisco area.

		'''),

	dcc.Input(
		id=ADDRESSINPUT_ID,
		autocomplete=True,
		inputmode='verbatim',
		maxlength=MAX_INPUTLENGTH,
		placeholder='Enter an address',
		size=40,
		spellcheck=True,
		type="text",
		value=INITIAL_INPUTS[ADDRESSINPUT_ID],
		),

	dcc.Input(
		id=TIMEINPUT_ID,
		autocomplete=True,
		inputmode='verbatim',
		maxlength=MAX_INPUTLENGTH,
		placeholder='Enter a time',
		size=40,
		spellcheck=False,
		type="text",
		value=INITIAL_INPUTS[TIMEINPUT_ID],
		),

	dcc.Graph(
		id=UNITPROBABILITIES_ID,
		config=dict(displayModeBar=False),
		),

	dcc.Markdown('''

# Preparing for the Future

For each ZIP code in the dataset, shows calls per day over time.
The ZIP codes are listed to the right of the graph.
To hide or show a ZIP code, click it once.
To isolate a ZIP code, click it twice.
To instead view calls *per capita* per day, click the "Per capita" checkbox
(population data is from the 2010 census).

		'''),

	dcc.Checklist(
		id=PERCAPITACHECKBOX_ID,
		options=[
	        {'label': 'Per capita', 'value': 'perCapita'},
		],
		values=INITIAL_INPUTS[PERCAPITACHECKBOX_ID],
		),

	dcc.Graph(
		id=FREQUENCYTIMEGRAPH_ID,
		config=dict(displayModeBar=False),
		),

	dcc.Markdown('''

# Findings & Limitations

When looking at response times for emergencies,
I noticed that "Investigation" and "Support" units
have significantly higher dispatch, departure, and
arrival times than their counterparts, which implies
that there might be a shortage of these unit types.

Northeastern San Francisco tends to
experience greater call volume, both in an absolute
sense and per capita, than southwestern San Fransisco,
which implies that higher population density may correlate
with an increased propensity for fires and other emergencies.
It also tends to have shorter arrival times than
southwestern San Fransisco, which suggests that the
facilities from which units depart (firehouses, police stations,
etc) are concentrated in the northeast.

The given dataset only spans 10 days, so identifying long-term trends
(such as increasing or decreasing call frequency in certain areas)
proved to be futile.

		'''),

	])

def parseEmergencyTypes(emergencyTypes:list) -> list:

	out = []
	if 'emergency' in emergencyTypes:
		# the dataset uses 3 to represent emergencies
		out.append(3)
	if 'non-emergency' in emergencyTypes:
		# the dataset uses 2 to represent non-emergencies
		out.append(2)
	return out

def parsePerCapitaCheckbox(perCapitaCheckbox:list) -> bool:

	return 'perCapita' in perCapitaCheckbox

def parseTimeInput(time:str) -> datetime.time:

	time = ''.join(time.split()) # remove whitespace
	amORpm = time[-2:].lower()
	hours, mins = [ int(s) for s in time[:-2].split(':') ]
	# converts from civilian time to military time
	if hours == 12:
		if amORpm == 'am':
			hours -= 12
	elif amORpm == 'pm':
		hours += 12
	return datetime.time(hour=hours, minute=mins)

def parseAddressInput(address:str, geocoder=Geocoder(access_token=MAPBOX_APITOKEN),
	boundingBox=[-122.6, 37.7, -122.3, 37.9]) -> tuple:

	geocoderResponse = geocoder.forward(
		address,
		limit=1, # how many results it returns
		types=['address'],
		bbox=boundingBox,
		)
	mapboxFeature = geocoderResponse.geojson()['features'][0]
	info = mapboxFeature['place_name'].split(', ')
	zipcode = int(info[2].split()[-1])
	friendlyName = info[0] + ', ' + str(zipcode)

	return (zipcode, friendlyName)

def parseTimeOfDayRangeSlider(hourRange:list) -> list:

	# datetime.time objects' hour fields must be < 24
	if hourRange[1] == 24:
		hourRange[1] -= 1/7200 # subtracts half a second

	mins = [(h-int(h))*60 for h in hourRange]
	secs = [(m-int(m))*60 for m in mins]

	return [ datetime.time(hour=int(h), minute=int(m), second=int(s))
							for h,m,s in zip(hourRange,mins,secs) ]

def parseResponseTimeTypePicker(timeType:str) -> tuple:

	if timeType == 'dispatchTimedelta':
		minMinutesUsually, maxMinutesUsually = 0, 2
	elif timeType == 'departureTimedelta':
		minMinutesUsually, maxMinutesUsually = 0, 5
	elif timeType == 'arrivalTimedelta':
		minMinutesUsually, maxMinutesUsually = 0, 20

	return (attrgetter(timeType), minMinutesUsually, maxMinutesUsually)

def listCalls(csvPath:str) -> list:

	calls = []

	with open(csvPath) as dataFile:

		dataReader = csvReader(dataFile, dialect='excel')

		for i,splitRow in enumerate(dataReader):

			if i == 0:
				Call.setSchema(splitRow)
			else:
				calls.append(Call(splitRow))

	return calls

def buildUnitTypes(calls:list) -> dict:

	unitTypes = { 'all':CallSet() }

	for call in calls:

		unitTypes['all'].add(call)

		if call.unitType not in unitTypes:

			unitTypes[call.unitType] = CallSet()

		unitTypes[call.unitType].add(call)

	return unitTypes

def buildZipcodes(calls:list) -> dict:

	zipcodes = { 'all':CallSet() }
	keys = []
	for call in calls:

		zipcodes['all'].add(call)

		if call.zipcode not in zipcodes:

			zipcodes[call.zipcode] = CallSet()
			keys.append(call.zipcode)

		zipcodes[call.zipcode].add(call)

	# adds population data to the CallSets
	keys.sort()
	currentKeyIndex = 0
	totalPopulation = 0
	with open(POPULATIONDATA_PATH) as dataFile:

		dataReader = csvReader(dataFile, dialect='excel')

		for i,splitRow in enumerate(dataReader):

			if i == 0:
				continue
			if currentKeyIndex >= len(keys):
				break
			if int(splitRow[0]) == keys[currentKeyIndex]:
				zipcodes[keys[currentKeyIndex]].setPopulation(int(splitRow[1]))
				totalPopulation += int(splitRow[1])
				currentKeyIndex += 1

	zipcodes['all'].setPopulation(totalPopulation)

	return zipcodes

calls = listCalls(DATA_PATH)
zipcodes = buildZipcodes(calls)
unitTypes = buildUnitTypes(calls)
app = dash.Dash()
server = app.server
app.layout = INITIAL_LAYOUT
app.css.append_css({'external_url':CSS_URL})
app.title = WEBAPP_TITLE

# these functions define the interactive aspects of the web app

@app.callback(
	Output(RESPONSETIMEUNIT_ID, 'figure'),
	[
	Input(RESPONSETIMESLIDER_ID, 'value'),
	Input(RESPONSETIMEPICKER_ID, 'value'),
	Input(EMERGENCYCHECKBOX_ID, 'values'),
		]
	)
def updateUnitTypeAvgTimeGraph(hourRange:list, timeType:str, emergencyTypes:list):

	startTime, endTime = parseTimeOfDayRangeSlider(hourRange)
	timeGetter = parseResponseTimeTypePicker(timeType)[0]
	priorities = parseEmergencyTypes(emergencyTypes)

	x = sorted([ key for key in unitTypes ])
	y = [ unitTypes[key].getAvgTime(timeGetter, startTime, endTime, 
			prioritiesToInclude=priorities).total_seconds()/60.0
			for key in x ]

	newX = []
	for string in x:
		if string != 'all':
			string = string.title()
		newX.append(string)
	x = newX

	return go.Figure(
		data=[
			go.Bar(
				x=x,
				y=y,
				marker=BARGRAPH_MARKER,
				)
			],
		layout=go.Layout(
			title='Average Minutes until ' + timeType[:-9].title(),
			xaxis=dict(
				title='Unit Type',
				titlefont=dict(
					size=BARGRAPH_XAXISFONTSIZE,
					),
				type='category',
				),
			)
		)

@app.callback(
	Output(RESPONSETIMEZIP_ID, 'figure'),
	[
	Input(RESPONSETIMESLIDER_ID, 'value'),
	Input(RESPONSETIMEPICKER_ID, 'value'),
	Input(EMERGENCYCHECKBOX_ID, 'values'),
		]
	)
def updateZipAvgTimeGraph(hourRange:list, timeType:str, emergencyTypes:list):

	startTime, endTime = parseTimeOfDayRangeSlider(hourRange)
	timeGetter = parseResponseTimeTypePicker(timeType)[0]
	priorities = parseEmergencyTypes(emergencyTypes)

	x = sorted([ str(key) for key in zipcodes ])
	y = []
	for e in x:
		if e != 'all':
			e = int(e)
		y.append(zipcodes[e].getAvgTime(timeGetter, startTime, endTime,
			prioritiesToInclude=priorities).total_seconds()/60.0)

	return go.Figure(
		data=[
			go.Bar(
				x=x,
				y=y,
				marker=BARGRAPH_MARKER,
				)
			],
		layout=go.Layout(
			title='Average Minutes until ' + timeType[:-9].title(),
			xaxis=dict(
				title='ZIP Code',
				titlefont=dict(size=BARGRAPH_XAXISFONTSIZE),
				type='category',
				),
			)
		)

@app.callback(
	Output(RESPONSETIMEMAP_ID, 'figure'),
	[
	Input(RESPONSETIMESLIDER_ID, 'value'),
	Input(RESPONSETIMEPICKER_ID, 'value'),
	Input(EMERGENCYCHECKBOX_ID, 'values'),
		]
	)
def updateResponseTimeMap(hourRange:list, timeType:str, emergencyTypes:list):

	startTime, endTime = parseTimeOfDayRangeSlider(hourRange)
	timeGetter, minMinutesUsually, maxMinutesUsually = parseResponseTimeTypePicker(timeType)
	priorities = parseEmergencyTypes(emergencyTypes)

	scatterMapBoxes = []
	for key in zipcodes:

		# prevents duplicate data points
		if key == 'all':
			continue

		lats, lons, times = [], [], []
		for call in zipcodes[key]:
			if call.priority in priorities:
				if call.isInRange(startTime, endTime):
					timeDelta = timeGetter(call)
					if timeDelta is not None:
						lats.append(call.latitude)
						lons.append(call.longitude)
						times.append(timeDelta.total_seconds()/60.0)

		latShifts, lonShifts = Counter(), Counter()
		for i,coord in enumerate(zip(lats,lons)):

			lats[i] += latShifts[coord]
			latShifts[coord] += 0.00001
			lons[i] += lonShifts[coord]
			lonShifts[coord] += 0.00001

		scatterMapBoxes.append(
			go.Scattermapbox(
				name=str(key),
				lat=lats,
				lon=lons,
				hoverinfo='name+text',
				text=times, # show times on hover
				mode='markers',
				marker=dict(
					size=6,
					opacity=0.5,
					color=times,
					colorscale='Bluered',
					cmin=minMinutesUsually,
					cmax=maxMinutesUsually,
					showscale=True,
					colorbar=dict(
						tickmode='array',
						tickvals=[minMinutesUsually,
							maxMinutesUsually/2, maxMinutesUsually],
						ticktext=[str(minMinutesUsually),
							str(maxMinutesUsually/2), str(maxMinutesUsually)+'+'],
						),
					),
				)
			)

	scatterMapBoxes.sort(key=attrgetter('name'))

	return go.Figure(
		data=[
			# dummy trace to indicate what the numbers
			# in the legend mean
			go.Scattermapbox(
				name='ZIP code',
				lat=[0],
				lon=[0],
				mode='markers',
				marker=dict(
					color='#ffffff'
					),
				),
			# dummy trace whose name is blank name
			# to separate the above dummy trace and
			# the actual traces
			go.Scattermapbox(
				name=' ',
				lat=[0],
				lon=[0],
				mode='markers',
				marker=dict(
					color='#ffffff'
					),
				),
			] + scatterMapBoxes, # the actual traces
		layout=go.Layout(
			title='Minutes until ' + timeType[:-9].title(),
			autosize=True,
			height=750,
			showlegend=True,
			legend=dict(x=-5), # put the zipcodes on the left
			mapbox=dict(
				accesstoken=MAPBOX_APITOKEN,
				center=dict(lat=37.77, lon=-122.44),
				pitch=0,
				zoom=11,
				)
			),
		)

@app.callback(
	Output(UNITPROBABILITIES_ID, 'figure'),
	[Input(ADDRESSINPUT_ID, 'value'), Input(TIMEINPUT_ID, 'value')],
	)
def updateUnitProbabilities(address:str, time:str):

	try:
		zipcode, address = parseAddressInput(address)
		time = parseTimeInput(time)
		probabilities = zipcodes[zipcode].getUnitTypeProbabilities(time)
	except Exception as e:
		print(str(e), file=sys.stderr)
		graphName = "Error: Couldn't parse input."
		probabilities = []
	else:
		graphName = 'Most Likely Unit Types for '
		# if no data was found nearby, look in all of San Francisco over a smaller time interval
		if len(probabilities) == 0:
			address = 'San Francisco'
			probabilities = zipcodes['all'].getUnitTypeProbabilities(time, dt=datetime.timedelta(minutes=5))
		graphName += address
		graphName += ' at ' + str(time)[:-3]

	return go.Figure(
		data=[
			go.Bar(
				# shows unit types from most likely -> least likely
				y=[ d['type'].title() for d in probabilities[::-1] ],
				x=[ d['howLikely'] for d in probabilities[::-1] ],
				orientation='h',
				marker=BARGRAPH_MARKER,
				)
			],
		layout=go.Layout(
			title=graphName,
			xaxis=dict(range=[0,1]), # probabilities range from 0 to 1
			)
		)

@app.callback(
	Output(FREQUENCYTIMEGRAPH_ID, 'figure'),
	[Input(PERCAPITACHECKBOX_ID, 'values')]
	)
def updateFrequencyTimeGraph(perCapita:list):

	perCapitaBool = parsePerCapitaCheckbox(perCapita)

	data = []
	for key in zipcodes:

		zipcode = zipcodes[key]
		population = zipcode.population if perCapitaBool else 1
		callsGroupedByDate = zipcode.getCallsGroupedByDate()

		data.append(
			go.Scatter(
				x=[ d['date'] for d in callsGroupedByDate ],
				y=[ len(d['calls'])/population for d in callsGroupedByDate ],
				mode='lines', # connect the data points
				name=str(key),
				visible=True if perCapitaBool or key != 'all' else 'legendonly',
				)
			)

	data.sort(key=attrgetter('name'))

	return go.Figure(
		data=data,
		layout=go.Layout(
			autosize=True,
			title='Calls per Capita per Day' if perCapitaBool else 'Calls per Day',
			),
		)

if __name__ == '__main__':

	#TODO: disable debugging for final deployment
	app.run_server(debug=True)