#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-
#
#  webInfo.py
#
#  python3 webInfo.py <path to configfile>
#
#  Ursprünglich war das Skript nur dazu gemacht von der Webseite www.wetter.com Inforamtionen
#  über die Regensituation an einem Ort zu holen.
#  inziwschen holt es außerdem von www.clever-tanken.de die aktuellen Preise einer Tankstelle
#  
#   tele/<mqttTopic>/rainAlarm : on || off
#   
#   tele/<mqttTopic>/petrolPrices : {"Diesel":"1.66","Super_E10":"1.69",
#                                    "Super_E5":"1.75","SuperPlus":"1.83"}
#   
#
  
import sys
import re
from pathlib import Path
import time
import logging
import asyncio
import aiohttp
import aiomqtt
import configparser
from aiohttp import web

#-----------------------------------------------------------------------
#  Config
#-----------------------------------------------------------------------
# default
serverPort  = 8095
mqttHost      = 'localhost'
#mqttHost    = '192.168.10.10'
mqttPort    = 1883
mqttTopic   = 'gths'
logLevel    = logging.INFO
#logLevel    = logging.DEBUG
logFormat = ('[%(asctime)s] %(levelname)-8s %(message)s')
logFile   = ""
locationURI = ''
#locationURI = '/deutschland/niederkruechten/kapelle/DE3205889.html'
#locationURI = '/deutschland/hattersheim-am-main/hattersheim/DE0004242.html'
petrolStationID = ''
#petrolStationID = '56417'  # Globus Hattersheim

def configApp():
    config = configparser.ConfigParser()
    global serverPort, mqttHost, mqttPort, mqttTopic, logLevel, logFile, locationURI, petrolStationID
    try:
        config.read(sys.argv[1])
    except :
        try:
            Path(logFile).resolve()
            logging.basicConfig(level=logLevel,
                                filename=logFile,
                                format=logFormat,)
        except:
            logging.basicConfig(level=logLevel,
                                format=logFormat,)

        logging.info("starting with default Params")
        return
    try:
        logLev    = config["LOGGING"]["level"]
        if logLev == "DEBUG":
            logLevel    = logging.DEBUG
        if logLev == "INFO":
            logLevel    = logging.INFO
        if logLev == "WARNING":
            logLevel    = logging.WARNING
        if logLev == "ERROR":
            logLevel    = logging.ERROR
        if logLev == "CRITICAL":
            logLevel    = logging.CRITICAL
    except: pass
    try:
        logFile = config["LOGGING"]["file"]
    except: pass
    try:
        serverPort = int(config["WEB-SERVER"]["port"])
    except: pass
    try:
        mqttIP = config["MQTT"]["host"]
    except: pass
    try:
        mqttPort = int(config["MQTT"]["port"])
    except: pass
    try:
        mqttTopic = config["MQTT"]["topic"]
    except: pass
    try:
        locationURI = config["LOCATION"]["uri"]
    except: pass
    try:
        petrolStationID = config["LOCATION"]["petrolStation"]
    except: pass
    try:
        Path(logFile).resolve()
        logging.basicConfig(level=logLevel,
                            filename=logFile,
                            format=logFormat,)
    except:
        logging.basicConfig(level=logLevel,
                            format=logFormat,)
    logging.info("starting with config file %s", sys.argv[1])

#-----------------------------------------------------------------------
#  Global Variables
#-----------------------------------------------------------------------
rainState = 0

priceList = {}

#-----------------------------------------------------------------------
#  MQTT
#-----------------------------------------------------------------------
mqttClient = None

async def publishRain():
    if rainState == 0: msg = "off"
    else: msg = "on"
    topic = "tele/" + mqttTopic + "/rainAlarm"
    try:
        await mqttClient.publish(topic, payload = msg)
        logging.debug("MQTT published: " + topic + ":" + msg)
    except aiomqtt.MqttError as e: 
        logging.warning("MQTT error: %s", e)

async def publishPriceList():
    payload =  "{"
    for key in priceList:
        payload = payload + "\"" + key + "\":\"" + priceList[key] + "\","
    payload = payload[0:-1] +"}"
    topic = "tele/" + mqttTopic + "/petrolPrices"
    try:
        await mqttClient.publish(topic, payload)
        logging.debug("MQTT published: " + topic + ":" + payload)
    except aiomqtt.MqttError as e: 
        logging.warning("MQTT error: %s", e)


async def mqttReceive(client):
    while True:
        try:
            async with client:

                logging.info("MQTT connected to %s : %i", mqttHost, mqttPort)
                async with client.messages() as messages:
                    subscribeTopic = "cmnd/"+mqttTopic +"/#"
                    await client.subscribe(subscribeTopic)
                    logging.info("MQTT subscribed: " + subscribeTopic)
                    async for message in messages:
                        logging.debug("MQTT-Msg received: %s", message.topic)
                        if message.topic.matches("cmd/" + mqttTopic +"/rainAlarm/get"):
                            await publishRain()
        except aiomqtt.MqttError as e:
            logging.warning("MQTT not connected, Error: %s", e)
            await asyncio.sleep(5)

#-----------------------------------------------------------------------
#  HTTP-Server
#-----------------------------------------------------------------------
returnTxt = [ "es regnet nicht",
            "es regnet innerhalb der nächsten 15 min",
            "es regnet gerade",
            "es regnet bald wieder"]
async def mainHandler(request):
    logging.debug("HTTP-Request received")
    if rainState < 4:
        return web.Response(text= returnTxt[rainState])
    else:
        return web.Response(text= "keine Meldung")

async def startHTTPServer():
    # set up the web server
    try:
        app = web.Application()
        app.router.add_get('/', mainHandler)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, port=serverPort)
        await site.start()
        logging.info("HTTP-Server started on port %i", serverPort)
    except Exception as e:
        logging.error("HTTP-Server Error: %", e)

#-----------------------------------------------------------------------
#  Web-Scrapper
#-----------------------------------------------------------------------
#  RainState
#-----------------------------------------------------------------------
async def checkRainState():
    rainEndTime = time.time() - 1
    rainAlarm = False

    rainVals = {            # colours of different rain levels / 0 = no rain
        "fff": 0,
        "bfd4ff": 1,
        "6699ff": 2,
        "004ce5": 3,
        "002673": 4,
        "ffa800": 5,
        "e60000": 6 }

    url = 'https://www.wetter.com' + locationURI + '#niederschlag'
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    logging.debug("HTTP-Get to : %" + url)
                    logging.debug("HTTP-Response status : %s", response.status)
                    if (response.status == 200):
# analyse webpage from www.wetter.com and
# prepare dictionary {'hh:mm' : rainvalue, ...}
                        txt = await response.text()
                        rains = {}
                        i= 0
                        while True:                             # create dictionary {"hh:min":rainvalue}
                            i = txt.find("nowcast-table-item", i)
                            if i>0 :
                                i = txt.find("<span>", i) + 6	# find time  (17:20)
                                j = txt.find("</span>", i)
                                t = (txt[i:j])
                                i = txt.find("#", i) + 1		# find rain colour
                                j = txt.find(";", i)
                                try :
                                    r = rainVals[txt[i:j]]		# get rain value from local table of values
                                except :
                                    r = 1
                                rains[t]=r						# add new key:value (exp: "17:20" : 2)
                            else :
                                break
                        logging.debug("expected rain: %s", rains)
# find next expected rain period (nextrain = -1 -> no rain expected)
                        timeKeys = []
                        now = (time.localtime().tm_hour *60) + (time.localtime().tm_min // 5 *5) #Anzahl der Minuten des Tages auf 5min gerundet
                        
                        for x in range(13):
                            timeKeys.append(str(now//60).zfill(2) + ":" + str(now%60).zfill(2)) #zfill für führende Nullen (1:2 -> 01:02))
                            now = (now + 5) % (24*60) # Werte 00:00 - 23:59 (Falls durch Addition nächster Tag erreicht wird)

                        nextRain = -1
                        i = -1
                        for t in timeKeys:
                            i = i + 1
                            if t in rains:
                                if rains.get(t) > 0 :
                                    nextRain = i        # next rain expected in i+5 minx
                                    break
                        if i==-1:
                            logging.warning("no rain forcast available")

                        global rainState
                        if (nextRain > -1) and (nextRain < 4): # next Rain within 15 mins
                            rainState = 1
                            logging.debug("rainAlarm ON (raining)")
                            rainEndTime = time.time() + 15*60 
                        elif rainEndTime > time.time(): # rained at least 15 mins ago
                            rainState = 2
                            logging.debug("rainAlarm ON (has rained)")
                        elif rainAlarm and nextRain > 0: # rainalarm on will rain within 60 mins again
                            rainState = 3
                            logging.debug("rainAlarm ON (will rain again)")
                        else:
                            rainAlarm = False
                            rainState = 0
                            logging.debug("rainAlarm OFF (not raining)")
                        await publishRain()
                    else:
                        logging.warning("No rain forecast : HTTP-Response status : %s", response.status)
        except Exception as e: 
            logging.warning("No rain forecast : HTTP-Error: %s", e)
        await asyncio.sleep(5*60)
#-----------------------------------------------------------------------
#  PetrolPrice
#-----------------------------------------------------------------------
async def getPetrolPrices():
    global priceList
    priceList = {}
    url = 'https://www.clever-tanken.de/tankstelle_details/' + petrolStationID
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    logging.debug("HTTP-Get to : %" + url)
                    logging.debug("HTTP-Response status : %s", response.status)
                    if (response.status == 200):
# analyse webpage from www.clever-tanken.de
                        txt = await response.text()
                        fuels = re.findall('<div class="price-type-name">.*?</div>', txt)
                        prices = re.findall('<span id="current-price-.*?</span>', txt)
                        i = 0
                        for f in fuels:
                            price=prices[i][27:-7]
                            fuelType= f[29:-6].replace(" ", "_")

                            priceList[fuelType] = price
                            i = i+1
                        await publishPriceList()
                    else:
                        logging.warning("No petrol prices : HTTP-Response status : %s", response.status)
        except Exception as e: 
            logging.warning("No petrol prices : HTTP-Error: %s", e)
        await asyncio.sleep(5*60)


#-----------------------------------------------------------------------
#  Main
#-----------------------------------------------------------------------
async def startApp():
    configApp()
    global mqttClient                               # start MQTT-Client
    mqttClient = aiomqtt.Client(mqttHost)
    asyncio.create_task(mqttReceive(mqttClient))
    await startHTTPServer()                         # start HTTP-Server
    if len(locationURI) > 0 :
        asyncio.create_task(checkRainState())       # start Web-Scrapper
    if len(petrolStationID) >0 :
        asyncio.create_task(getPetrolPrices())      # start Web-Scrapper
    while True:                                     # run forever
        await asyncio.sleep(3600)

def main():
    asyncio.run(startApp())

if __name__ == "__main__":
    sys.exit(main())
