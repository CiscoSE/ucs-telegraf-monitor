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
from logging.config import dictConfig
import time
import base64
import json
import typing
import urllib.error
import urllib.parse
import urllib.request
from email.message import Message
import ssl
import argparse
import csv

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
    def __init__(self, headers: dict, args: dict, powerSupplyCSV, temperatureCSV ):
        self.address = args.address
        self.reportDirectory = args.reportDirectory
        self.powerSupplyCSV = powerSupplyCSV
        self.temperatureCSV = temperatureCSV
        self.headers = headers
        return
    def supplyProcessing(self):
        supplyUrl="https://{0}/redfish/v1/Chassis/1/Power".format(self.address)
        print(supplyUrl)
        response = self.request(url=supplyUrl, headers=self.headers)
        for supply in response.json()["PowerSupplies"]:
            supplyItems = ["PowerOutputWatts","LineInputVoltage","Name","PowerInputWatts","LastPowerOutputWatts"]
        for item in supplyItems:
            self.powerSupplyCSV.write(str(supply[item])+",") #Cols key
        self.powerSupplyCSV.write("\n")
        return
    def temperatureProcessing(self):
        response = self.request(url="https://{}/redfish/v1/Chassis/1/Thermal".format(self.address), headers=self.headers)
        tempItems = ["TEMP_SENS_FRONT","DIMM_A1_TMP","DIMM_B1_TMP","DIMM_C1_TMP","DIMM_D1_TMP","DIMM_E1_TMP","DIMM_F1_TMP","DIMM_G1_TMP","DIMM_H1_TMP","P1_TEMP_SENS","PSU1_TEMP","PSU2_TEMP"]
        for temp in response.json()["Temperatures"]:
            tempFile.write(str(temp["ReadingCelsius"])+",") #Cols temp["Name"]
        return
    def request(
        self,
        url: str,
        headers: dict = None,
        method: str = "GET",
        error_count: int = 0,
    ) -> Response:
        method = method.upper()
        headers = headers or {}
        headers = {"Accept": "application/json", **headers}
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        httprequest = urllib.request.Request(
            url, headers=headers, method=method
        )
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
                status=e.code,
                error_count=error_count + 1,
            )
        if not (200 <= response.status < 300):
            print("Don't have access to the API requested") 
            exit()
        return response

helpmsg = """
    This will poll power and temperature readings from a Cisco Stand-alone C series server using the Redfish API.
"""
argsParse = argparse.ArgumentParser(description=helpmsg)
argsParse.add_argument('-a', '--address',           action='store', dest='address',         default='',      help="System to get API Data from")
argsParse.add_argument('-u', '--user',              action='store', dest='username',        default='admin', help='User Name to access the API' )
argsParse.add_argument('-p', '--password',          action='store', dest='password',        default='',      help="Password for API Access")
argsParse.add_argument('-r', '--reportDirectory',   action='store', dest="reportDirectory", default='./',    help="Location directory for files")
argsParse.add_argument('-c', '--count', type=int, action='store', dest='counter',         default='1',     help="Number of times to repeat")
args=argsParse.parse_args()
address = "{}".format(args.address)
username = "{}".format(args.username)
password = "{}".format(args.password)

headers = {'Authorization': 'Basic '+base64.b64encode((username+":"+password).encode('ascii')).decode("utf-8") }
supplyFile = open("{0}{1}-powersupply.csv".format(args.reportDirectory,address), "a")
tempFile = open("{0}{1}-temperature.csv".format(args.reportDirectory,address), "a")
csvObject = csvProcessing(headers=headers,args=args,powerSupplyCSV=supplyFile,temperatureCSV=tempFile)
bailout=False
counter = args.counter
while (bailout == False ):
    csvObject.supplyProcessing()
    csvObject.temperatureProcessing()    
    print(f"Counter Equals: {counter}")
    if counter == 1:
        bailout = True
    else:
        time.sleep(5)
        if counter != 0:
            counter = counter - 1

tempFile.write("\n")
tempFile.close()
supplyFile.close()
