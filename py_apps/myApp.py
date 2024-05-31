import rainradar
import petrolPrice
import serial2mqtt
import vpnCtrl
import asyncio
import aiomqtt
import logging

logLevel = logging.DEBUG
logFile = 'myApp.log'
logFormat = ('[%(asctime)s] %(levelname)-8s %(filename)-12s %(message)s')

#logger = logging.getLogger(__name__)
logging.basicConfig(
    filename=logFile,
    level=logLevel,
#    handlers=[journal.JournaldLogHandler()],
    format=logFormat)

#broker = "192.168.10.10"
broker = "localhost"
rainLocation = ''
#rainLocation = '/deutschland/hattersheim-am-main/hattersheim/DE0004242.html'
petrolStationID = ''
#petrolStationID = '56417'  # Globus Hattersheim
#serialTopic =""
serialTopic ="cmnd/radio/#"

async def sendTest(txt) :
    print("Test :" + txt)

async def distributeMqtt(mClient) :
    logging.info("distributing MQTT")
    async for message in mClient.messages:
        for key in subscriptions :
            if message.topic.matches(key):
                await subscriptions[key](str(message.topic) + ":" + str(message.payload))

async def publishMqtt(queue,mClient) :
    logging.info("publishing MQTT")
    while True:
        msg = await queue.get()
        m = msg.split(":", 1) 
        await mClient.publish(m[0], payload=m[1])
        logging.debug("publishing: " + msg)

async def publishPrnt(queue) :
    logging.info("publishing print")
    while True:
        print("publish: " + await queue.get())


subscriptions = {"myApp/#" : sendTest ,
                 "cmnd/vpn/set" : vpnCtrl.setCountry,
                 "cmnd/radio/#" : serial2mqtt.sendMsg}

async def main():
    while True :
        aQueue = asyncio.Queue()
        async with aiomqtt.Client(broker) as client:
            async with asyncio.TaskGroup() as tg: 
                tg.create_task(publishMqtt(aQueue, client))
#                tg.create_task(publishPrnt(aQueue))
                if rainLocation != "" :
                    tg.create_task(rainradar.startSensor(rainLocation, aQueue, 5))
                if petrolStationID != "" :
                    tg.create_task(petrolPrice.startSensor(petrolStationID, aQueue, 5))
                if serialTopic != "" :
                    tg.create_task(serial2mqtt.startSerial(aQueue))
                for key in subscriptions :
                    await client.subscribe(key)
                tg.create_task(distributeMqtt(client))
    
if __name__ == "__main__":
    asyncio.run(main())