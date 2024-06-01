import py_apps
from py_apps import rainRadar
from py_apps import petrolPrice
from py_apps import vpnCtrl
from py_apps import serial2mqtt
from systemd import journal
import asyncio
import aiomqtt
import logging


logger = logging.getLogger(__name__)
logLevel = logging.INFO
#logFile = 'myApp.log'
logFormat = ('[%(asctime)s] %(levelname)-8s %(filename)-12s %(message)s')

logging.basicConfig(
#    filename=logFile,
    level=logLevel,
    handlers=[journal.JournaldLogHandler()],
    format=logFormat)

broker = "192.168.10.10"
#broker = "localhost"
#rainLocation = ''
rainLocation = '/deutschland/hattersheim-am-main/hattersheim/DE0004242.html'
#petrolStationID = ''
petrolStationID = '56417'  # Globus Hattersheim
#serialTopic =""
serialTopic ="cmnd/radio/#"

async def distributeMqtt(mClient) :
    logger.info("distributing MQTT")
    async for message in mClient.messages:
        for key in subscriptions :
            if message.topic.matches(key):
                await subscriptions[key](str(message.topic) + ":" + str(message.payload))

async def publishMqtt(queue,mClient) :
    logger.info("publishing MQTT")
    while True:
        msg = await queue.get()
        logger.debug("publishing: " + msg)
        m = msg.split(":", 1)
        if len(m) == 2 : await mClient.publish(m[0], payload=m[1])
        else : await mClient.publish(msg)

async def publishPrnt(queue) :              # for test purpose
    logger.info("publishing print")
    while True:
        print("publish: " + await queue.get())


subscriptions = {"cmnd/vpn/set" : vpnCtrl.setVPN,
                 "cmnd/radio/#" : serial2mqtt.sendMsg}
async def start():
    while True :
        aQueue = asyncio.Queue()
        async with aiomqtt.Client(broker) as client:
            async with asyncio.TaskGroup() as tg: 
                tg.create_task(publishMqtt(aQueue, client))
#                tg.create_task(publishPrnt(aQueue))
                if rainLocation != "" :
                    tg.create_task(rainRadar.startSensor(rainLocation, aQueue, 5))
                if petrolStationID != "" :
                    tg.create_task(petrolPrice.startSensor(petrolStationID, aQueue, 5))
                if serialTopic != "" :
                    tg.create_task(serial2mqtt.startSerial(aQueue))
                for key in subscriptions :
                    await client.subscribe(key)
                tg.create_task(distributeMqtt(client))

def main():
    asyncio.run(start())

if __name__ == "__main__":
    main()