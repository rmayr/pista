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
				val = int(payload, 16)
				if splits[2] == "00":
					human = "PIDs supported bitmap: %s" % (payload)
					#TODO
	
				if splits[2] == "01":
					if val & 0x8000:
						mil = "MIL"
					else:
						mil = "___"
					dtcs = (val & 0x7f000000) >> 24
					human =  "Monitor Status since DTCs cleared: TODO %d %s" % (dtcs, mil)

				if splits[2] == "02":
					human =  "Freeze DTC: %s" % (dtcString(payload))

				if splits[2] == "03":
					human =  "Fuel System Status: %s" % (payload)
					#TODO

				if splits[2] == "04":
					human = "Calculated Engine Load Value: %d%%" % (val * 100 / 255)

				if splits[2] == "05":
					human = "Engine Coolant Temparature: %d degrees C" % (val - 40)

				if splits[2] == "06":
					trim = (int(payload, 16) - 128) * 100 / 128
					human = "Short Term Fuel Trim Bank 1: %d%%" % ((val - 128) * 100 / 128)

				if splits[2] == "07":
					human = "Long Term Fuel Trim Bank 1: %d%%" % (val * 100 / 128)

				if splits[2] == "08":
					human = "Short Term Fuel Trim Bank 2: %d%%" % (val * 100 / 128)

				if splits[2] == "09":
					human = "Long Term Fuel Trim Bank 2: %d%%" % (val * 100 / 128)

				if splits[2] == "0a":
					human = "Fuel Pressure: %d kPa" % (val * 3)

				if splits[2] == "0b":
					human = "Intake Manifold Absolute Pressure: %d kPa" % (val)

				if splits[2] == "0c":
					human = "Engine RPM: %d rpm" % (val / 4)

				if splits[2] == "0d":
					human = "Vehicle Speed: %d km/h" % (val)

				if splits[2] == "0e":
					human = "Timing Advance: %f degrees relative to #1 cylinder" % (float(val - 128) / 2.0)

				if splits[2] == "0f":
					human = "Intake air temperature: %d degrees C" % (val - 40)

				if splits[2] == "10":
					human = "MAF air flow rate %f grams/sec" % (float(val) / 100.0)

				if splits[2] == "11":
					human = "Throttle position %d%%" % (val * 100 / 255)

				if splits[2] == "12":
					human = "Commanded secondary air status %s" % (payload)
					#TODO

				if splits[2] == "13":
					human = "Oxygen sensors present %s" % (payload)
					#TODO

				if splits[2] == "14":
					fmt = "Bank 1, Sensor 1: Oxygen sensor voltage: %fV, Short term fuel trim %f%%"
					human = fmt % (float(val / 256) / 200.0, (val % 256) * 100 / 128)

				if splits[2] == "15":
					fmt = "Bank 1, Sensor 2: Oxygen sensor voltage: %fV, Short term fuel trim %f%%"
					human = fmt % (float(val / 256) / 200.0, (val % 256) * 100 / 128)

				if splits[2] == "16":
					fmt = "Bank 1, Sensor 3: Oxygen sensor voltage: %fV, Short term fuel trim %f%%"
					human = fmt % (float(val / 256) / 200.0, (val % 256) * 100 / 128)

				if splits[2] == "17":
					fmt = "Bank 1, Sensor 4: Oxygen sensor voltage: %fV, Short term fuel trim %f%%"
					human = fmt % (float(val / 256) / 200.0, (val % 256) * 100 / 128)

				if splits[2] == "18":
					fmt = "Bank 2, Sensor 1: Oxygen sensor voltage: %fV, Short term fuel trim %f%%"
					human = fmt % (float(val / 256) / 200.0, (val % 256) * 100 / 128)

				if splits[2] == "19":
					fmt = "Bank 2, Sensor 2: Oxygen sensor voltage: %fV, Short term fuel trim %f%%"
					human = fmt % (float(val / 256) / 200.0, (val % 256) * 100 / 128)

				if splits[2] == "1a":
					fmt = "Bank 2, Sensor 3: Oxygen sensor voltage: %fV, Short term fuel trim %f%%"
					human = fmt % (float(val / 256) / 200.0, (val % 256) * 100 / 128)

				if splits[2] == "1b":
					fmt = "Bank 2, Sensor 4: Oxygen sensor voltage: %fV, Short term fuel trim %f%%"
					human = fmt % (float(val / 256) / 200.0, (val % 256) * 100 / 128)

				if splits[2] == "1c":
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

				if splits[2] == "1d":
					human = "Oxygen sensors present %s" % (payload)
					#TODO

				if splits[2] == "1e":
					if val & 0x01:
						status = "active"
					else:
						status= "inactive"
					human = "Auxiliary input status: Powert Take Off (PTO) %s" % (status)

				if splits[2] == "1f":
					human = "Run time since engine start %d seconds" % (val)

				if splits[2] == "20":
					human = "PIDs supported bitmap: %s" % (payload)
					#TODO

				if splits[2] == "21":
					human = "Distance traveled with malfunction indicator lamp (MIL) on: %d km" % (val)

				if splits[2] == "22":
					human = "Fuel Rail Pressures (relative to manifold vacuum) %f kPa" % (float(val) * 0.079)

				if splits[2] == "23":
					human = "Fuel Rail Pressures (diesel, or gasoline direct inject) %d kPa (gauge)" % (val * 10)
				if splits[2] == "30":
					human = "# of warm-ups since codes cleared: %d" % (val)

				if splits[2] == "31":
					human = "Distance traveled since codes cleared: %d km" % (val)

				if splits[2] == "33":
					human = "Barometric pressure: %d kPa (Absolute)" % (val)

				if splits[2] == "34":
					fmt = "O2S1_WR_lambda(1): Equivalence Ratio: %f, Current %f mA"
					human = fmt % (float(val / 65536) / 32768.0, float(val % 65536) / 256.0 - 128.0)

#TODO
#24	4	O2S1_WR_lambda(1): #Equivalence Ratio #Voltage	0 #0	1.999 #7.999	N/A #V	((A*256)+B)*2/65535 or ((A*256)+B)/32768 #((C*256)+D)*8/65535 or ((C*256)+D)/8192
#25	4	O2S2_WR_lambda(1): #Equivalence Ratio #Voltage	0 #0	2 #8	N/A #V	((A*256)+B)*2/65535 #((C*256)+D)*8/65535
#26	4	O2S3_WR_lambda(1): #Equivalence Ratio #Voltage	0 #0	2 #8	N/A #V	((A*256)+B)*2/65535 #((C*256)+D)*8/65535
#27	4	O2S4_WR_lambda(1): #Equivalence Ratio #Voltage	0 #0	2 #8	N/A #V	((A*256)+B)*2/65535 #((C*256)+D)*8/65535
#28	4	O2S5_WR_lambda(1): #Equivalence Ratio #Voltage	0 #0	2 #8	N/A #V	((A*256)+B)*2/65535 #((C*256)+D)*8/65535
#29	4	O2S6_WR_lambda(1): #Equivalence Ratio #Voltage	0 #0	2 #8	N/A #V	((A*256)+B)*2/65535 #((C*256)+D)*8/65535
#2A	4	O2S7_WR_lambda(1): #Equivalence Ratio #Voltage	0 #0	2 #8	N/A #V	((A*256)+B)*2/65535 #((C*256)+D)*8/65535
#2B	4	O2S8_WR_lambda(1): #Equivalence Ratio #Voltage	0 #0	2 #8	N/A #V	((A*256)+B)*2/65535 #((C*256)+D)*8/65535
#2C	1	Commanded EGR	0	100	 %	A*100/255
#2D	1	EGR Error	-100	99.22	 %	(A-128) * 100/128
#2E	1	Commanded evaporative purge	0	100	 %	A*100/255
#2F	1	Fuel Level Input	0	100	 %	A*100/255
#32	2	Evap. System Vapor Pressure	-8,192	8,192	Pa	((A*256)+B)/4 (A and B are two's complement signed)
#35	4	O2S2_WR_lambda(1): #Equivalence Ratio #Current	0 #-128	2 #128	N/A #mA	((A*256)+B)/32,768 #((C*256)+D)/256 - 128
#36	4	O2S3_WR_lambda(1): #Equivalence Ratio #Current	0 #-128	2 #128	N/A #mA	((A*256)+B)/32768 #((C*256)+D)/256 - 128
#37	4	O2S4_WR_lambda(1): #Equivalence Ratio #Current	0 #-128	2 #128	N/A #mA	((A*256)+B)/32,768 #((C*256)+D)/256 - 128
#38	4	O2S5_WR_lambda(1): #Equivalence Ratio #Current	0 #-128	2 #128	N/A #mA	((A*256)+B)/32,768 #((C*256)+D)/256 - 128
#39	4	O2S6_WR_lambda(1): #Equivalence Ratio #Current	0 #-128	2 #128	N/A #mA	((A*256)+B)/32,768 #((C*256)+D)/256 - 128
#3A	4	O2S7_WR_lambda(1): #Equivalence Ratio #Current	0 #-128	2 #128	N/A #mA	((A*256)+B)/32,768 #((C*256)+D)/256 - 128
#3B	4	O2S8_WR_lambda(1): #Equivalence Ratio #Current	0 #-128	2 #128	N/A #mA	((A*256)+B)/32,768 #((C*256)+D)/256 - 128
#3C	2	Catalyst Temperature #Bank 1, Sensor 1	-40	6,513.5	°C	((A*256)+B)/10 - 40
#3D	2	Catalyst Temperature #Bank 2, Sensor 1	-40	6,513.5	°C	((A*256)+B)/10 - 40
#3E	2	Catalyst Temperature #Bank 1, Sensor 2	-40	6,513.5	°C	((A*256)+B)/10 - 40
#3F	2	Catalyst Temperature #Bank 2, Sensor 2	-40	6,513.5	°C	((A*256)+B)/10 - 40

				if splits[2] == "40":
					human = "PIDs supported bitmap: %s" % (payload)
					#TODO

				if splits[2] == "41":
					human = "Monitor status this drive cycle (Bit encoded): %s" % (payload)
					#TODO
	
				if splits[2] == "42":
					human = "Control module voltage: %f V" % (float(val) / 1000.0)

				if splits[2] == "45":
					human = "Relative throttle position: %d%%" % (val * 100 / 255)

				if splits[2] == "46":
					human = "Ambient air temperature: %d degrees C" % (val - 40)

				if splits[2] == "49":
					human = "Accelerator pedal position D: %d%%" % (val * 100 / 255)

				if splits[2] == "4a":
					human = "Accelerator pedal position F: %d%%" % (val * 100 / 255)

				if splits[2] == "4c":
					human = "Commanded throttle actuator: %d%%" % (val * 100 / 255)

				if splits[2] == "4f":
					fmt = "Maximum value for equivalence ratio: %d, oxygen sensor voltage: %d V, oxygen sensor current: %d mA, and intake manifold absolute pressure %d kPa"
					human = fmt % (int(payload[0:2]), int(payload[2:4]),int(payload[4:6]),int(payload[6:8]) * 110)

#TODO
#43	2	Absolute load value	0	25,700	 %	((A*256)+B)*100/255
#44	2	Fuel/Air commanded equivalence ratio	0	2	N/A	((A*256)+B)/32768
#45	1	Relative throttle position	0	100	 %	A*100/255
#47	1	Absolute throttle position B	0	100	 %	A*100/255
#48	1	Absolute throttle position C	0	100	 %	A*100/255
#4B	1	Accelerator pedal position F	0	100	 %	A*100/255
#4D	2	Time run with MIL on	0	65,535	minutes	(A*256)+B
#4E	2	Time since trouble codes cleared	0	65,535	minutes	(A*256)+B
#50	4	Maximum value for air flow rate from mass air flow sensor	0	2550	g/s	A*10, B, C, and D are reserved for future use
#51	1	Fuel Type				From fuel type table see below
#52	1	Ethanol fuel %	0	100	 %	A*100/255
#53	2	Absolute Evap system Vapor Pressure	0	327.675	kPa	((A*256)+B)/200
#54	2	Evap system vapor pressure	-32,767	32,768	Pa	((A*256)+B)-32767
#55	2	Short term secondary oxygen sensor trim bank 1 and bank 3	-100	99.22	 %	(A-128)*100/128
#(B-128)*100/128
#56	2	Long term secondary oxygen sensor trim bank 1 and bank 3	-100	99.22	 %	(A-128)*100/128
#(B-128)*100/128
#57	2	Short term secondary oxygen sensor trim bank 2 and bank 4	-100	99.22	 %	(A-128)*100/128
#(B-128)*100/128
#58	2	Long term secondary oxygen sensor trim bank 2 and bank 4	-100	99.22	 %	(A-128)*100/128
#(B-128)*100/128
#59	2	Fuel rail pressure (absolute)	0	655,350	kPa	((A*256)+B) * 10
#5A	1	Relative accelerator pedal position	0	100	 %	A*100/255
#5B	1	Hybrid battery pack remaining life	0	100	 %	A*100/255
#5C	1	Engine oil temperature	-40	210	°C	A - 40
#5D	2	Fuel injection timing	-210.00	301.992	°	(((A*256)+B)-26,880)/128
#5E	2	Engine fuel rate	0	3212.75	L/h	((A*256)+B)*0.05
#5F	1	Emission requirements to which vehicle is designed				Bit Encoded

				if splits[2] == "60":
					human = "PIDs supported bitmap: %s" % (payload)
					#TODO

				if splits[2] == "61":
					human = "Driver's demand engine - percent torque %d%%" % (val - 125)

				if splits[2] == "62":
					human = "Actual engine - percent torque %d%%" % (val - 125)

				if splits[2] == "63":
					human = "Engine reference torque %d Nm" % (val)

				if splits[2] == "64":
					fmt = "Engin percent torque data: Idle: %d%%, Engine point 1: %d%%, Engine point 2: %d%%, Engine point 3: %d%%, Engine point 4: %d%%"
					human = fmt % (int(payload[0:2]) - 125, int(payload[2:4]) - 125,int(payload[4:6]) - 125,int(payload[6:8]) - 125,int(payload[8]) - 125)

				if splits[2] == "65":
					human = "Auxiliary input / output supported, Bit Encoded: %s" % (payload)

				if splits[2] == "66":
					human = "Mass air flow sensor: %s" % (payload)

				if splits[2] == "67":
					human = "Engine coolant temperature: %s" % (payload)

				if splits[2] == "68":
					human = "Intake air temperature sensor: %s" % (payload)

				if splits[2] == "69":
					human = "Commanded EGR and EGR Error: %s" % (payload)

				if splits[2] == "6A":
					human = "Commanded Diesel intake air flow control and relative intake air flow position: %s" % (payload)

				if splits[2] == "6B":
					human = "Exhaust gas recirculation temperature: %s" % (payload)

				if splits[2] == "6C":
					human = "Commanded throttle actuator control and relative throttle position: %s" % (payload)

				if splits[2] == "6D":
					human = "Fuel pressure control system: %s" % (payload)

				if splits[2] == "6E":
					human = "Injection pressure control system: %s" % (payload)

				if splits[2] == "6F":
					human = "Turbocharger compressor inlet pressure: %s" % (payload)

				if splits[2] == "70":
					human = "Boost pressure control: %s" % (payload)

				if splits[2] == "71":
					human = "Variable Geometry turbo (VGT) control: %s" % (payload)

				if splits[2] == "72":
					human = "Wastegate control: %s" % (payload)

				if splits[2] == "73":
					human = "Exhaust pressure: %s" % (payload)

				if splits[2] == "74":
					human = "Turbocharger RPM: %s" % (payload)

				if splits[2] == "75":
					human = "Turbocharger temperature: %s" % (payload)

				if splits[2] == "76":
					human = "Turbocharger temperature: %s" % (payload)

				if splits[2] == "77":
					human = "Charge air cooler temperature (CACT): %s" % (payload)

				if splits[2] == "78":
					human = "Exhaust Gas temperature (EGT) Bank 1: %s" % (payload)
					#TODO

				if splits[2] == "79":
					human = "Exhaust Gas temperature (EGT) Bank 2: %s" % (payload)
					#TODO

				if splits[2] == "7A":
					human = "Diesel particulate filter (DPF): %s" % (payload)

				if splits[2] == "7B":
					human = "Diesel particulate filter (DPF): %s" % (payload)

				if splits[2] == "7C":
					human = "Diesel Particulate filter (DPF) temperature: %s" % (payload)

				if splits[2] == "7D":
					human = "NOx NTE control area status: %s" % (payload)

				if splits[2] == "7E":
					human = "PM NTE control area status: %s" % (payload)

				if splits[2] == "7F":
					human = "Engine run time: %s" % (payload)

				if splits[2] == "80":
					human = "PIDs supported bitmap: %s" % (payload)

					#TODO

				if splits[2] == "81":
					human = "Engine run time for Auxiliary Emissions Control Device (AECD): %s" % (payload)
	
				if splits[2] == "82":
					human = "Engine run time for Auxiliary Emissions Control Device (AECD): %s" % (payload)
	
				if splits[2] == "83":
					human = "NOx sensor: %s" % (payload)
	
				if splits[2] == "84":
					human = "Manifold surfrace temperature: %s" % (payload)

	
				if splits[2] == "85":
					human = "NOx reagent system: %s" % (payload)
	
				if splits[2] == "86":
					human = "Particulate matter (PM) sensor: %s" % (payload)
	
				if splits[2] == "87":
					human = " Intake manifold absolute pressure: %s" % (payload)
	
				if splits[2] == "a0":
					human = "PIDs supported bitmap: %s" % (payload)
					#TODO
	
				if splits[2] == "c0":
					human = "PIDs supported bitmap: %s" % (payload)
					#TODO
	

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

