#!/usr/bin/env python

'''
get-pip.py
pip install flask_restful
pip install pyserial
pip install requests
pip install eventlet
pip install python-simplexml
'''
import math
import serial
import re
import requests
import sys
import datetime
#import traceback
#import pdb
import time
import os
#import shutil
#import urlparse
import eventlet

from flask import make_response, Flask
from flask_restful import Resource, Api
from simplexml import dumps

import logging
logging.basicConfig(filename='ProfaluxApi.log',level=logging.DEBUG,format='%(asctime)s:%(levelname)s %(message)s')
logging.warning('Starting Profalux API')


def delai():
  time.sleep(0.2)

def send_order (order):
  global line
  global EUI_dongle
  ser.write(order)
  line = ""
  logging.debug(order)
  while ("OK" not in line):
    delai()
    line = ser.readline()
    logging.debug(line)
    if ("Telegesis" in line):
      delai()
      line = ser.readline()
      logging.debug(line)
      delai()
      line = ser.readline()
      EUI_dongle = line
      EUI_dongle = EUI_dongle.replace("\r","")
      EUI_dongle = EUI_dongle.replace("\n","")
      logging.debug(line)
      line = ""




## Initialisation du Dongle Telgesys
ser = serial.Serial ('/dev/ttyUSB0', 19200, timeout=1)
logging.debug(ser.name)             
line = ""                  
device = list()            
EUI_dongle = ""            
eventlet.monkey_patch()    


global ArrVolets
ArrVolets= {}
with open('/domotique/ProfaluxApi/zigbee_devices.txt') as devices:
  for line in devices:
    Volet={}
    line = line.rstrip()

    VoletId= line.split('|')[0]
    VoletEndPoint = line.split('|')[1]
    VoletName = line.split('|')[2]
    Volet["Id"] =   VoletId
    Volet["EndPoint"] =  VoletEndPoint

    ArrVolets[VoletName] = Volet

logging.debug(ArrVolets)

## API RESTFUL
def output_xml(data, code, headers=None):
    """Makes a Flask response with a XML encoded body"""
    resp = make_response(dumps({'response' :data}), code)
    resp.headers.extend(headers or {})
    return resp

app = Flask(__name__)
api = Api(app,default_mediatype='application/xml')
api.representations['application/xml'] = output_xml



class Volets(Resource):
  '''def __init__(**kwargs):
        # smart_engine is a black box dependency
        self.ArrVolets = kwargs['ArrVolets']
   '''    
  def get(self, VoletName, Pourcentage):
    global ArrVolets
    # Retourne le status du volet 
    a=0.00081872
    b=0.2171167
    c=-8.60201639

    with eventlet.Timeout(5, False):
      delai()
      #logging.debug(line)
      ser.write("AT+READATR:" + ArrVolets[VoletName]['Id'] + "," + ArrVolets[VoletName]['EndPoint'] + ",0,0008,0000\r")
      receive=""
      logging.debug("1 " + VoletName)
      while ("OK" not in receive):
        receive = ser.readline()
        logging.debug("RECEIVED before while:" + receive)
        delai()
        #while (("RESPATTR" and ArrVolets[VoletName]['Id']) not in receive):
        while ("RESPATTR" not in receive):
          delai()
          receive = ser.readline()
          logging.debug("RECEIVED:" + receive)
        receive = receive.rstrip()
        receiveSplit=receive.split(',')
        logging.debug(receiveSplit)
        level = int(receiveSplit[5],16)
        logging.debug("Raw level:" + str(level))
        level = int(level * level * a + level * b + c)
        
        #level = int(math.ceil(level / 10.0)) * 10
        logging.debug("level:" + str(level))
        if level < 0 :
          level = 0
        elif level >10:
          level =int(round(level,-1))
        logging.debug(VoletName + " est au niveau " + str(level) + " \n")
        #level = int(level * 32 / 100)
          

    return {'level': level}
    
  def put(self, VoletName, Pourcentage):
    # Positionne le volet a un certain niveau
    logging.debug('Serial Device:' + ser.name)
    
    if Pourcentage == 0: # Fermer/Descendre le Volet
      with eventlet.Timeout(5, False):
        ser.write("AT+LCMV:" + ArrVolets[VoletName]['Id'] + "," + ArrVolets[VoletName]['EndPoint'] + ",0,1,01,FF\r")
        #ser.write("AT+LCMV:" + "0000" + "," + "01" + ",0,1,00,FF\r")
        receive = ""
        delai()
        while ("DFTREP" not in receive):
          receive = ser.readline()
          logging.debug(receive)
          delai()
        receive = receive.rstrip()
        if (receive.split(',')[4] != "00"):
          logging.debug("Transmit KO to " + VoletName + "\n")
          return{'status': 'NOK'}
        else:
          logging.debug("Transmit OK to " + VoletName + "\n")
          return{'status': 'OK'}


    elif Pourcentage == 100: # Ouvrir/Monter le Volet
      with eventlet.Timeout(5, False):
        ser.write("AT+LCMV:" + ArrVolets[VoletName]['Id'] + "," + ArrVolets[VoletName]['EndPoint'] + ",0,1,00,FF\r")
        receive = ""
        delai()
        while ("DFTREP" not in receive):
          receive = ser.readline()
          logging.debug(receive)
          delai()
        receive = receive.rstrip()
        if (receive.split(',')[4] != "00"):
          logging.debug("Transmit KO to " + VoletName + "\n")
          return{'status': 'NOK'}
        else:
          logging.debug("Transmit OK to " + VoletName + "\n")
          return{'status': 'OK'}
    ## sinon ouvrir a %
    else:
      with eventlet.Timeout(5, False):
        a = -0.0084
        b = 3.04
        c = 35 
        level = Pourcentage * Pourcentage * a + Pourcentage * b + c 
        level = int(level)
        level = format(level,'02X')
        ser.write("AT+LCMVTOLEV:" + ArrVolets[VoletName]['Id'] + "," + ArrVolets[VoletName]['EndPoint'] + ",0,0," + level + ",000F\r")
        receive = ""
        delai()
        while ("DFTREP" not in receive):
          receive = ser.readline()
          logging.debug(receive)
          delai()
        receive = receive.rstrip()
        if (receive.split(',')[4] != "00"):
          #print receive.split(',')[4]
          logging.debug("Transmit KO to " + VoletName + "\n")
          return{'status': 'NOK'}
        else:
          logging.debug( "Transmit OK to " + VoletName + "\n")
          return{'status': 'OK'}
    
    return {'hello': str(VoletName) + ' ' + str(Pourcentage) + "%"}

class GrpVolets(Resource):
  def put(self, VoletName):
    return {'hello': VoletName}


api.add_resource(Volets, '/volet/<VoletName>/<int:Pourcentage>')
#api.add_resource(GrpVolets, '/grpvolet/<GrpVoletName>',resource_class_kwargs={ 'ArrVolets': ArrVolets })

if __name__ == '__main__':
  app.run(debug=True, use_reloader=False,host='0.0.0.0',port=5010)
  
