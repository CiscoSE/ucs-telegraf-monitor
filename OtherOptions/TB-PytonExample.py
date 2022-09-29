_LICENSE_= """
Copyright (c) 2022 Cisco and/or its affiliates.
This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at
               https://developer.cisco.com/docs/licenses
All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied.
"""

#import requests
from audioop import tostereo
from datetime import datetime
from distutils.command.install_egg_info import to_filename
from logging.config import dictConfig
from re import M
from symbol import power
import time
import base64
import json
import typing
import urllib.error
import urllib.parse
import urllib.request
from email.message import Message
import ssl
import os
import argparse
import csv

helpmsg = """
    This will poll power and temperature readings from a Cisco Stand-alone C series server using the Redfish API.
"""
argsParse = argparse.ArgumentParser(description=helpmsg)
argsParse.add_argument('-a', '--address',         action='store', dest='address',         default='',      help="System to get API Data from")
argsParse.add_argument('-u', '--user',            action='store', dest='username',        default='admin', help='User Name to access the API' )
argsParse.add_argument('-p', '--password',        action='store', dest='password',        default='',      help="Password for API Access")
argsParse.add_argument('-r', '--reportDirectory', action='store', dest="reportDirectory", default='./',    help="Location directory for files")
argsParse.add_argument('-c', '--count', type=int, action='store', dest='counter',         default='1',     help="Number of times to repeat")
argsParse.add_argument('-v',                      action='count', dest='verbose',         default=0,       help="Used for Verbose Logging")
argsParse.add_argument('--failCount',   type=int, action='store', dest='failCount',       default=10,      help="Number of times to retry a failed connection - Only applies when counter is set to 0")
args=argsParse.parse_args()

powerSupplyFields = ["PowerOutputWatts","LineInputVoltage","Name","PowerInputWatts","LastPowerOutputWatts"]
temperatureFields = ["TEMP_SENS_FRONT","DIMM_A1_TMP","DIMM_B1_TMP","DIMM_C1_TMP","DIMM_D1_TMP","DIMM_E1_TMP","DIMM_F1_TMP","DIMM_G1_TMP","DIMM_H1_TMP","P1_TEMP_SENS","PSU1_TEMP","PSU2_TEMP"]
failCount: int=args.failCount
bailout: bool=False
counter: int= args.counter
token: dict = {'X-Auth-Token': None,'Location': None}

class writeEvents():
    noColor = '\x1b[0m'
    INFO = '\033[32m'
    WARN = '\033[33m'
    FAIL = '\033[31m'
    def toScreen(self, msg: str, msgType: str='INFO', exitOnFail: bool=False):
        if msgType == 'INFO':
            print(f"[ {self.INFO}INFO{self.noColor} ] {msg}")
        elif msgType == 'WARN':
            print(f"[ {self.WARN}WARN{self.noColor} ] {msg}")
        elif msgType == "FAIL":
            print(f"[ {self.FAIL}FAIL{self.noColor} ] {msg}")
            if exitOnFail == True: 
                if token['Location'] != None:
                    httpRequest().clearAuthToken()
                exit()
        return

class Response(typing.NamedTuple):
    body: str
    headers: Message
    status: int
    error_count: int = 0
    def json(self) -> typing.Any:
        try:
            output = json.loads(self.body)
        except json.JSONDecodeError:
            output = ""
        return output



class csvProcessing():
    def fileTest(self,fileName):
        if args.verbose > 2: writeEvents().toScreen(msg="\tDoes this path exist?")
        if os.path.exists(fileName):
            if args.verbose > 2: writeEvents().toScreen(msg="\tFile Found.")
            return True
        else:
            if args.verbose > 2: writeEvents().toScreen(msg="\tFile Not Found")
            return False
        return

def processHeaders():
    if token['X-Auth-Token'] == None:
        base64EncodedAuth = base64.b64encode("{0}:{1}".format(args.username,args.password).encode('ascii')).decode('utf-8') 
        if args.verbose > 2: writeEvents().toScreen(msg="Base64 Encoded String: {0}".format(base64EncodedAuth))
        header = {"Authorization":"Basic {0}".format(base64EncodedAuth)}
    else:
        header = {"X-Auth-Token": "{0}".format(token["X-Auth-Token"])}
    return header

class powerSupplyProcessing():
    #def __init__(self):
    #    return
    def newOrOldCSV(self):
        powerSupplyFileName = "{0}{1}-powersupply.csv".format(args.reportDirectory,args.address)
        # For basic logging when some output is required.  
        if args.verbose > 0: writeEvents().toScreen(msg="Start Processing Power Supply Data - CSV Assignment Starting")
        if args.verbose > 1: writeEvents().toScreen(msg="Power Supply File Name: {}".format(powerSupplyFileName))
        if (csvProcessing().fileTest(powerSupplyFileName) == False):
            if args.verbose > 1: writeEvents().toScreen(msg="Creating a new file")
            powerSupplyFileObject = open(powerSupplyFileName, 'w')
            powerSupplyCSVWriter = csv.writer(powerSupplyFileObject)
            powerSupplyCSVWriter.writerow(['Time'] + powerSupplyFields)  
            return powerSupplyCSVWriter
        else:
            #TODO Check to see if we have the right fields in the file
            #TODO Rename the existing file if the fields are wrong, and return an object for a new file
            #TODO Return an object with the existing file if the fields are right.
            powerSupplyFileObject = open(powerSupplyFileName, 'a')
            powerSupplyCSVWriter = csv.writer(powerSupplyFileObject)
            return powerSupplyCSVWriter
    def pollPowerSupply(self):
        global failCount
        powerSupplyUrl="https://{0}/redfish/v1/Chassis/1/Power".format(args.address)
        powerSupplyResponse = httpRequest().getUrl(url=powerSupplyUrl,headers=(processHeaders()))
        if not (200 <= powerSupplyResponse.status < 300):
            # Failed to talk to the API
            if args.verbose > 0: writeEvents().toScreen(msg="Connection to API failed.\n\t{0}\n{1}".format(powerSupplyResponse.status,powerSupplyResponse.body),msgType="WARN")
            if args.count == 0 and failCount != 0:
                if args.verbose > 0: writeEvents().toScreen(msg="\t{0} retries remain before script exit".format(failCount),msgType="WARN")
                failAction = False
                failCount = failCount - 1
            else:
                # To many failures. Script exists
                failAction = True    
            writeEvents().toScreen(msg="",msgType='FAIL',exitOnFail=failAction)
            return
        else:
            #If we succeed at any point we reset the failure counter
            if failCount < args.failCount: 
                failCount = args.failCount
            self.writeJSONResponseToFile(powerSupplyResponse.body)
            #Write contents to CSV
        return
    def writeJSONResponseToFile(self,jsonResponse):
        now=datetime.now()
        date_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
        columnOrder = ['Time'] + powerSupplyFields
        for powerSupply in json.loads(jsonResponse)['PowerSupplies']:
            powerSupplyProperties = {'Time':"{0}".format(date_time_str)}
            for item in powerSupplyFields:
                if item in powerSupply:
                    powerSupplyProperties[item] = str(powerSupply[item])
                else:
                   powerSupplyProperties[item] = "No Data Present" 
            powerSupplyCSVObject.writerow([powerSupplyProperties.get(column, None) for column in columnOrder])
        return
class temperatureProcessing():
    #def __init__(self):
    #    return
    def newOrOldCSV(self):
        temperatureFileName = "{0}{1}-temperature.csv".format(args.reportDirectory,args.address)
        # For basic logging when some output is required.
        if args.verbose > 0: writeEvents().toScreen(msg="Start Processing Temperature Data - CSV Assignment Starting")
        if args.verbose > 1: writeEvents().toScreen(msg="Power Supply File Name: {}".format(temperatureFileName))
        if (csvProcessing().fileTest(temperatureFileName) == False):
            if args.verbose > 1: writeEvents().toScreen(msg="Creating a new file")
            temperatureFileObject = open(temperatureFileName, 'w')
            temperatureCSVWriter = csv.writer(temperatureFileObject)
            temperatureCSVWriter.writerow(['Time'] + temperatureFields)
            return temperatureCSVWriter
        else:
            #TODO Check to see if we have the right fields in the file
            #TODO Rename the existing file if the fields are wrong, and return an object for a new file
            #TODO Return an object with the existing file if the fields are right.
            temperatureFileObject = open(temperatureFileName, 'a')
            temperatureCSVWriter = csv.writer(temperatureFileObject)
            return temperatureCSVWriter
    def pollTemperature(self):
        global failCount
        temperatureUrl="https://{0}/redfish/v1/Chassis/1/Thermal".format(args.address)
        temperatureResponse = httpRequest().getUrl(url=temperatureUrl,headers=(processHeaders()))
        if not (200 <= temperatureResponse.status < 300):
            # Failed to talk to the API
            if args.verbose > 0: writeEvents().toScreen(msg="Connection to API failed.\n\t{0}\n{1}".format(temperatureResponse.status,temperatureResponse.body),msgType="WARN")
            if args.counter == 0 and failCount != 0:
                if args.verbose > 0: writeEvents().toScreen(msg="\t{0} retries remain before script exit".format(failCount),msgType="WARN")
                failAction = False
                failCount = failCount - 1
            else:
                # To many failures. Script exists
                failAction = True
            writeEvents().toScreen(msg="",msgType='FAIL',exitOnFail=failAction)
            return
        else:
            #If we succeed at any point we reset the failure counter
            if failCount < args.failCount:
                failCount = args.failCount
            self.writeJSONResponseToFile(temperatureResponse.body)
            #Write contents to CSV
        return
    def writeJSONResponseToFile(self,jsonResponse):
        now=datetime.now()
        date_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
        columnOrder = ['Time'] + temperatureFields
        temperatureDictionary = {'Time': date_time_str}
        for item in temperatureFields:
            temperatureDictionary[item] = None
            for temperature in json.loads(jsonResponse)['Temperatures']:
                if temperature['Name'] == item:
                    temperatureDictionary[item] = temperature['ReadingCelsius']
            if temperatureDictionary[item] == None:
                temperatureDictionary[item]="No Data Found"
        temperatureCSVObject.writerow([temperatureDictionary.get(column, None) for column in columnOrder])
        return 

class httpRequest():
    def getUrl(self, url: str,headers: dict, method: str='GET', data=None):
        if args.verbose > 0: writeEvents().toScreen(msg='Starting HTML Call')
        headers = {"Accept": "application/json", **headers}
        if args.verbose > 2: writeEvents().toScreen(msg="Header Data: \n\t{0}".format(headers))
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        httprequest = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(httprequest, context=ctx) as httpresponse:
                response = Response(
                    headers=httpresponse.headers,
                    status=httpresponse.status,
                    body=httpresponse.read().decode(
                        httpresponse.headers.get_content_charset("utf-8")
                    ),
                )
        except urllib.error.HTTPError as e:
            response = Response(
                body=str(e.reason),
                headers=e.headers,
                status=e.code
        )
        if args.verbose > 2: writeEvents().toScreen(msg='Raw Response from HTML call\n{0}'.format(response.headers))
        return response
    
    def getAuthToken(self):
        tokenRequest = json.dumps({'UserName':"{}".format(args.username),"Password":"{0}".format(args.password)})
        tokenURL = "https://{}/redfish/v1/SessionService/Sessions".format(args.address)
        tokenResponse = self.getUrl(url=tokenURL, data=tokenRequest.encode("utf-8"), method='POST',headers=processHeaders())
        if tokenResponse.headers['X-Auth-Token']:
            return {'X-Auth-Token': tokenResponse.headers['X-Auth-Token'],'Location':tokenResponse.headers['Location']}
        else:
            writeEvents().toScreen(msg='Failed to Obtain Authentication Token',msgType='FAIL',exitOnFail=True)
    def clearAuthToken(self):
        if token['Location']:
            clearTokenURL = "https://{0}/{1}".format(args.address,token["Location"])
            headers = processHeaders()
            httpRequest().getUrl(url=clearTokenURL,headers=headers,method='DELETE')
        return

while (bailout == False ):
    # For basic logging when some output is required. 
    if args.verbose > 0: print("Counter Equals: {}".format(counter))
    token = httpRequest().getAuthToken()
    powerSupplyCSVObject = powerSupplyProcessing().newOrOldCSV()
    powerSupplyProcessing().pollPowerSupply()
    temperatureCSVObject = temperatureProcessing().newOrOldCSV()
    temperatureProcessing().pollTemperature()

    # How we exit the loop. If 
    if counter == 1:
        bailout = True
    else:
        time.sleep(5)
        #If the counter = 0 we will never exit. 
        if counter != 0:
            # Otherwise we are counting down to 1.
            counter = counter - 1

if token:
    httpRequest().clearAuthToken()

