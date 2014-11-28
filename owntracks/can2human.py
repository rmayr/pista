#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import time
import re
import os
import sys

import dtc

def obd22human(splits, payload):
	human = None
	if len(splits) >= 2:
		if splits[1] == "01" or splits[1] == "02":
			if len(splits) >= 3:
				if splits[2] == "01":
					monitor = int (payload, 16)
					if monitor & 0x8000:
						mil = "MIL"
					else:
						mil = "___"
					dtcs = (monitor & 0x7f000000) >> 24

					human =  "Monitor Status since DTCs cleared: TODO %d %s" % (dtcs, mil)
				if splits[2] == "02":
					human =  "Freeze DTC: %s" % dtcString(payload)
				if splits[2] == "03":
					human =  "Fuel System Status: %s" % payload
				if splits[2] == "04":
					load = int(payload, 16) / 255
					human = "Calculated Engine Load Value: %d%%" % load
				if splits[2] == "05":
					temp = int(payload, 16) - 40
					human = "Engine Coolant Temparature: %d degrees C" % temp

				if splits[2] == "06":
					trim = (int(payload, 16) - 128) * 100 / 128
					human = "Short Term Fuel Trim Bank 1: %d%%" % trim
				if splits[2] == "07":
					trim = (int(payload, 16) - 128) * 100 / 128
					human = "Long Term Fuel Trim Bank 1: %d%%" % trim
				if splits[2] == "08":
					trim = (int(payload, 16) - 128) * 100 / 128
					human = "Short Term Fuel Trim Bank 2: %d%%" % trim
				if splits[2] == "09":
					trim = (int(payload, 16) - 128) * 100 / 128
					human = "Long Term Fuel Trim Bank 2: %d%%" % trim

				if splits[2] == "0a":
					pressure = int(payload, 16) * 3
					human = "Fuel Pressure: %d kPa" % pressure
				if splits[2] == "0b":
					pressure = int(payload, 16)
					human = "Intake Manifold Absolute Pressure: %d kPa" % pressure
				if splits[2] == "0c":
					rpm = int(payload, 16) / 4
					human = "Engine RPM: %d rpm" % rpm
				if splits[2] == "0d":
					speed = int(payload, 16)
					human = "Vehicle Speed: %d km/h" % speed

				# TODO

				if splits[2] == "1c":
					standard = int(payload, 16)
					standards = [
						"OBD-II as defined by the CARB",
						"OBD as defined by the EPA",
						"OBD and OBD-II",
						"OBD-I",
						"Not OBD compliant",
						"EOBD (Europe)",
						"EOBD and OBD-II",
						"EOBD and OBD",
						"EOBD, OBD and OBD II",
						"JOBD (Japan)",
						"JOBD and OBD II",
						"JOBD and EOBD",
						"JOBD, EOBD, and OBD II",
						"Reserved",
						"Reserved",
						"Reserved",
						"Engine Manufacturer Diagnostics (EMD)",
						"Engine Manufacturer Diagnostics Enhanced (EMD+)",
						"Heavy Duty On-Board Diagnostics (Child/Partial) (HD OBD-C)",
						"Heavy Duty On-Board Diagnostics (HD OBD)",
						"World Wide Harmonized OBD (WWH OBD)",
						"Reserved",
						"Heavy Duty Euro OBD Stage I without NOx control (HD EOBD-I)",
						"Heavy Duty Euro OBD Stage I with NOx control (HD EOBD-I N)",
						"Heavy Duty Euro OBD Stage II without NOx control (HD EOBD-II)",
						"Heavy Duty Euro OBD Stage II with NOx control (HD EOBD-II N)",
						"Reserved",
						"Brazil OBD Phase 1 (OBDBr-1)",
						"Brazil OBD Phase 2 (OBDBr-2)",
						"Korean OBD (KOBD)",
						"India OBD I (IOBD I)",
						"India OBD II (IOBD II)",
						"Heavy Duty Euro OBD Stage VI (HD EOBD-IV)"
						]
					if standard < len(standards):
						standardsText = standards[standard]
					elif standard < 251:
						standardsText = "Reserved"
					else:	
						standardsText = "Not available for assignement (SAE J1939 special meaning)"

					human = "OBD standards this vehicle conforms to: %s" % standardsText

		if splits[1] == "09":
			if len(splits) >= 7:
				if splits[2] == "02":
					name = payload.decode("hex")
					human = "VIN: %s" % name
				elif splits[2] == "04":
					name = payload.decode("hex")
					human = "Calibration ID: %s" % name
				elif splits[2] == "06":
					human = "CVN: %s" % payload

		elif splits[1] == "03":
			dtcs = int(payload[0:2], 16)
			for dtcnum in range(0, dtcs):
				human = "DTC: %s" % (dtcString(payload[2 + dtcnum * 4:2 + dtcnum * 4 + 4]))
	return human


def fms2human(splits, payload):
	human = None
	#print 'fms2human', splits

	if len(splits) >= 1:

		if splits[0] == "vehicleid":
			human = "Vehicle ID = %s" % (payload)

		if splits[0] == "driverid":
			human = "Driver ID = %s" % (payload)

		if splits[0] == "timedate":
			year = int(payload[10:], 16) + 1985
			month = int(payload[6:8], 16)
			day = (int(payload[8:10], 16) + 3) / 4
			hour = int(payload[4:6], 16)
			minute = int(payload[2:4], 16)
			second = (int(payload[0:2], 16) + 3) / 4

			if day > 0:
				human = "Date = %d-%d-%d %d:%d:%d" % (year, month, day, hour, minute, second)

		if splits[0] == "data":
			if len(splits) >= 2:
			
				if splits[1] == "maxspeed":
					maxspeed = int(payload, 16)
					human = "Maximum Speed = %d km/h" % (maxspeed)
			
				if splits[1] == "speed0":
					Samples = int(payload[2:], 16) * 256 + int(payload[0:2], 16)
					human = "# Samples speed 0 km/h = %d" % (Samples)
			
				if splits[1] == "speed1":
					Samples = int(payload[2:], 16) * 256 + int(payload[0:2], 16)
					human = "# Samples speed >= 1 km/h = %d" % (Samples)
			
				if splits[1] == "speed16":
					Samples = int(payload[2:], 16) * 256 + int(payload[0:2], 16)
					human = "# Samples speed >= 16 km/h = %d" % (Samples)
			
				if splits[1] == "speed46":
					Samples = int(payload[2:], 16) * 256 + int(payload[0:2], 16)
					human = "# Samples speed >= 46 km/h = %d" % (Samples)
			
				if splits[1] == "speed70":
					Samples = int(payload[2:], 16) * 256 + int(payload[0:2], 16)
					human = "# Samples speed >= 70 km/h = %d" % (Samples)
			
				if splits[1] == "brakes":
					Samples = int(payload[2:], 16) * 256 + int(payload[0:2], 16)
					human = "# Brakes = %d" % (Samples)
			
				if splits[1] == "cruise":
					Samples = int(payload[2:], 16) * 256 + int(payload[0:2], 16)
					human = "# Samples w/ Cruise Control = %d" % (Samples)
			
				if splits[1] == "pto":
					Samples = int(payload[2:], 16) * 256 + int(payload[0:2], 16)
					human = "# Samples w/ Power Takeoff = %d" % (Samples)
			
				if splits[1] == "rpm0":
					Samples = int(payload[2:], 16) * 256 + int(payload[0:2], 16)
					human = "# Samples rpm >= 0 = %d" % (Samples)
			
				if splits[1] == "rpm801":
					Samples = int(payload[2:], 16) * 256 + int(payload[0:2], 16)
					human = "# Samples rpm >= 801 = %d" % (Samples)
			
				if splits[1] == "rpm1101":
					Samples = int(payload[2:], 16) * 256 + int(payload[0:2], 16)
					human = "# Samples rpm >= 1101 = %d" % (Samples)
			
				if splits[1] == "rpm1451":
					Samples = int(payload[2:], 16) * 256 + int(payload[0:2], 16)
					human = "# Samples rpm >= 1451 = %d" % (Samples)
			
				if splits[1] == "rpm1701":
					Samples = int(payload[2:], 16) * 256 + int(payload[0:2], 16)
					human = "# Samples rpm >= 1701 = %d" % (Samples)
			
				if splits[1] == "totalfuel":
					fuel = float(int(payload[6:], 16) * 256 * 256 * 256 + int(payload[4:6], 16) * 256 * 256 + int(payload[2:4], 16) * 256 + int(payload[0:2], 16)) * 0.001
					human = "Total Fuel = %f L" % (fuel)
			
				if splits[1] == "fuellevel":
					level = float(int(payload, 16)) * 0.4
					human = "Fuel Level = %f %%" % (level)
			
				if splits[1] == "axesweight":
					weight = float(int(payload[8:]) * 256 * 256 * 256 * 256 + int(payload[6:8], 16) * 256 * 256 * 256 + int(payload[4:6], 16) * 256 * 256 + int(payload[2:4], 16) * 256 + int(payload[0:2], 16)) * 0.5
					human = "Axes Weight = %f kg" % (weight)
			
				if splits[1] == "enginehours":
					hours = float(int(payload[6:], 16) * 256 * 256 * 256 + int(payload[4:6], 16) * 256 * 256 + int(payload[2:4], 16) * 256 + int(payload[0:2], 16)) * 0.05
					human = "Engine Hours = %f h" % (hours)
			
				if splits[1] == "totaldist":
					dist = float(int(payload[6:], 16) * 256 * 256 * 256 + int(payload[4:6], 16) * 256 * 256 + int(payload[2:4], 16) * 256 + int(payload[0:2], 16)) * 0.005
					human = "Total Distance = %f km" % (dist)
			
				if splits[1] == "coolingtemp":
					temp = int(payload, 16) - 40
					human = "Coolant Temperature = %d C" % (temp)
			
				if splits[1] == "engineload":
					load = int(payload, 16)
					human = "Engine Load = %d %%" % (load)
			
				if splits[1] == "servicedist":
					dist = int(payload[2:], 16) * 256 + int(payload[0:2], 16) * 5
					human = "Next Service in= %d km" % (dist)
			
				if splits[1] == "tachodata":
					human = "Tachograph Data = %s" % (payload)
			
				if splits[1] == "tachospeed":
					speed = int(payload[2:], 16) * 256 + int(payload[0:2], 16)
					human = "Tachograph Speed %d km/h" % (speed)
			
				if splits[1] == "fuelrate":
					rate = int(payload[2:], 16) * 256 + int(payload[0:2], 16) * 0.05
					human = "Fuel Rate = %d L/h" % (rate)
			
				if splits[1] == "fuelecon":
					econ = int(payload[2:], 16) * 256 + int(payload[0:2], 16) / 512
					human = "Fuel Economy = %d km/L" % (econ)
			
				if splits[1] == "fmssw":
					human = "FMS SW = %s" % (payload)
			
				if splits[1] == "pedal0":
					Samples = int(payload[2:], 16) * 256 + int(payload[0:2], 16)
					human = "# Samples pedal > 0 %% = %d" % (Samples)
			
				if splits[1] == "pedal20":
					Samples = int(payload[2:], 16) * 256 + int(payload[0:2], 16)
					human = "# Samples pedal > 20 %% = %d" % (Samples)
			
				if splits[1] == "pedal40":
					Samples = int(payload[2:], 16) * 256 + int(payload[0:2], 16)
					human = "# Samples pedal > 40 %% = %d" % (Samples)
			
				if splits[1] == "pedal60":
					Samples = int(payload[2:], 16) * 256 + int(payload[0:2], 16)
					human = "# Samples pedal > 60 %% = %d" % (Samples)
			
				if splits[1] == "pedal80":
					Samples = int(payload[2:], 16) * 256 + int(payload[0:2], 16)
					human = "# Samples pedal > 80 %% = %d" % (Samples)
			
				if splits[1] == "selectedgear":
					gear = int(payload, 16) - 125
					if gear == 126:
						human = "Selected Gear = P" 
					elif gear == 0:
						human = "Selected Gear = N" 
					else:
						human = "Selected Gear = %d" % (gear)
			
				if splits[1] == "currentgear":
					gear = int(payload, 16) - 125
					if gear == 126:
						human = "Current Gear = P" 
					elif gear == 0:
						human = "Current Gear = N" 
					else:
						human = "Current Gear = %d" % (gear)
			
	return human

def can2human(topic, payload):
	splits = topic.split("/");
	#print "can2human", splits

	if splits[3] == "obd2":
		return obd22human(splits[4:], payload)

	if splits[3] == "fms":
		return fms2human(splits[4:], payload)

