#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-
#
#  vpnControll.py
#  Skript zur Änderung von VPN-Tunnels
#  Das Script muss mit root-Rechten gestartet werden.
#  In den dictionaries startCmds und stopCmds sind die Befehle einzutragen, die ausgefürt
#  werden müssen, um die vorgesehenen Tunnel ab- bzw. aufzubauen.
#
#  Das Sript testet mit Hilfe zweier URLs welcher Tunnel aktiv ist.
#  
#  Empfängt das Skript ein Länderkürzel, wird der bestehende Tunnel herunter-
#  gefahren und der neue gestartet 
#
#  Nach dem Connect wird das aktuelle VPN-Ziel übermittelt.
#  Danach wird in Endlosschleife receive aufgerufen, um ggf. das Ziel zu ändern.
#  Der Timeout alle 60 Sekunden wird verwendet, um das aktuelle Ziel zu ermitteln.
#  Beim Diconnect kehrt der Receive-aufruf ebenfalls zurück aber mit leerem String.
#  In diesem Fall wird ein Reconnect versucht.

import socket
import time
import subprocess
import json

countries = ["de", "es","us"]
country = ""
host = "localhost"
port = 1818
timeout_seconds = 60

startCmds   = {
	"de" : [['wg-quick','up','wg0']] ,
	"us" : [['systemctl', 'start', 'openvpn@CG_US'],['wg-quick','up','wg1']] ,
	"es" : [['wg-quick','up','wg1']]}
stopCmds = {
	"de" : [['wg-quick','down','wg0']] ,
	"us" : [['systemctl', 'stop', 'openvpn@CG_US'],['wg-quick','down','wg1']] ,
	"es" : [['wg-quick','down','wg1']]}

def getCountry():
	global country
	cmd1 = ['curl','ifconfig.co/country-iso']		# liefert Countrycode der public IP-Address
	cmd2 = ['curl','ipinfo.io']		# liefert JSON-Info about public IP-Adress
	print("get IP from cmd1")
	try:
		p = subprocess.run(cmd1,stdout=subprocess.PIPE)
		if p.returncode == 0:
			input = p.stdout.decode('utf-8').split('\n')[0].lower()	# Ergebnis in Kleinbuchstaben
			if input in countries:
				print("store country code from cmd1")
				country = input
			else:
				print("get IP from cmd2")
				p = subprocess.run(cmd2,stdout=subprocess.PIPE)
				if p.returncode == 0:
					dict = json.loads((p.stdout.decode('utf-8')))
					input = dict.get("country").lower()
					if input in countries:
						print("store country code from cmd2")
						country = input
	except:
		print("exception while looking for countrycode")
	sock.sendall(country.encode())

def setCountry(cn):
	global country
	error = 0
	for cmd in stopCmds.get(country):
		p = subprocess.run(cmd)
		if p.returncode != 0:
			print("error stop VPN to " + country)
		time.sleep(1)
	for cmd in startCmds.get(cn):
		p = subprocess.run(cmd)
		if p.returncode != 0:
			print("error start VPN to " + cn)
			error = 2
		else:
			print("store country code from parameter")
			country = cn
		time.sleep(1)
	if error == 0:
		sock.sendall(cn.encode())

def connectSocket():
	connected = False
	print("connecting")
	while not connected :
		try:
			global sock
			sock = socket.create_connection((host, port))
			sock.settimeout(timeout_seconds)                #timeout auch für receive
			connected = True
		except ConnectionRefusedError:
			time.sleep(5)
	
	print("connected")

def main():
	connectSocket()
	getCountry()
	while True:
		try:
			data = sock.recv(4096).decode("UTF-8")
			if data =="" :
				connectSocket()
			else:
				print("received: " + data)
				setCountry(data)
		except socket.timeout:
			getCountry()

if __name__ == '__main__':
	import sys
	sys.exit(main())
