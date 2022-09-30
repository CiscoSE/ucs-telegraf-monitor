# Directions for Configuration of Telegraf for monitoring of UCS #
This area documents configuration of Telegraf for monitoring power and thermal for UCS stand alone C series servers. This was written specifically for C125 servers, but should work with other stand along systems. This was written for a specific scenario / customer condition, and may reflect specific files relevant to that implementation. 

## Concept of Operations
This process creates a database of power and temperature statistics stored in InfluxDB. InfluxDB is used because it was developed for the kind of data we need to ingest and has readily available tools for populating the database and displaying stored data with little to no development required. 

In this instance we use Telegraf to import redish API data into InfluxDB, and the data in the database is easily displayed using common tools such as Grafana. In this instance we demonstrate obtaining power and thermal information from a C125 UCS server using the redfish API.

## Installation of elements.
Note that CentOS 7 or RHEL 7 do not offer Telegraf or InfluxDB, and we will provide links to public locations for these utilities. 

## <p align="center">Obtaining InfluxDB</p> ##
    InfluxDB location (RHEL7)
```
    https://repos.influxdata.com/rhel/7/x86_64/stable/
    influxdb-1.8.10.x86_64.rpm
```

## <p align="center">Install and Configure InfluxDB</p> ##
We install these files locally. In this example we pull the files with wget, install them with yum, and then configure the database and user. We do not expose the database through the firewall and this example assumes that the influxdb and telegraf resources are on the same server.

Pull the files locally and install with yum
```
# We will pull these files from the influxdb repository.
influxSource=https://repos.influxdata.com/rhel/7/x86_64/stable/influxdb-1.8.10.x86_64.rpm

# This pulls the files locally. 
wget $influxSource

# Installs InfluxDB
yum install influxdb-1.8.10.x86_64.rpm 
```
Start and enable service
```
systemctl start influxdb
systemctl enable influxdb
```
Create database and associated user
```
influx -execute 'create database telegrafdb'
influx -database telegraf -execute "CREATE USER telegrafu WITH PASSWORD 'Passw0rd123'"
influx -database telegraf -execute "GRANT ALL ON telegrafdb TO telegrafu"
```

## <p align="center">Install and Configure Telegraf</p> ##
    Telegraf location (RHEL7)
```
    https://repos.influxdata.com/rhel/7/x86_64/stable/
    telegraf-1.24.1-1.x86_64.rpm
```
## <p align="center">Install and Configure Telegraf</p> ##
We install these files locally. In this example we pull the files with wget, install them with yum, and then configure polling of a server through redfish. In this instance we assume that the InfluxDB database is on the same server, though it is possible to separate them.

Pull the files locally and install with yum
```
# We will pull these files from the influxdb repository (InfluxDB and Telegraf are stored in the same repo).
telegrafSource=https://repos.influxdata.com/rhel/7/x86_64/stable/telegraf-1.24.1-1.x86_64.rpm

# This pulls the files locally. 
wget $telegrafSource

# Installs Telegraf
yum install telegraf-1.24.1-1.x86_64.rpm
```
Configure Telegraph Input and Output
```
# Protect the original telegraf.conf file
mv /etc/telegraf/telegraf.conf /etc/telegraf/telegraf.conf.original

# Create a new telegraf file with default top level settings
cat <<EOF > /etc/telegraf/telegraf.conf
[global_tags]
[agent]
  # This is not the default, and you can set it to how often you want to poll your servers. 
  interval = "30s"
  round_interval = true
  metric_batch_size = 1000
  metric_buffer_limit = 10000
  collection_jitter = "0s"
  flush_interval = "10s"
  flush_jitter = "0s"
  precision = ""
  debug = false
  hostname = ""
  omit_hostname = true
  # If do not want telegraf logs, you can remove this line. Once you have everything working I would remove this.
  logfile = "/var/log/telegraf/telegraf.log"
EOF

# Set outputs to InfluxDB
cat <<EOF >> /etc/telegraf/telegraf.conf
[[outputs.influxdb]]
  # Location of InfluxDB database
  urls = ["http://127.0.0.1:8086"]
  # Name of the database to write to
  database = "telegrafdb"
  # User name with access to the InfluxDB database
  username = "telegrafu"
  # User Password
  password = "Passw0rd123"
  user_agent = "telegraf"
EOF

# Configure Telegraf to Poll a server supported by Redfish
cat <<EOF >> /etc/telegraf/telegraf.conf
[[inputs.redfish]]
  # Cisco Management IP (CIMC)
  address = "https://10.1.1.1"
  # A user created through the CIMC for API access.
  username = "CIMCUserName"
  #The password for the API User
  password = "CIMCPassword"
  # The serial number of the system to be captured
  computer_system_id = "WZP23000AA"
  # Allows for self signed certificates to be accepted. 
  insecure_skip_verify = true
EOF
```
Start and enable service
```
systemctl start telegraf
systemctl enable telegraf
```





