#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Christoph Krey <krey.christoph()gmail.com>'
__copyright__ = 'Copyright 2014 Christoph Krey'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

import datetime
import time
import re
import os
import sys

from owntracks.dtc import dtcString

def obd22human(splits, payload):
	human = None
	if len(splits) >= 2:
		if splits[1] == "01" or splits[1] == "02":
			val = int(payload, 16)
			if len(splits) >= 3:
				if splits[2] == "00":
					human = "PIDs supported bitmap: TODO %s" % (payload)
	
				elif splits[2] == "01":
					if val & 0x8000:
						mil = "MIL"
					else:
						mil = "___"
					dtcs = (val & 0x7f000000) >> 24
					human =  "Monitor Status since DTCs cleared: %d %s" % (dtcs, mil)

				elif splits[2] == "02":
					human =  "Freeze DTC: %s" % (dtcString(payload))

				elif splits[2] == "03":
					human =  "Fuel System Status: TODO %s" % (payload)

				elif splits[2] == "04":
					human = "Calculated Engine Load Value: %d%%" % (val * 100 / 255)

				elif splits[2] == "05":
					human = "Engine Coolant Temparature: %d degrees C" % (val - 40)

				elif splits[2] == "06":
					trim = (int(payload, 16) - 128) * 100 / 128
					human = "Short Term Fuel Trim Bank 1: %d%%" % ((val - 128) * 100 / 128)

				elif splits[2] == "07":
					human = "Long Term Fuel Trim Bank 1: %d%%" % (val * 100 / 128)

				elif splits[2] == "08":
					human = "Short Term Fuel Trim Bank 2: %d%%" % (val * 100 / 128)

				elif splits[2] == "09":
					human = "Long Term Fuel Trim Bank 2: %d%%" % (val * 100 / 128)

				elif splits[2] == "0a":
					human = "Fuel Pressure: %d kPa" % (val * 3)

				elif splits[2] == "0b":
					human = "Intake Manifold Absolute Pressure: %d kPa" % (val)

				elif splits[2] == "0c":
					human = "Engine RPM: %d rpm" % (val / 4)

				elif splits[2] == "0d":
					human = "Vehicle Speed: %d km/h" % (val)

				elif splits[2] == "0e":
					human = "Timing Advance: %f degrees relative to #1 cylinder" % (float(val - 128) / 2.0)

				elif splits[2] == "0f":
					human = "Intake air temperature: %d degrees C" % (val - 40)

				elif splits[2] == "10":
					human = "MAF air flow rate %f grams/sec" % (float(val) / 100.0)

				elif splits[2] == "11":
					human = "Throttle position %d%%" % (val * 100 / 255)

				elif splits[2] == "12":
					human = "Commanded secondary air status: TODO %s" % (payload)

				elif splits[2] == "13":
					human = "Oxygen sensors present: TODO %s" % (payload)

				elif splits[2] == "14":
					fmt = "Bank 1, Sensor 1: Oxygen sensor voltage: %fV, Short term fuel trim %f%%"
					human = fmt % (float(val / 256) / 200.0, (val % 256) * 100 / 128)

				elif splits[2] == "15":
					fmt = "Bank 1, Sensor 2: Oxygen sensor voltage: %fV, Short term fuel trim %f%%"
					human = fmt % (float(val / 256) / 200.0, (val % 256) * 100 / 128)

				elif splits[2] == "16":
					fmt = "Bank 1, Sensor 3: Oxygen sensor voltage: %fV, Short term fuel trim %f%%"
					human = fmt % (float(val / 256) / 200.0, (val % 256) * 100 / 128)

				elif splits[2] == "17":
					fmt = "Bank 1, Sensor 4: Oxygen sensor voltage: %fV, Short term fuel trim %f%%"
					human = fmt % (float(val / 256) / 200.0, (val % 256) * 100 / 128)

				elif splits[2] == "18":
					fmt = "Bank 2, Sensor 1: Oxygen sensor voltage: %fV, Short term fuel trim %f%%"
					human = fmt % (float(val / 256) / 200.0, (val % 256) * 100 / 128)

				elif splits[2] == "19":
					fmt = "Bank 2, Sensor 2: Oxygen sensor voltage: %fV, Short term fuel trim %f%%"
					human = fmt % (float(val / 256) / 200.0, (val % 256) * 100 / 128)

				elif splits[2] == "1a":
					fmt = "Bank 2, Sensor 3: Oxygen sensor voltage: %fV, Short term fuel trim %f%%"
					human = fmt % (float(val / 256) / 200.0, (val % 256) * 100 / 128)

				elif splits[2] == "1b":
					fmt = "Bank 2, Sensor 4: Oxygen sensor voltage: %fV, Short term fuel trim %f%%"
					human = fmt % (float(val / 256) / 200.0, (val % 256) * 100 / 128)

				elif splits[2] == "1c":
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
					if val < len(standards):
						standardsText = standards[val]
					elif val < 251:
						standardsText = "Reserved"
					else:	
						standardsText = "Not available for assignement (SAE J1939 special meaning)"

					human = "OBD standards this vehicle conforms to: %s" % standardsText

				elif splits[2] == "1d":
					human = "Oxygen sensors present: TODO %s" % (payload)

				elif splits[2] == "1e":
					if val & 0x01:
						status = "active"
					else:
						status= "inactive"
					human = "Auxiliary input status: Powert Take Off (PTO) %s" % (status)

				elif splits[2] == "1f":
					human = "Run time since engine start %d seconds" % (val)

				elif splits[2] == "20":
					human = "PIDs supported bitmap: TODO %s" % (payload)

				elif splits[2] == "21":
					human = "Distance traveled with malfunction indicator lamp (MIL) on: %d km" % (val)

				elif splits[2] == "22":
					human = "Fuel Rail Pressures (relative to manifold vacuum) %f kPa" % (float(val) * 0.079)

				elif splits[2] == "23":
					human = "Fuel Rail Pressures (diesel, or gasoline direct inject) %d kPa (gauge)" % (val * 10)

				elif splits[2] == "24":
					fmt = "O2S1_WR_lambda(1): Equivalence Ratio: %f, Voltage: %f V" 
					human = fmt % (float(val / 65536) / 32768.0, float(val % 65536) / 8192.0)

				elif splits[2] == "25":
					fmt = "O2S2_WR_lambda(1): Equivalence Ratio: %f, Voltage: %f V" 
					human = fmt % (float(val / 65536) / 32768.0, float(val % 65536) / 8192.0)

				elif splits[2] == "26":
					fmt = "O2S3_WR_lambda(1): Equivalence Ratio: %f, Voltage: %f V" 
					human = fmt % (float(val / 65536) / 32768.0, float(val % 65536) / 8192.0)

				elif splits[2] == "27":
					fmt = "O2S4_WR_lambda(1): Equivalence Ratio: %f, Voltage: %f V" 
					human = fmt % (float(val / 65536) / 32768.0, float(val % 65536) / 8192.0)

				elif splits[2] == "28":
					fmt = "O2S5_WR_lambda(1): Equivalence Ratio: %f, Voltage: %f V" 
					human = fmt % (float(val / 65536) / 32768.0, float(val % 65536) / 8192.0)

				elif splits[2] == "29":
					fmt = "O2S6_WR_lambda(1): Equivalence Ratio: %f, Voltage: %f V" 
					human = fmt % (float(val / 65536) / 32768.0, float(val % 65536) / 8192.0)

				elif splits[2] == "2a":
					fmt = "O2S7_WR_lambda(1): Equivalence Ratio: %f, Voltage: %f V" 
					human = fmt % (float(val / 65536) / 32768.0, float(val % 65536) / 8192.0)

				elif splits[2] == "2b":
					fmt = "O2S8_WR_lambda(1): Equivalence Ratio: %f, Voltage: %f V" 
					human = fmt % (float(val / 65536) / 32768.0, float(val % 65536) / 8192.0)

				elif splits[2] == "2c":
					human = "# of warm-ups since codes cleared: %d" % (val)

				elif splits[2] == "2d":
					human = "Commanded EGR: %d%%" % (val * 100 / 255)

				elif splits[2] == "2e":
					human = "EGR Error: %d%%" % ((val-128) * 100 / 128)

				elif splits[2] == "2f":
					human = "Fuel Level Input: %d%%" % (val * 100 / 255)

				elif splits[2] == "32":
					if val > 32767:
						value = -65536 + val
					else:
						value = val
					human = "Evap. System Vapor Pressure: %d Pa" % (value / 4)

				elif splits[2] == "30":
					human = "# of warm-ups since codes cleared: %d" % (val)

				elif splits[2] == "31":
					human = "Distance traveled since codes cleared: %d km" % (val)

				elif splits[2] == "33":
					human = "Barometric pressure: %d kPa (Absolute)" % (val)

				elif splits[2] == "34":
					fmt = "O2S1_WR_lambda(1): Equivalence Ratio: %f, Current %f mA"
					human = fmt % (float(val / 65536) / 32768.0, float(val % 65536) / 256.0 - 128.0)

				elif splits[2] == "35":
					fmt = "O2S2_WR_lambda(1): Equivalence Ratio: %f, Current %f mA"
					human = fmt % (float(val / 65536) / 32768.0, float(val % 65536) / 256.0 - 128.0)

				elif splits[2] == "36":
					fmt = "O2S3_WR_lambda(1): Equivalence Ratio: %f, Current %f mA"
					human = fmt % (float(val / 65536) / 32768.0, float(val % 65536) / 256.0 - 128.0)

				elif splits[2] == "37":
					fmt = "O2S4_WR_lambda(1): Equivalence Ratio: %f, Current %f mA"
					human = fmt % (float(val / 65536) / 32768.0, float(val % 65536) / 256.0 - 128.0)

				elif splits[2] == "38":
					fmt = "O2S5_WR_lambda(1): Equivalence Ratio: %f, Current %f mA"
					human = fmt % (float(val / 65536) / 32768.0, float(val % 65536) / 256.0 - 128.0)

				elif splits[2] == "39":
					fmt = "O2S6_WR_lambda(1): Equivalence Ratio: %f, Current %f mA"
					human = fmt % (float(val / 65536) / 32768.0, float(val % 65536) / 256.0 - 128.0)

				elif splits[2] == "3a":
					fmt = "O2S7_WR_lambda(1): Equivalence Ratio: %f, Current %f mA"
					human = fmt % (float(val / 65536) / 32768.0, float(val % 65536) / 256.0 - 128.0)

				elif splits[2] == "3b":
					fmt = "O2S8_WR_lambda(1): Equivalence Ratio: %f, Current %f mA"
					human = fmt % (float(val / 65536) / 32768.0, float(val % 65536) / 256.0 - 128.0)

				elif splits[2] == "3c":
					human = "Catalyst Temperature Bank 1, Sensor 1: %f degrees C" % (float(val) / 10.0 - 40.0)

				elif splits[2] == "3d":
					human = "Catalyst Temperature Bank 2, Sensor 1: %f degrees C" % (float(val) / 10.0 - 40.0)

				elif splits[2] == "3e":
					human = "Catalyst Temperature Bank 1, Sensor 2: %f degrees C" % (float(val) / 10.0 - 40.0)

				elif splits[2] == "3f":
					human = "Catalyst Temperature Bank 2, Sensor 2: %f degrees C" % (float(val) / 10.0 - 40.0)

				elif splits[2] == "40":
					human = "PIDs supported bitmap: TODO %s" % (payload)

				elif splits[2] == "41":
					human = "Monitor status this drive cycle (Bit encoded): TODO %s" % (payload)
	
				elif splits[2] == "42":
					human = "Control module voltage: %f V" % (float(val) / 1000.0)

				elif splits[2] == "43":
					human = "Absolute load value: %d%%" % (val * 100 / 255)

				elif splits[2] == "44":
					human = "Fuel/Air commanded equivalence ration: %f" % (float(val) / 32768)

				elif splits[2] == "45":
					human = "Relative throttle position: %d%%" % (val * 100 / 255)

				elif splits[2] == "46":
					human = "Ambient air temperature: %d degrees C" % (val - 40)

				elif splits[2] == "47":
					human = "Absolute throttle position B: %d%%" % (val * 100 / 255)

				elif splits[2] == "48":
					human = "Absolute throttle position C: %d%%" % (val * 100 / 255)

				elif splits[2] == "49":
					human = "Accelerator pedal position D: %d%%" % (val * 100 / 255)

				elif splits[2] == "4a":
					human = "Accelerator pedal position E: %d%%" % (val * 100 / 255)

				elif splits[2] == "4b":
					human = "Accelerator pedal position F: %d%%" % (val * 100 / 255)

				elif splits[2] == "4c":
					human = "Commanded throttle actuator: %d%%" % (val * 100 / 255)

				elif splits[2] == "4d":
					human = "Time run with MIL on: %d" % (val)

				elif splits[2] == "4e":
					human = "Time since trouble codes cleared: %d minutes" % (val)

				elif splits[2] == "4f":
					fmt = "Maximum value for equivalence ratio: %d, oxygen sensor voltage: %d V, oxygen sensor current: %d mA, and intake manifold absolute pressure %d kPa"
					human = fmt % (int(payload[0:2]), int(payload[2:4]),int(payload[4:6]),int(payload[6:8]) * 110)

				elif splits[2] == "50":
					human = "Maximum value for air flow rate from mass air flow sensor: %d g/s" % ((val / 65536 / 256) * 10)
	
				elif splits[2] == "51":
					human = "Fuel Type: TODO %s" % (payload)
	
				elif splits[2] == "52":
					human = "Ethanol fuel: %d%%" % (val * 100 / 255)

				elif splits[2] == "53":
					human = "Absolute Evap system Vapor Pressure: %d kPa" % (val / 200)

				elif splits[2] == "54":
					human = "Evap system vapor pressure: %d Pa" % (val - 32767)

				elif splits[2] == "55":
					human = "Short term secondary oxygen sensor trim bank 1 and bank 3: %f%% %f%%" % (float(val / 256) * 100.0 / 128.0, float((val % 256) * 100.0 / 128.0))

				elif splits[2] == "56":
					human = "Long term secondary oxygen sensor trim bank 1 and bank 3: %f%% %f%%" % (float(val / 256) * 100.0 / 128.0, float((val % 256) * 100.0 / 128.0))

				elif splits[2] == "57":
					human = "Short term secondary oxygen sensor trim bank 2 and bank 4: %f%% %f%%" % (float(val / 256) * 100.0 / 128.0, float((val % 256) * 100.0 / 128.0))

				elif splits[2] == "58":
					human = "Long term secondary oxygen sensor trim bank 2 and bank 4: %f%% %f%%" % (float(val / 256) * 100.0 / 128.0, float((val % 256) * 100.0 / 128.0))

				elif splits[2] == "59":
					human = "Fuel rail pressure (absolute): %d" % (val * 10)

				elif splits[2] == "5a":
					human = "Relative accelerator pedal position: %d%%" % (val * 100 / 255)

				elif splits[2] == "5b":
					human = "Hybrid battery pack remaining life: %d%%" % (val * 100 / 255)

				elif splits[2] == "5c":
					human = "Engine oil temperature: %d degrees C" % (val - 40)

				elif splits[2] == "5d":
					human = "Fuel injection timing: %f degrees" % (float(val - 26880) / 128.0)

				elif splits[2] == "5e":
					human = "Engine fuel rate: %f L/h" % (float(val) * 0.05)

				elif splits[2] == "5f":
					human = "Emiession requirements to which vehicle is designed: TODO %s" % (payload)
	
				elif splits[2] == "60":
					human = "PIDs supported bitmap: TODO %s" % (payload)

				elif splits[2] == "61":
					human = "Driver's demand engine - percent torque %d%%" % (val - 125)

				elif splits[2] == "62":
					human = "Actual engine - percent torque %d%%" % (val - 125)

				elif splits[2] == "63":
					human = "Engine reference torque %d Nm" % (val)

				elif splits[2] == "64":
					fmt = "Engin percent torque data: Idle: %d%%, Engine point 1: %d%%, Engine point 2: %d%%, Engine point 3: %d%%, Engine point 4: %d%%"
					human = fmt % (int(payload[0:2]) - 125, int(payload[2:4]) - 125,int(payload[4:6]) - 125,int(payload[6:8]) - 125,int(payload[8]) - 125)

				elif splits[2] == "65":
					human = "Auxiliary input / output supported, Bit Encoded: %s" % (payload)

				elif splits[2] == "66":
					human = "Mass air flow sensor: %s" % (payload)

				elif splits[2] == "67":
					human = "Engine coolant temperature: %s" % (payload)

				elif splits[2] == "68":
					human = "Intake air temperature sensor: %s" % (payload)

				elif splits[2] == "69":
					human = "Commanded EGR and EGR Error: %s" % (payload)

				elif splits[2] == "6A":
					human = "Commanded Diesel intake air flow control and relative intake air flow position: %s" % (payload)

				elif splits[2] == "6B":
					human = "Exhaust gas recirculation temperature: %s" % (payload)

				elif splits[2] == "6C":
					human = "Commanded throttle actuator control and relative throttle position: %s" % (payload)

				elif splits[2] == "6D":
					human = "Fuel pressure control system: %s" % (payload)

				elif splits[2] == "6E":
					human = "Injection pressure control system: %s" % (payload)

				elif splits[2] == "6F":
					human = "Turbocharger compressor inlet pressure: %s" % (payload)

				elif splits[2] == "70":
					human = "Boost pressure control: %s" % (payload)

				elif splits[2] == "71":
					human = "Variable Geometry turbo (VGT) control: %s" % (payload)

				elif splits[2] == "72":
					human = "Wastegate control: %s" % (payload)

				elif splits[2] == "73":
					human = "Exhaust pressure: %s" % (payload)

				elif splits[2] == "74":
					human = "Turbocharger RPM: %s" % (payload)

				elif splits[2] == "75":
					human = "Turbocharger temperature: %s" % (payload)

				elif splits[2] == "76":
					human = "Turbocharger temperature: %s" % (payload)

				elif splits[2] == "77":
					human = "Charge air cooler temperature (CACT): %s" % (payload)

				elif splits[2] == "78":
					human = "Exhaust Gas temperature (EGT) Bank 1: TODO %s" % (payload)

				elif splits[2] == "79":
					human = "Exhaust Gas temperature (EGT) Bank 2: TODO %s" % (payload)

				elif splits[2] == "7A":
					human = "Diesel particulate filter (DPF): %s" % (payload)

				elif splits[2] == "7B":
					human = "Diesel particulate filter (DPF): %s" % (payload)

				elif splits[2] == "7C":
					human = "Diesel Particulate filter (DPF) temperature: %s" % (payload)

				elif splits[2] == "7D":
					human = "NOx NTE control area status: %s" % (payload)

				elif splits[2] == "7E":
					human = "PM NTE control area status: %s" % (payload)

				elif splits[2] == "7F":
					human = "Engine run time: %s" % (payload)

				elif splits[2] == "80":
					human = "PIDs supported bitmap: TODO %s" % (payload)

				elif splits[2] == "81":
					human = "Engine run time for Auxiliary Emissions Control Device (AECD): %s" % (payload)
	
				elif splits[2] == "82":
					human = "Engine run time for Auxiliary Emissions Control Device (AECD): %s" % (payload)
	
				elif splits[2] == "83":
					human = "NOx sensor: %s" % (payload)
	
				elif splits[2] == "84":
					human = "Manifold surfrace temperature: %s" % (payload)
	
				elif splits[2] == "85":
					human = "NOx reagent system: %s" % (payload)
	
				elif splits[2] == "86":
					human = "Particulate matter (PM) sensor: %s" % (payload)
	
				elif splits[2] == "87":
					human = " Intake manifold absolute pressure: %s" % (payload)
	
				elif splits[2] == "a0":
					human = "PIDs supported bitmap: TODO %s" % (payload)
	
				elif splits[2] == "c0":
					human = "PIDs supported bitmap: TODO %s" % (payload)

		elif splits[1] == "03":
			dtcs = int(payload[0:2], 16)
			human = None
			for dtcnum in range(0, dtcs):
				if human == None:
					human = "DTCs (%d):" % (dtcs)
				else:
					human += "," 
				human += " %s" % (dtcString(payload[2 + dtcnum * 4:2 + dtcnum * 4 + 4]))

		elif splits[1] == "09":
			if len(splits) >= 3:
				val = int(payload, 16)
				if splits[2] == "00":
					human = "PIDs supported bitmap: TODO %s" % (payload)

				elif splits[2] == "01":
					human = "VIN Message Count in PID 02: %d" % (val)

				elif splits[2] == "02":
					name = payload.decode("hex").encode("string-escape")
					human = "VIN: %s" % name

				elif splits[2] == "03":
					human = "Calibration ID message count in PID 04: %d" % (val)

				elif splits[2] == "04":
					name = payload.decode("hex").encode("string-escape")
					human = "Calibration ID: %s" % name

				elif splits[2] == "05":
					human = "Calibration verification numbers (CVN) message count in PID 06: %d" % (val)

				elif splits[2] == "06":
					human = "CVN: %s" % payload

	return human


def fms2human(splits, payload):
	human = None
	#print 'fms2human', splits

	if len(splits) >= 1:

		if splits[0] == "vehicleid":
			id = payload.decode("hex").encode("string-escape")
			human = "Vehicle ID = %s" % (id)

		if splits[0] == "driverid":
			id = payload.decode("hex").encode("string-escape")
			human = "Driver ID = %s" % (id)

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
			
				elif splits[1] == "speed0":
					Samples = int(payload[2:], 16) * 256 + int(payload[0:2], 16)
					human = "# Samples speed 0 km/h = %d" % (Samples)
			
				elif splits[1] == "speed1":
					Samples = int(payload[2:], 16) * 256 + int(payload[0:2], 16)
					human = "# Samples speed >= 1 km/h = %d" % (Samples)
			
				elif splits[1] == "speed16":
					Samples = int(payload[2:], 16) * 256 + int(payload[0:2], 16)
					human = "# Samples speed >= 16 km/h = %d" % (Samples)
			
				elif splits[1] == "speed46":
					Samples = int(payload[2:], 16) * 256 + int(payload[0:2], 16)
					human = "# Samples speed >= 46 km/h = %d" % (Samples)
			
				elif splits[1] == "speed70":
					Samples = int(payload[2:], 16) * 256 + int(payload[0:2], 16)
					human = "# Samples speed >= 70 km/h = %d" % (Samples)
			
				elif splits[1] == "brakes":
					Samples = int(payload[2:], 16) * 256 + int(payload[0:2], 16)
					human = "# Brakes = %d" % (Samples)
			
				elif splits[1] == "cruise":
					Samples = int(payload[2:], 16) * 256 + int(payload[0:2], 16)
					human = "# Samples w/ Cruise Control = %d" % (Samples)
			
				elif splits[1] == "pto":
					Samples = int(payload[2:], 16) * 256 + int(payload[0:2], 16)
					human = "# Samples w/ Power Takeoff = %d" % (Samples)
			
				elif splits[1] == "rpm0":
					Samples = int(payload[2:], 16) * 256 + int(payload[0:2], 16)
					human = "# Samples rpm >= 0 = %d" % (Samples)
			
				elif splits[1] == "rpm801":
					Samples = int(payload[2:], 16) * 256 + int(payload[0:2], 16)
					human = "# Samples rpm >= 801 = %d" % (Samples)
			
				elif splits[1] == "rpm1101":
					Samples = int(payload[2:], 16) * 256 + int(payload[0:2], 16)
					human = "# Samples rpm >= 1101 = %d" % (Samples)
			
				elif splits[1] == "rpm1451":
					Samples = int(payload[2:], 16) * 256 + int(payload[0:2], 16)
					human = "# Samples rpm >= 1451 = %d" % (Samples)
			
				elif splits[1] == "rpm1701":
					Samples = int(payload[2:], 16) * 256 + int(payload[0:2], 16)
					human = "# Samples rpm >= 1701 = %d" % (Samples)
			
				elif splits[1] == "totalfuel":
					fuel = float(int(payload[6:], 16) * 256 * 256 * 256 + int(payload[4:6], 16) * 256 * 256 + int(payload[2:4], 16) * 256 + int(payload[0:2], 16)) * 0.5
					human = "Total Fuel = %f L" % (fuel)
			
				elif splits[1] == "fuellevel":
					level = float(int(payload, 16)) * 0.4
					human = "Fuel Level = %f %%" % (level)
			
				elif splits[1] == "axlesweight":
					weight = float(int(payload[8:]) * 256 * 256 * 256 * 256 + int(payload[6:8], 16) * 256 * 256 * 256 + int(payload[4:6], 16) * 256 * 256 + int(payload[2:4], 16) * 256 + int(payload[0:2], 16)) * 0.5
					human = "Axles Weight = %f kg" % (weight)
			
				elif splits[1] == "enginehours":
					hours = float(int(payload[6:], 16) * 256 * 256 * 256 + int(payload[4:6], 16) * 256 * 256 + int(payload[2:4], 16) * 256 + int(payload[0:2], 16)) * 0.05
					human = "Engine Hours = %f h" % (hours)
			
				elif splits[1] == "totaldist":
					dist = float(int(payload[6:], 16) * 256 * 256 * 256 + int(payload[4:6], 16) * 256 * 256 + int(payload[2:4], 16) * 256 + int(payload[0:2], 16)) * 0.005
					human = "Total Distance = %f km" % (dist)
			
				elif splits[1] == "coolingtemp":
					temp = int(payload, 16) - 40
					human = "Coolant Temperature = %d C" % (temp)
			
				elif splits[1] == "engineload":
					load = int(payload, 16)
					human = "Engine Load = %d %%" % (load)
			
				elif splits[1] == "servicedist":
					dist = int(payload[2:], 16) * 256 + int(payload[0:2], 16) * 5
					human = "Next Service in= %d km" % (dist)
			
				elif splits[1] == "tachodata":
					human = "Tachograph Data = %s" % (payload)
			
				elif splits[1] == "tachospeed":
					speed = float(int(payload[2:], 16) * 256 + int(payload[0:2], 16)) / 256.0
					human = "Tachograph Speed %f km/h" % (speed)
			
				elif splits[1] == "fuelrate":
					rate = float(int(payload[2:], 16) * 256 + int(payload[0:2], 16)) * 0.05
					human = "Fuel Rate = %f L/h" % (rate)
			
				elif splits[1] == "fuelecon":
					econ = float(int(payload[2:], 16) * 256 + int(payload[0:2], 16)) / 512.0
					human = "Fuel Economy = %f km/L" % (econ)
			
				elif splits[1] == "fmssw":
					id = payload.decode("hex").encode("string-escape")
					human = "FMS SW = %s" % (id)
			
				elif splits[1] == "pedal0":
					Samples = int(payload[2:], 16) * 256 + int(payload[0:2], 16)
					human = "# Samples pedal > 0 %% = %d" % (Samples)
			
				elif splits[1] == "pedal20":
					Samples = int(payload[2:], 16) * 256 + int(payload[0:2], 16)
					human = "# Samples pedal > 20 %% = %d" % (Samples)
			
				elif splits[1] == "pedal40":
					Samples = int(payload[2:], 16) * 256 + int(payload[0:2], 16)
					human = "# Samples pedal > 40 %% = %d" % (Samples)
			
				elif splits[1] == "pedal60":
					Samples = int(payload[2:], 16) * 256 + int(payload[0:2], 16)
					human = "# Samples pedal > 60 %% = %d" % (Samples)
			
				elif splits[1] == "pedal80":
					Samples = int(payload[2:], 16) * 256 + int(payload[0:2], 16)
					human = "# Samples pedal > 80 %% = %d" % (Samples)
			
				elif splits[1] == "selectedgear":
					gear = int(payload, 16) - 125
					if gear == 126:
						human = "Selected Gear = P" 
					elif gear == 0:
						human = "Selected Gear = N" 
					else:
						human = "Selected Gear = %d" % (gear)
			
				elif splits[1] == "currentgear":
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

	elif splits[3] == "fms":
		return fms2human(splits[4:], payload)

