# Basic API Monitoring Through Python for Temperature and Power Supply Monitoring of Stand-Alone C Series

## Overview
This is an example script that demonstrates polling of Temperature and Power Supply information with output in CSV format for short term assessment of Power and Thermal conditions. Written to use only native python libraries most systems instal with python 3.6 or later, this script polls the Cisco Integrated Management Controller (CIMC) using the redfish API to obtain power supply usage data and temperature related statistics. 

## Running This Script
To run this script, install python3 on most linux distributions. This was tested on the MAC OS and CentOS, but should work with most distributions of linux that include a version of python3.6 or later.

<p align="center">Example 1</p>
Monitoring 10.1.1.1 with the admin account for a single polling instance:

```
python3 ./TB-PythonExample.py --address 10.1.1.1 -u admin -p somepassword -c 1
```

<p align="center">Example 2</p>
Monitoring of 10.1.1.1 with the admin account until the script is terminated using Ctl+c

```
python3 ./TB-PythonExample.py -a 10.1.1.1 --username admin --password somepassword -c 0
```
<p align="center">Example 3</p>
Monitoring of 10.1.1.1 with the admin account for two polling cycles, creating reports in the /tmp/ directory.

```
python3 ./TB-PythonExample.py -a 10.1.1.1 -u admin -p somepassword -c 2 -r /tmp/
```
<br>
Note: The path provide for the -r argument must end with a / to be treated as a path and no checking is done to validate that the path is a directory. The entry you provide for the -r argument will be appended as a prefix to the name of the script. 

<p align="center">Expected Output</p>
This example will poll 10.1.1.1 a single time and return one row for each power supply found in the system, plus 1 row of temperature readings. It will product two files:

10.1.1.1-powersupply.csv
10.1.1.1-temperature.csv

The first row of each file contains the column headers separated by commas. Each additional row contains data collected. When files already exist, new rows are appended to the existing file. 

## Debugging Options
When there is a need to debug, use the the verbose option to change the output. 
    -v      Limit loggging with indications of basic activities. 
    -vv     Detailed value responses. 
    -vvv    Detailed output including raw Jason and HTML response data. 