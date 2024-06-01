#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-
#
#  vpnCtrl.py
#  Skript zur Änderung von VPN-Tunnels
#  Das Script muss mit root-Rechten gestartet werden.
#  In den dictionaries startCmds und stopCmds sind die Befehle einzutragen, die ausgefürt
#  werden müssen, um die vorgesehenen Tunnel ab- bzw. aufzubauen.
#
#  Das Sript ermittelt mit Hilfe der Webseite https://ifconfig.co/country-iso das Land, in dem
#  der Zugang zu Internet erfolgt (und damit den bestehenden VPN-Tunnel). Der Ländercode wird
#  regelmäßig ermittelt
#  
#  Zur Änderung des Landes wird der bestehende Tunnel herunter gefahren und ein neuer gestartet.
#  Die notwendigen Befehle stehen in den Dictionaries stopCmds bzw startCmds
#
import asyncio
import aiohttp
import logging

logger = logging.getLogger(__name__)

country = "de"

nstartCmds   = {
    "de" : ['wg-quick up wg0'] ,
	"us" : ['systemctl start openvpn@CG_US','wg-quick up wg1'] ,
	"es" : ['wg-quick up wg1']}
nstopCmds = {
	"de" : ['wg-quick down wg0'] ,
	"us" : ['systemctl stop openvpn@CG_US' , 'wg-quick down wg1'] ,
	"es" : ['wg-quick down wg1']}

startCmds   = {
    "de" : ['mkdir de','touch de/de.txt'] ,
    "us" : ['mkdir us','touch us/us.txt'] ,
    "es" : ['mkdir es','touch es/es.txt'] }
stopCmds = {
	"de" : ['rm -r de'] ,
	"us" : ['rm -r us'] ,
	"es" : ['rm -r es']}

async def publish(queue):
    while True:
        message = await queue.get()
        print("publishing : " + message)
        logger.info("publishing: " + message)

async def setVPN(cmd,queue=None):
    newCountry = cmd.split(":", 1)[1]      # cmnd/vpn:us  --> us
    global country
    logger.debug("setVPN to " + newCountry)
    if newCountry in startCmds.keys() :
        for cmd in stopCmds.get(country):
            logger.debug(cmd)
            process = await asyncio.create_subprocess_shell(cmd)
            await process.wait()
        for cmd in startCmds.get(newCountry):
            logger.debug(cmd)
            process = await asyncio.create_subprocess_shell(cmd)
            await process.wait()
        country = newCountry
        if queue != None :
            queue.put_nowait("info/vpn:" + newCountry)
    else :
        logger.warning("setVPN unknow newCountry")

async def getCountry():
    newCountry = ""      
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://ifconfig.co/country-iso') as response:
                if (response.status == 200):
                    newCountry = await response.text()
                    if len(newCountry) == 3 :                         # normally text has 3 characters 
                        newCountry = newCountry.lower()[0:2]          # last one has to be cut away
                    else :
                        logger.warning("unkown country " + newCountry)
                        return "unknown"
                else :
                    logger.warning("HTTP return " + str(response.status))
                    return "unknown"                
    except aiohttp.ClientError as e:
        logger.error(f"HTTP error {e}")
        return "unknown"
    return newCountry

async def startSensor(queue, interval) :
    while True :
        global country
        ctr = getCountry()
        try: 
            queue.put_nowait("tele/vpn:" + ctr)
        except Exception as e:
            logger.warning("Queue Error %s", e)
        await asyncio.sleep(interval * 60)

interval = 1
async def main():
    while True :
        aQueue = asyncio.Queue()
        async with asyncio.TaskGroup() as tg:
            tg.create_task(publish(aQueue))
            tg.create_task(startSensor(aQueue, interval))