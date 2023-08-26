#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-
#
#  vpnControll.py
#  Überprüft jede Minute ob tun0 existiert.
#  Daraus schließt das Programm, dass eine VPN-Verbindung nach Spanien existiert.
#  Anderenfalls wird eine deutsche IP-Adresse angenommen.

import sys
import time
import logging
#from systemd import journal
from subprocess import run
import paho.mqtt.client as mqttClient
import os
import shutil
import glob

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

log.info("start vpnCheck Version 0.6")

nodeName = "wohnz"
sndTopic = "evt/" + nodeName + "/vpn"
sbsTopic = "cmd/" + nodeName
vpnActive = False 

broker_address= "localhost"  #Broker address
broker_port = 1883                        #Broker port


Connected = False   #global variable for the state of the connection
  
def on_connect(client, userdata, flags, rc):
	if rc == 0:
		global Connected                #Use global variable
		Connected = True                #Signal connection
		client.subscribe(sbsTopic + "/#")
		log.debug("subscribed: " + sbsTopic + "/#")
	else:
		log.info("Connection failed")

def sendStatus():
	if Connected == False:
		connectMqtt()
	if Connected == False:
		return
	country = 'de'
	p = run( [ 'ip', 'link', 'sh', 'tun0'] )
	if p.returncode == 0:
		idFile = open('/etc/openvpn/readme.txt', 'r')
		country = idFile.readline().strip()
		idFile.close()
	try:
		client.publish(sndTopic, country)
	except:
		log.warning("could not publish to " + broker_address + " Port: " + str(broker_port))


def on_message(client, userdata, message):
	log.info("Message received: "  + message.payload)

def on_vpn(client, userdata, msg):
	global vpnActive
	payload = (msg.payload).decode('utf-8')
	log.debug("on_vpn: " + payload)
	
	oldFiles = glob.glob('/etc/openvpn/*')
	newDir = '/etc/openvpn/' + payload + '/*' 
	newFiles = glob.glob(newDir)
	
	p = run( [ 'systemctl', 'stop', 'openvpn'] )
	
	for delFile in oldFiles:
		try:
			if os.path.isfile(delFile):
				os.remove(delFile)
		except:
			log.warnig("Error while deleting file : " + delFile)

	destDir = '/etc/openvpn'
	for cpFile in newFiles:
		try:
			if os.path.isfile(cpFile):
				shutil.copy(cpFile, destDir)
		except:
			log.warnig("Error while coping file : " + cpFile)

	vpnActive = False
	if payload != "de" :
		p = run( [ 'systemctl', 'start', 'openvpn'] )
		vpnActive = True
	time.sleep(10)
	sendStatus()

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
	client = mqttClient.Client("Python1")               #create new instance
	client.on_connect= on_connect                      #attach function to callback
	client.message_callback_add(sbsTopic + "/vpn", on_vpn)
	client.on_message = on_message                      #attach function to callback

	connectMqtt()

	try:
		while True:
			sendStatus()
			time.sleep(60)
			p = run( [ 'ip', 'link', 'sh', 'tun0'] )
			if p.returncode != 0:
				if vpnActive == True:
					log.info("restart openvpn")
					p = run( [ 'systemctl', 'stop', 'openvpn'] )
					p = run( [ 'systemctl', 'start', 'openvpn'] )

	except KeyboardInterrupt:
		print("exiting")
		client.disconnect()
		client.loop_stop()

if __name__ == '__main__':
	import sys
	sys.exit(main())
