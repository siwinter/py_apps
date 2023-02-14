#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-
#
#  serialMqtt.py
#  
#  Copyright 2023 swinter <swinter@swinter-ThinkPad-T420>
#  
#

import sys
import time
import logging
from systemd import journal
import paho.mqtt.client as mqttClient
import serial

#-----------------------------------------------------------------------
#  Logger
#
#-----------------------------------------------------------------------
logLevel    = logging.DEBUG
log_format = ('[%(asctime)s] %(levelname)-8s %(filename)-12s %(message)s')

logging.basicConfig(
	# Define logging level
	level=logLevel,
	# Declare the object we created to format the log messages
	format=log_format,
	# Declare handlers
#	handlers=[
#		journal.JournaldLogHandler()
#		journal.JournalHandler()
#	]
)

log = logging.getLogger(__name__)

log.info("start serialMqtt Version 0.0")

#-----------------------------------------------------------------------
#  MQTT
#
#-----------------------------------------------------------------------

broker_address= "localhost"  #Broker address
broker_port = 1883           #Broker port


Connected = False   #global variable for the state of the MQTT-connection
  
def on_connect(client, userdata, flags, rc):
	if rc == 0:
		global Connected                #Use global variable
		Connected = True                #Signal connection
		log.debug("MQTT connected")
	else:
		log.info("Connection failed")

def sndMqtt(string):
	t = string.split("/")
	if len(t) > 1 :
		if t[1] == "inf" :
			param = string.split(":", 1)
			if len(param) == 2 :
				try:
					client.publish(param[0], param[1])
				except:
					log.warning("could not publish to " + broker_address + " Port: " + str(broker_port))

def on_message(client, userdata, message):
	log.info("Message received: "  + message.payload)

def connectMqtt():
	try:
		log.info("connecting to " + broker_address + ":" + str(broker_port))
		client.connect(broker_address, broker_port)          #connect to broker
		log.info("connecting ...")
		client.loop_start()        #start the loop
		log.info("connected")
		while Connected != True:    #Wait for connection
			time.sleep(0.1)
	except:
		log.warning("connection failure")

def main():
	client = mqttClient.Client("serial2mqtt")              #create new instance
	client.on_connect= on_connect                      #attach function to callback
	client.on_message = on_message                     #attach function to callback
	connectMqtt()

	ser = serial.Serial('/dev/ttyUSB0', 9800, timeout=1)
	time.sleep(2)

	try:
		while True:
			l = ser.readline()
			if l:
				line = l.decode()    # Converting Byte Strings into unicode strings
				sndMqtt(line)

	except KeyboardInterrupt:
		print("exiting")
		client.disconnect()
		client.loop_stop()
		ser.close()
		
if __name__ == '__main__':
	import sys
	sys.exit(main())
