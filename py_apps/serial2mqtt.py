import asyncio
import aioserial
import logging

logger = logging.getLogger(__name__)

serialPorts = ["/dev/ttyUSB0","/dev/ttyUSB1","/dev/ttyUSB2","/dev/ttyACM0","/dev/ttyACM1","/dev/ttyACM2"]
baudRate = 9600

sendQueue = asyncio.Queue()

async def publisher(queue) :
    while True :
        msg = await queue.get()
        logger.debug("to publish " + msg)

async def heartbeat() :
    b = 0
    await asyncio.sleep(5)
    while True :
        msg = "cmnd/test/set: " + str(b)
        b = b+1
        await sendMsg(msg)
        await asyncio.sleep(30)

async def sendMsg(msg) :
    logger.debug("sendMsg: " + msg)
    sendQueue.put_nowait(msg)

async def sendSerial(serial) :
    try:
        while True :
            logger.debug("send Serial: waiting for msg")
            msg = await sendQueue.get()
            msg = ">" + msg + ";"
            msg = msg.encode()
            await serial.write_async(msg)
    except asyncio.CancelledError:
        logger.info("sendSerial canceled")


async def startSerial(queue) :
    interfaceIndex = 0
    while True :
        try :
            logger.debug("startSerial connection to " + serialPorts[interfaceIndex])
            task = None
            aSerial: aioserial.AioSerial = aioserial.AioSerial(  # open serial interface
                port=serialPorts[interfaceIndex],
                baudrate=baudRate)
                        
            task = asyncio.create_task(sendSerial(aSerial)) # start task to send msg via serial interface
            while True:
                inMsg = await aSerial.readline_async()      # listening at serial interface
                inMsg = inMsg.decode()                      # convert Bytes to String
                logger.debug("serial received: " + inMsg)
                if inMsg[0] == "/" : inMsg = inMsg[1:]      # cut first "/"
                queue.put_nowait(inMsg)                     # forward msg to (MQTT-)publisher

        except Exception as e:
                if task != None : task.cancel()
                interfaceIndex = interfaceIndex + 1
                if interfaceIndex >= len(serialPorts) : interfaceIndex = 0
                logger.error("startSerial Error: ", e)
                await asyncio.sleep(5)

async def start():
    while True :
        aQueue = asyncio.Queue()
        async with asyncio.TaskGroup() as tg:
#            tg.create_task(heartbeat())
            tg.create_task(publisher(aQueue))
            tg.create_task(startSerial(aQueue))

def main():
    asyncio.run(start())

if __name__ == "__main__":
    main()