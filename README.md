# ipmi-mqtt
Python app for IPMI states to be sent to Home Assistant via MQTT

This is a simple application that will run continuosly on your server (current version must be executed each time), getting IPMI sensor data (executing IPMITOOLs trhough the shell) from one or many servers and then republishes that data to MQTT in a format that Home Assistant automatically recognizes as entities and (currently working on it) switches for On Off.
The app requires:

python and ipmitools to be installed on the server:
```
sudo apt install python3 ipmitool
```


as well as the following modules:

yaml:
```
pip install pyyaml
```


paho-mqtt:
```
pip install paho-mqtt
```

Then, copy this repo, make the script executable and run it.

That's it.


All of the configuration is done via a config.yaml file, an example file is provided.

It must contain:

An Mqtt configuration:
paho-mqtt:
```
MQTT:
    MQTT_ip: MQTT BROKER IP
    MQTT_USER: 'MQTT user'
    MQTT_PW: 'MQTTPASSWORD'

```


    
A topics configuration, which can have one POWER topic and all of the SDRs (the name of the values that will be given to HA on the MQTT Broker), you must put one SDR type per type of SDR as you will reference them on the server configuration part.



```
TOPICS:
    POWER: 'THE NAME YOU WILL GIVE TO THE POWER VALUES'
    SDR_TYPES:
        1: 'server_cpu_temp'
        2: 'server_system_temp'
        3:  'server_cpu_fan'
        4:  'server_bmc_voltage'

```



On the SERVERS part, you can put as many servers as you wish  (I have 3), you must specify their nodename (the name you want to use for them), their brand (currently ASUS or SUPERMICRO), their IP, IPMI USER, PASSWORD and the SDR values for the sensors you want to use, if you don't know the SDR values of the sensors you can use:
ipmitool -I lanplus -L User -H "server-ip" -U "ipmi_user" -P "server_pass" sdr elist full
to connect to your server and see all of the available sensors and their SDR value.



```
SERVERS:
      - IPMI_NODENAME: SERVER NAME
        BRAND: SERVER BRAND
        IPMI_IP: SERVER IPMI IP
        IPMI_USER: 'SERVER IPMI USER'
        IPMI_PASSWORD: 'SERVER IPMI PASSWORD'
        SDRS:
            - SDR_TYPE: TYPE OF SDR (a number to match the dictionary of types in topics)
              SDR_CLASS: ENTITY CLASS FOR HA (CAN BE temperature, voltage or fan)
              SUBCLASS: IF IT'S AN ASUS PLEASE CHECK THE NAME FOR THE SENSOR ON IPMITOOL AND PUT IT HERE, for example Mb Temp
              VALUE: SDR VALUE 


```



After configuring this, the first time you run the script it will create the entities directly in your MQTT broker you will find them on Home Assistant in the MQTT broker's entity page (not on device, maybe in the future).

I'm currently working on making it run continously and subscribing to a switch entity on MQTT so it can receive switch commands from HA.
