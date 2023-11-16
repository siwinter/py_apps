#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-
#
#  certServer.py
#  
#  Der Server erneuert die LetsEncrypt-Zertifikate (http://host:port/renew)
#  und liefert diese aus (http://host:port/privkey bzw. http://host:port/pubkey)
#  
#  Es weren nur Requests bekannter IP-Adressen bearbeitet.
#  Der Name der Domän ist die IP-Adresse zugeordnet. (siehe peers)
#
import sys
from pathlib import Path
import time
import logging
import asyncio
import aiohttp
import configparser
from aiohttp import web

#-----------------------------------------------------------------------
#  Config
#-----------------------------------------------------------------------
# default
serverPort  = 8095
servedHost  = 'localhost'
logLevel    = logging.INFO
#logLevel    = logging.DEBUG
logFormat = ('[%(asctime)s] %(levelname)-8s %(message)s')
logFile   = ""

def configApp():
    config = configparser.ConfigParser()
    global serverPort, mqttHost, mqttPort, mqttTopic, logLevel, logFile, locationURI
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
        serverHost = int(config["WEB-SERVER"]["host"])
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
#  HTTP-Server
#-----------------------------------------------------------------------
peers = {
        "192.168.206.4": "dsbg.mooo.com",
        "192.168.206.3": "gths.mooo.com",
        "192.168.206.2": "islc.mooo.com" }

async def renewHandler(request):
    logging.debug("HTTP-Request received")
    try:
        peername = request.transport.get_extra_info('peername')
        if peername is not None:
            host, port = peername

            domain = peers(host)
            logging.debug('renew cert for ' + domain)

            process = await asyncio.create_subprocess_exec('systemctl', 'stop', 'nginx')
            await process.wait()
            logging.debug('nginx stopped')
            process = await asyncio.create_subprocess_exec('certbot', 'certonly',  '--non-interactive', '--standalone', '--force-renewal', '--cert-name', domain)
            await process.wait()
            logging.debug('certs completed')
            process = await asyncio.create_subprocess_exec('systemctl', 'start', 'nginx')
            await process.wait()
            logging.debug('nginx stopped')
        else:
            return web.Response(status=403, body="403 Forbidden")
    except:
        logging.warning()
        return web.Response(status=400, body="400 Bad Request")
    
    return web.Response(text= "keine Meldung")

async def publicHandler(request):
    logging.debug("HTTP-Request received")
    try:
        peername = request.transport.get_extra_info('peername')
        if peername is not None:
            host, port = peername
            domain = peers(host)
            logging.debug('renew cert for ' + domain)
        else:
            return web.Response(status=403, body="403 Forbidden")
        certFile = '/etc/letsencrypt/live/' + domain + '/fullchain.pem'
        if not(Path(certFile).is_file()):
            return web.Response(status=404, body="404 Not Found")
        
        return web.FileResponse(certFile,headers={
                        'Content-Disposition': 'filename=crt.pem'})
    except:
        logging.warning()
        return web.Response(status=400, body="400 Bad Request")

async def privateHandler(request):
    logging.debug("HTTP-Request received")
    try:
        peername = request.transport.get_extra_info('peername')
        if peername is not None:
            host, port = peername
            domain = peers(host)
            logging.debug('renew cert for ' + domain)
        else:
            return web.Response(status=403, body="403 Forbidden")
        certFile = '/etc/letsencrypt/live/' + domain + '/fullchain.pem'
        if not(Path(certFile).is_file()):
            return web.Response(status=404, body="404 Not Found")
        
        return web.FileResponse(certFile,headers={
                        'Content-Disposition': 'filename=crt.pem'})
    except:
        logging.warning()
        return web.Response(status=400, body="400 Bad Request")
    
async def startHTTPServer():
    # set up the web server
    try:
        app = web.Application()
        app.router.add_get('/renew'  , renewHandler)
        app.router.add_get('/privkey', privateHandler)
        app.router.add_get('/pubkey' , publicHandler)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host=servedHost, port=serverPort)
        await site.start()
        logging.info("HTTP-Server started on port %i", serverPort)
    except Exception as e:
        logging.error("HTTP-Server Error: %", e)


#-----------------------------------------------------------------------
#  Main
#-----------------------------------------------------------------------
async def startApp():
    configApp()

    await startHTTPServer()                         # start HTTP-Serverr
    while True:                                     # run forever
        await asyncio.sleep(3600)

def main():
    asyncio.run(startApp())

if __name__ == "__main__":
    sys.exit(main())
