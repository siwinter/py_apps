import asyncio
import aiohttp
import re
import logging


#logLevel = logging.DEBUG
#logFile = 'myApp.log'
#logFormat = ('[%(asctime)s] %(levelname)-8s %(filename)-12s %(message)s')

#logger = logging.getLogger(__name__)
#logging.basicConfig(
#    filename=logFile,
#    level=logLevel,
#    handlers=[journal.JournaldLogHandler()],
#    format=logFormat)

async def publish(queue):
    while True:
        message = await queue.get()
        print("publishing : " + message)
        logging.info("publishing: " + message)

priceList = {}
async def getPrices(stationID):
    global priceList
    priceList = {}
    url = 'https://www.clever-tanken.de/tankstelle_details/' + petrolStationID
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
                else:
                    logging.warning("No petrol prices : HTTP-Response status : %s", response.status)
    except Exception as e: 
        logging.warning("No petrol prices : HTTP-Error: %s", e)
        priceList = {}
    return priceList

async def startSensor(stationID, queue, interval) :
    logging.info("Sensor started")
    while True :
        priceList = await getPrices(stationID)
        payload =  "{"
        for key in priceList:
            payload = payload + "\"" + key + "\":\"" + priceList[key] + "\","
        payload = payload[0:-1] +"}"
        try: 
            queue.put_nowait("tele/petrolPrices:" + payload)
        except Exception as e:
            logging.warning("Queue Error %s", e)
        await asyncio.sleep(interval * 60)

petrolStationID = '56417'  # Globus Hattersheim

async def start():
    while True :
        aQueue = asyncio.Queue()
        async with asyncio.TaskGroup() as tg:
            tg.create_task(publish(aQueue))
            tg.create_task(startSensor(petrolStationID, aQueue, 1))

def main():
    asyncio.run(start())

if __name__ == "__main__":
    main()
