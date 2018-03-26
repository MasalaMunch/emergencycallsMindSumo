import datetime
from collections import Counter
from operator import attrgetter

ARBITRARY_DATE = datetime.date.today()
LOCAL_TIMEINTERVAL = datetime.timedelta(minutes=15)

class Call:

	@classmethod
	def setSchema(cls, splitCsvRow:list):

		cls.schema = { string:index for index,string in enumerate(splitCsvRow) }

	def __init__(self, splitCsvRow:list):

		self.priority = int(splitCsvRow[Call.schema['final_priority']])
		self.unitType = splitCsvRow[Call.schema['unit_type']]
		self.zipcode = int(splitCsvRow[Call.schema['zipcode_of_incident']])
		self.latitude = float(splitCsvRow[Call.schema['latitude']])
		self.longitude = float(splitCsvRow[Call.schema['longitude']])
		self.time = Call.getDatetime(splitCsvRow[Call.schema['entry_timestamp']])	
		
		# group dispatch, departure, and arrival timestamps
		times = [ splitCsvRow[Call.schema[s]]
			for s in ('dispatch_timestamp', 'response_timestamp', 'on_scene_timestamp') ]
		# convert these into timedeltas relative to when the call was received
		for i,stamp in enumerate(times):
			times[i] = Call.getDatetime(stamp) - self.time if stamp != '' else None
		
		self.dispatchTimedelta, self.departureTimedelta, self.arrivalTimedelta = times

	def isInRange(self, rangeStart:datetime.datetime, rangeEnd:datetime.datetime,
		dateOverride=ARBITRARY_DATE, overrideRange=True) -> bool:

		time = self.time

		if dateOverride is not None:

			time = datetime.datetime(dateOverride.year, dateOverride.month, dateOverride.day,
				hour=time.hour, minute=time.minute, second=time.second, microsecond=time.microsecond
				)
			
			if overrideRange:

				rangeStart = datetime.datetime(dateOverride.year, dateOverride.month, dateOverride.day,
					hour=rangeStart.hour, minute=rangeStart.minute, second=rangeStart.second, microsecond=rangeStart.microsecond
					)
				rangeEnd = datetime.datetime(dateOverride.year, dateOverride.month, dateOverride.day,
					hour=rangeEnd.hour, minute=rangeEnd.minute, second=rangeEnd.second, microsecond=rangeEnd.microsecond
					)

		return rangeStart <= time <= rangeEnd

	@staticmethod
	def getDatetime(timestamp:str) -> datetime.datetime:

		date, time = timestamp.split(' ')[:2]
		year, month, day = [ int(s) for s in date.split('-') ]
		hrs, mins, secs =  [ int(float(s)) for s in time.split(':') ]
		return datetime.datetime(year, month, day, hour=hrs, minute=mins, second=secs)

class CallSet:

	def __init__(self):

		self._calls = []
		self._isSortedByTime = True

	def __iter__(self):

		for call in self._calls:
			yield call

	def add(self, call:Call):

		self._calls.append(call)
		self._isSortedByTime = False

	def setPopulation(self, population:int):

		self.population = population

	def _sortByTime(self):

		self._calls.sort(key=attrgetter('time'))
		self._isSortedByTime = True

	def getCallsGroupedByDate(self) -> list:

		if not self._isSortedByTime:
			self._sortByTime()

		try:
			out = [
				{ 'date':self._calls[0].time.date(), 'calls':[] }
			]
		except IndexError: # CallSet is empty
			return []

		for call in self:

			date = call.time.date()

			if date != out[-1]['date']:
				out.append( { 'date':date, 'calls':[] } )

			out[-1]['calls'].append(call)

		return out

	def getAvgTime(self, timeGetter:attrgetter,
		rangeStart:datetime.time, rangeEnd:datetime.datetime,
		prioritiesToInclude=[2,3], dateOverride=ARBITRARY_DATE) -> datetime.timedelta:

		totalTime = datetime.timedelta()
		callCount = 0
		for call in self:
			if call.priority in prioritiesToInclude:
				if call.isInRange(rangeStart, rangeEnd, dateOverride=dateOverride):
					timeDelta = timeGetter(call)
					if timeDelta is not None:
						totalTime = totalTime + timeDelta
						callCount += 1

		return totalTime/callCount if callCount>0 else totalTime

	def getUnitTypeProbabilities(self, time:datetime.time,
		dt=LOCAL_TIMEINTERVAL, dateOverride=ARBITRARY_DATE) -> list:

		rangeStart, rangeEnd = CallSet.getLocalRange(time, dt, dateOverride=dateOverride)
		callCounts, totalCount = Counter(), 0

		for call in self:

			if call.isInRange(rangeStart, rangeEnd,
				dateOverride=dateOverride, overrideRange=False):
				# range dates were already overridden by CallSet.getLocalRange

				callCounts[call.unitType] += 1
				totalCount += 1

		return [ { 'type':unitType, 'howLikely':callCount/totalCount }
			for unitType, callCount in callCounts.most_common() ]

	@staticmethod
	def getLocalRange(time:datetime.datetime, dt:datetime.timedelta,
		dateOverride=ARBITRARY_DATE) -> tuple:

		if dateOverride is not None:

			time = datetime.datetime(dateOverride.year, dateOverride.month, dateOverride.day,
				hour=time.hour, minute=time.minute, second=time.second, microsecond=time.microsecond,
				)

		return (time-dt, time+dt)