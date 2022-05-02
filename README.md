# ipmi-mqtt
Python app for IPMI states to be sent to Home Assistant via MQTT

This is a simple application that you can either run continuously in a predefined interval, run once (-o), use just to create your entities in home assistant through mqtt (-i) or run continuously as a daemon (-d). The scripts uses ipmi-tool to get IPMI sensor data (executing IPMITOOLs through the shell) from one or many servers and then republishes that data to MQTT in a format that Home Assistant automatically recognizes as devices, each with its own entities and switches so that the servers can be turned On or Off through IPMI.

If you want to use it as a service in linux or FreeBSD you can check the readme on the FreeBSD-service folder or the systemd-service folder in the repo and follow those instructions too.

The script requires:

python and ipmitools to be installed on the server 
for linux (apt):
```
sudo apt install python3 ipmitool python3-pip
```
as well as the following modules with pip:

yaml, paho-mqtt and python-daemon (which are all on ports):
```
sudo pip install yaml paho-mqtt python-daemon
```

for freebsd (pkg):

```
pkg install python3 ipmitool
```

as well as the following modules:

yaml, paho-mqtt and python-daemon (which are all on ports):
```
pkg install py38-daemon py38-yaml py38-paho-mqttp
```

Once installed, just copy this repo (you can use git clone), complete the YAML file and rename it config.yaml, make the script executable and run it.

That's it. You can execute it with -i in order to just execute the config payload being sent to the MQTT topic, or -d in order to have the script run as a daemon. You can also set a time (in seconds) inside the YAML file for the script to run in a loop and get new sensor values in that time period or simply run with -o to run one time only. 


All of the configuration is done via a config.yaml file, an example file is provided, you need to rename it to config.yml.

It must contain:

An MQTT configuration with IP, user, password, the topics for sensors (the example ones are for HA to do discovery) and the time period, which is the amount of time before re-runs of the sensor data gathering, if set to 0 the script will not repeat itself (like with option -o), otherwise it will run until killed:
paho-mqtt:
```
MQTT:
    MQTT_ip: MQTT BROKER IP
    MQTT_USER: 'MQTT user'
    MQTT_PW: 'MQTTPASSWORD'
    HA_BINARY: 'homeassistant/binary_sensor'
    HA_SENSOR: 'homeassistant/sensor'
    HA_SWITCH: 'homeassistant/switch'
    TIME_PERIOD: 300

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

```
ipmitool -I lanplus -L User -H "server-ip" -U "ipmi_user" -P "server_pass" sdr elist full

```

and you should get something like this (ASUS):

```
5V_AUX           | 01h | ok  |  7.0 | 4.95 Volts
3.3V_AUX         | 02h | ok  |  7.0 | 3.32 Volts
CPU_Vcore        | 03h | ok  |  7.0 | 1.06 Volts
VNN              | 04h | ok  |  7.0 | 0.84 Volts
VCCSRAM          | 05h | ok  |  7.0 | 1.05 Volts
VCCM             | 06h | ok  |  7.0 | 1.21 Volts
1.05V            | 07h | ok  |  7.0 | 1.06 Volts
1.8V             | 08h | ok  |  7.0 | 1.80 Volts
BAT              | 0Bh | ok  |  7.0 | 3.14 Volts
12V              | 0Fh | ok  |  7.0 | 12.10 Volts
MB Temp          | 30h | ok  |  3.0 | 47 degrees C
Card side Temp   | 31h | ok  |  3.0 | 56 degrees C
TR1 Temp         | 32h | ns  |  3.0 | No Reading
CPU1 Temp        | 33h | ok  |  3.0 | 78 degrees C
MemA Temp        | 40h | ok  |  3.0 | 63 degrees C
MemB Temp        | 41h | ok  |  3.0 | 62 degrees C
CPU1_FAN1        | 60h | ok  |  7.0 | 5000 RPM
FRNT_FAN1        | 62h | ok  |  7.0 | 5200 RPM
FRNT_FAN2        | 63h | ok  |  7.0 | 5000 RPM
REAR_FAN1        | 66h | ns  |  7.0 | No Reading

```
The fourth column has the SDR and the first the SUBCLASS

or this (SUPERMICRO):

```
CPU Temp         | 01h | ok  |  3.1 | 77 degrees C
System Temp      | 0Bh | ok  |  7.11 | 71 degrees C
Peripheral Temp  | 0Ch | ok  |  7.12 | 52 degrees C
DIMMA1 Temp      | B0h | ok  | 32.64 | 68 degrees C
DIMMA2 Temp      | B1h | ok  | 32.65 | 66 degrees C
DIMMB1 Temp      | B4h | ok  | 32.68 | 64 degrees C
DIMMB2 Temp      | B5h | ok  | 32.69 | 66 degrees C
FAN1             | 41h | ok  | 29.1 | 1300 RPM
FAN2             | 42h | ok  | 29.2 | 1300 RPM
FAN3             | 43h | ns  | 29.3 | No Reading
FANA             | 44h | ns  | 29.4 | No Reading
12V              | 30h | ok  |  7.48 | 12.06 Volts
5VCC             | 31h | ok  |  7.49 | 5.03 Volts
3.3VCC           | 32h | ok  |  7.50 | 3.35 Volts
VBAT             | 33h | ok  |  7.51 | 3.06 Volts
Vcpu             | 34h | ok  |  3.52 | 1.04 Volts
VDIMM            | 35h | ok  | 32.53 | 1.22 Volts
PVCCSRAM         | 36h | ok  |  7.54 | 1.02 Volts
P1V05_A          | 37h | ok  |  7.55 | 1.05 Volts
5VSB             | 38h | ok  |  7.56 | 4.97 Volts
3.3VSB           | 39h | ok  |  7.57 | 3.30 Volts
PVNN             | 3Ah | ok  |  7.58 | 0.85 Volts
PVPP             | 3Bh | ok  |  7.59 | 2.70 Volts
P1V538_A         | 3Ch | ok  |  7.60 | 1.54 Volts
1.2V BMC         | 3Dh | ok  |  7.61 | 1.22 Volts
PVCC_REF         | 3Eh | ok  |  7.62 | 1.26 Volts

```
The fourth column has the SDR value


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
              SDR_CLASS: ENTITY CLASS FOR HA (CAN BE temperature, temperaturef for fahrenheit, frequency, voltage or fan, units will be C, F, Hz, V or RPM accordingly)
              SUBCLASS: IF IT'S AN ASUS PLEASE CHECK THE NAME FOR THE SENSOR ON IPMITOOL AND PUT IT HERE, for example Mb Temp
              VALUE: SDR VALUE 


```

After configuring this, the first time you run the script it will create the devices and its entities directly in your MQTT broker you will find them on Home Assistant in the MQTT broker's entity page as well as separate devices(one per server). The entities are grouped into a each server which will appear as a device,  you can edit it to add it to an area.

I'm currently working on subscribing to a switch entity on MQTT so it can receive switch commands from HA and HA can turn on or off a PC through MQTT.

The program generates a log that will grow to 10MiB and then cycle 2 times (that is, there will be no more than 30MiB of logs).


