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
def request(
    url: str,
    data: dict = None,
    params: dict = None,
    headers: dict = None,
    method: str = "GET",
    data_as_json: bool = True,
    error_count: int = 0,
) -> Response:
    if not url.casefold().startswith("http"):
        raise urllib.error.URLError("Incorrect and possibly insecure protocol in url")
    method = method.upper()
    request_data = None
    headers = headers or {}
    data = data or {}
    params = params or {}
    headers = {"Accept": "application/json", **headers}
    if method == "GET":
        params = {**params, **data}
        data = None
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True, safe="/")
    if data:
        if data_as_json:
            request_data = json.dumps(data).encode()
            headers["Content-Type"] = "application/json; charset=UTF-8"
        else:
            request_data = urllib.parse.urlencode(data).encode()
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    httprequest = urllib.request.Request(
        url, data=request_data, headers=headers, method=method
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

    return response

helpmsg = """
    Help will eventually be here.
"""
argsParse = argparse.ArgumentParser(description=helpmsg)
argsParse.add_argument('-a', '--address',         action='store', dest='address',         default='',      help="System to get API Data from")
argsParse.add_argument('-u', '--user',            action='store', dest='username',        default='admin', help='User Name to access the API' )
argsParse.add_argument('-p', '--password',        action='store', dest='password',        default='',      help="Password for API Access")
argsParse.add_argument('-r', '--reportDirectory', action='store', dest="reportDirectory", default='./',    help="Location directory for files")
args=argsParse.parse_args()
address = "{}".format(args.address)
username = "{}".format(args.username)
password = "{}".format(args.password)

while True:
    tempFile = open("{0}{1}.csv".format(args.reportDirectory,address), "a")
    supplyFile = open("supply.csv", "a")
    headers = {'Authorization': 'Basic '+base64.b64encode((username+":"+password).encode('ascii')).decode("utf-8") }
    response = request(url="https://"+address+"/redfish/v1/Chassis/1/Power", headers=headers, data={})
    for supply in response.json()["PowerSupplies"]:
        supplyItems = ["PowerOutputWatts","LineInputVoltage","Name","PowerInputWatts","LastPowerOutputWatts"]
        for item in supplyItems:
            supplyFile.write(str(supply[item])+",") #Cols key
    supplyFile.write("\n")
    response = request(url="https://"+address+"/redfish/v1/Chassis/1/Thermal", headers=headers, data={})
    tempItems = ["TEMP_SENS_FRONT","DIMM_A1_TMP","DIMM_B1_TMP","DIMM_C1_TMP","DIMM_D1_TMP","DIMM_E1_TMP","DIMM_F1_TMP","DIMM_G1_TMP","DIMM_H1_TMP","P1_TEMP_SENS","PSU1_TEMP","PSU2_TEMP"]
    for temp in response.json()["Temperatures"]:
        tempFile.write(str(temp["ReadingCelsius"])+",") #Cols temp["Name"]
    tempFile.write("\n")
    tempFile.close()
    supplyFile.close()
    time.sleep(60)

