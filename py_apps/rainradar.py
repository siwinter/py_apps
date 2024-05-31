import asyncio
import aiohttp
import time
import logging

logLevel = logging.DEBUG
logFile = 'myApp.log'
logFormat = ('[%(asctime)s] %(levelname)-8s %(filename)-12s %(message)s')

logger = logging.getLogger(__name__)
logging.basicConfig(
    filename=logFile,
    level=logLevel,
#    handlers=[journal.JournaldLogHandler()],
    format=logFormat)

async def publish(queue):
    while True:
        message = await queue.get()
        print()
        logging.info("publishing: " + message)

rainstate = 0

rainVals = {            # colours of different rain levels / 0 = no rain
    "fff": 0,
    "bfd4ff": 1,
    "6699ff": 2,
    "004ce5": 3,
    "002673": 4,
    "ffa800": 5,
    "e60000": 6 }

async def rainChecker(locationURI):

    rainEndTime = time.time() - 1
    rainAlarm = False

    url = 'https://www.wetter.com' + locationURI + '#niederschlag'
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
                    if rainState == 0: return "off"
                    else: return "on"
                else:
                    logging.warning("No rain forecast : HTTP-Response status : %s", response.status)
                    return "error"
    except Exception as e: 
        logging.warning("No rain forecast : HTTP-Error: %s", e)
        return "error"

async def startSensor(location, queue, interval) :
    logging.info("Sensor started")
    while True :
        msg = await rainChecker(location)
        try: 
            queue.put_nowait("tele/rainalarm:" + msg)
        except Exception as e:
            logging.warning("Queue Error %s", e)
        await asyncio.sleep(interval * 60)

interval = 1
location = '/deutschland/hattersheim-am-main/hattersheim/DE0004242.html'
async def main():
    while True :
        aQueue = asyncio.Queue()
        async with asyncio.TaskGroup() as tg:
            tg.create_task(startSensor(location, aQueue, interval))
            tg.create_task(publish(aQueue))

    
if __name__ == "__main__":
    asyncio.run(main())
