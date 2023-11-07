#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-
#
#  aioSerialMqtt.py
#  
#  erster Entwurf einer auf asyncio beruhenden Serial-MQTT-Bridge
#  der noch nicht läuft aber zumindest im Prinzip funkionieren sollte
#  
#

import serial
import asyncio
import aiomqtt

mqttHost = "localhost"
mqttTopics = ["cmd/#", "inf/#"]
serialDev = '/dev/ttyUSB0'
serBaudrate = 115200

async def heartbeat(interval):
    while True:
        print("hearbeat")
        await asyncio.sleep(interval)

async def readSerial(ser, mqtt):
    reading = False
    inTxt = ""
    while True:
        inBytes = ser.read()
        if inBytes:
            try:
                txt = inBytes.decode()    # Converting Byte Strings into unicode strings
            except:
                txt =""
            if txt.find(">") != -1:        # -1 if not found
                l = txt.split(">")
                inTxt = l[len(l)-1]
                reading = True
            else:
                if reading :
                    inTxt = inTxt + txt
            if inTxt.find("\n") != -1:
                reading = False
                mqttList = inTxt.split("\n")[0].split(":")
                inTxt = ""
                try:
                    if len(mqttList) == 1:
                        print("to publish Topic: %s", mqttList[0])
#                        await mqtt.publish(mqttList[0])

                    elif len(mqttList) == 2:
                        print("to publish Topic: %s : %s", mqttList[0], mqttList[1])
#                        await mqtt.publish(mqttList[0], payload=mqttList[1])
                except aiomqtt.MqttError as e: 
                    #logging.warning("MQTT error: %s", e)
                    pass
        await asyncio.sleep(0)

async def readMQTT(ser, mqtt):
    while True:
        try:
            async with mqtt:
#                logging.info("MQTT connected to %s : %i", mqttHost, mqttPort)
                async with mqtt.messages() as messages:
                    for subscription in mqttTopics:
                        await mqtt.subscribe(subscription)
 #                       logging.info("MQTT subscribed: " + subscribeTopic)
                    async for message in messages:
                        txt= message.topic + ":" + message.payload
                        ser.write(txt.encode())
        except aiomqtt.MqttError as e:
#            logging.warning("MQTT not connected, Error: %s", e)
            await asyncio.sleep(5)

async def main():
    mqttClient = aiomqtt.Client(mqttHost)

    noSerial = True
    while noSerial:
        try:
            ser = serial.Serial(serialDev, serBaudrate, timeout=0)
            ser. reset_output_buffer()
            noSerial = False
        except Exception as e:
            print("serial Error retry : \n %i", e)
            await asyncio.sleep(5) 

    asyncio.create_task(readSerial(ser, mqttClient))
    asyncio.create_task(readMQTT(ser, mqttClient))
    asyncio.create_task(heartbeat(5))

    while True:                                     # run forever
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
