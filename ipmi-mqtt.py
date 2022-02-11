#!/bin/python 
# Las dependencias:
from logging import NullHandler
import yaml
import json
import subprocess
import argparse
import paho.mqtt.client as mqtt
import time

parser = argparse.ArgumentParser(description='This is a simple python script that uses IPMITools in order to connect to your servers, review their power states and SDRs, if defined, and then send them through mqtt to an mqtt broker in order for Home Assistant to use them. In order for it to work, you must have filled your mqtt connetion information and your IPMI server connection information.')

args = parser.parse_args()

#Here I load yaml configuration files and create variables for the elements in the yaml

ha_sensor_topic="homeassistant/sensor"
ha_binary_topic="homeassistant/binary_sensor"

try:
    with open('config.yaml', 'r') as configuration:
        config = yaml.safe_load(configuration)
        try:
            mqtt_dict = config['MQTT']
            mqtt_ip = mqtt_dict['MQTT_ip']
            mqtt_user = mqtt_dict['MQTT_USER']
            mqtt_pass = mqtt_dict['MQTT_PW']
        except Exception as exception:
            print(f'Your YAML is missing something in the MQTT section. You get the following error: {exception} ')
        try:
            topic_dict = config ['TOPICS']
            if 'POWER' in topic_dict: 
                power_topic = topic_dict['POWER']
                sdr_count = len(topic_dict) - 1
            else:
                print('No power topic')
                sdr_count = len(topic_dict)
            if 'SDR_TYPES' in topic_dict:

                sdr_topic_types = topic_dict['SDR_TYPES']
            else:
                print('No SDR topics')
                sdr_count = 0
        except Exception as exception:
            print(f'Your YAML is missing something in the TOPICS section. You get the following error: {exception} ')

        try:
            server_config = config['SERVERS']
            if server_config is None:
                print("You have no servers.")  
            else:
                server_count = len(server_config)
                print(f"You have {server_count} servers.")
        except Exception as exception:
            print(f'Your YAML is missing something in the SERVERS section. You get the following error: {exception} ')
    
except Exception as exception:
    print(f"Please check your YAML, it might be missing some parts. The exception is {exception}")


# Connect to MQTT - this I took directly from the paho docs.



# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("$SYS/#")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))


#MQTT Config
client = mqtt.Client("ipmi-mqtt-server")
client.on_connect = on_connect
client.on_message = on_message
client.username_pw_set(mqtt_user, password=mqtt_pass)


#Get GUID for each server
try:
    server_number = 0 #first server will be 0
    guid_list = []
    for i in server_config:
        server = server_config[server_number]
        server_nodename = server['IPMI_NODENAME']
        server_ip = server['IPMI_IP']
        server_user = server['IPMI_USER']
        server_pass = server['IPMI_PASSWORD']
        ipmi_guid_command = f"ipmitool -I lanplus -H \"{server_ip}\" -L User -U \"{server_user}\" -P \"{server_pass}\" mc guid|grep -i guid"
        ipmi_command_subprocess = subprocess.run(ipmi_guid_command, shell=True, capture_output=True)
        ipmi_guid_pure = ipmi_command_subprocess.stdout.decode("utf-8") #I decode the shell output with UTF-8
        ipmi_guid_pure = ipmi_guid_pure[15:] # I strip the sentence System GUID : 
        guid_list.append(ipmi_guid_pure.strip()) #I add this server's guid to the list on the position equal to the number of the server on the loop
        server_number = server_number + 1
except Exception as exception:
    print(f"There is an error generating your server's guid. The error is the following: {exception}")


#First run - device initialization on HA - I need to move this to only be executed when an argument is called.
try:    
    server_number = 0
    for i in server_config:
        server = server_config[server_number]
        server_nodename = server['IPMI_NODENAME']
        server_mqtt_config_topic = ha_binary_topic + "/" + guid_list[server_number] + "_" + power_topic + "/" + "config"
        server_mqtt_state_topic = ha_binary_topic + "/" + guid_list[server_number] + "_" + power_topic + "/" + "state"
        mqtt_payload = {"device_class" : "power", "name" : server_nodename + " " + power_topic , "unique_id" : guid_list[server_number], "force_update" : True, "payload_on" : "on", "payload_off" : "off" , "retain" : True, "state_topic" : server_mqtt_state_topic }
        mqtt_payload = json.dumps(mqtt_payload)  
        print(mqtt_payload)
        client.connect(mqtt_ip, 1883, 60)
        client.publish(server_mqtt_config_topic, str(mqtt_payload))
        server_number = server_number + 1





except Exception as exception:
    print(f"There was an error.{exception}")
# First run Sensor initialization
try:    
    server_number = 0
    for i in server_config:
        sdr_number = 0
        server = server_config[server_number]
        server_nodename = server['IPMI_NODENAME']
        sdr_list = server['SDRS']
   
        
        for e in sdr_list:

            current_sdr = sdr_list[sdr_number]
            sdr_type = current_sdr['SDR_TYPE']
            sdr_class = current_sdr['SDR_CLASS']
            sdr_topic = sdr_topic_types[sdr_type]
            if sdr_class == 'temperature':
                unit = "°C"
            elif sdr_class == 'fan':
                unit = "rpm"
            elif sdr_class == 'voltage':
                unit = "V"
            else:
                print("no unit defined for this type")
                unit = ""
            server_mqtt_config_topic = ha_sensor_topic + "/" + guid_list[server_number] + "_" + sdr_topic + "/" + "config"
            server_mqtt_state_topic = ha_sensor_topic + "/" + guid_list[server_number] + "_" + sdr_topic + "/" + "state"     
            mqtt_payload = {"device_class" : sdr_class, "name" : server_nodename + " " + sdr_topic , "unique_id" : guid_list[server_number], "Unit of Measurement" : unit, "force_update" : True, "payload_on" : "on", "payload_off" : "off" , "retain" : True, "state_topic" : server_mqtt_state_topic }
            mqtt_payload = json.dumps(mqtt_payload)  
            print(mqtt_payload)
            client.connect(mqtt_ip, 1883, 60)
            client.publish(server_mqtt_config_topic, str(mqtt_payload)) 
            sdr_number = sdr_number + 1
        server_number = server_number + 1 

except Exception as exception:
    print(f"There is an error in your SDR sensor collection. The error is the following: {exception}")












# Get Power data for each server if power topic is declared
try:
    if 'POWER' not in topic_dict:
        print("You have no power topic.")
    else:
        server_number = 0
        power_states = {} #I create a dictionary
        for i in server_config:
            server = server_config[server_number]
            server_nodename = server['IPMI_NODENAME']
            server_ip = server['IPMI_IP']
            server_user = server['IPMI_USER']
            server_pass = server['IPMI_PASSWORD']
            server_mqtt_topic = ha_binary_topic + "/" + guid_list[server_number] + "_" + power_topic + "/" + "state"
            ipmi_power_command = f"ipmitool -I lanplus -L User -H \"{server_ip}\" -U \"{server_user}\" -P \"{server_pass}\" chassis power status | cut -b 18-20"
            ipmi_command_subprocess = subprocess.run(ipmi_power_command, shell=True, capture_output=True)
            server_power_state = ipmi_command_subprocess.stdout.decode("utf-8").strip()
            power_states[guid_list[server_number]] = server_power_state #I use the GUIDs as key with the server's power state as output
            client.connect(mqtt_ip, 1883, 60)
            client.publish(server_mqtt_topic, server_power_state)
            server_number = server_number + 1
except Exception as exception:
    print(f"There is an error in your power sensor collection. The error is the following: {exception}")


# Get SDR DATA for each server if power topic is declared
try:
    if 'SDR_TYPES' not in topic_dict:
        print("You have no SDRs.")
    else:
        server_number = 0
        sdr_states = {} #I create a dictionary for all the servers
        for i in server_config:
            server = server_config[server_number]
            server_nodename = server['IPMI_NODENAME']
            server_ip = server['IPMI_IP']
            server_user = server['IPMI_USER']
            server_pass = server['IPMI_PASSWORD']
            sdr_list = server['SDRS']
            sdr_server_dict = {} # I create a dictionary with all of the servers values
            sdr_number = 0
            for e in sdr_list:
                  
                current_sdr = sdr_list[sdr_number]
                sdr_entity = current_sdr['VALUE']
                ipmi_sdr_command = f"ipmitool -I lanplus -L User -H \"{server_ip}\" -U \"{server_user}\" -P \"{server_pass}\" sdr entity \"{sdr_entity}\""
                
                ipmi_command_subprocess = subprocess.run(ipmi_sdr_command, shell=True, capture_output=True)
                server_sdr_state = ipmi_command_subprocess.stdout.decode("utf-8").strip()
                
                sdr_type = current_sdr['SDR_TYPE']
                sdr_type = sdr_topic_types[sdr_type]
                if server['BRAND'] == 'SUPERMICRO':
#                    print(server_nodename + " is a Supermicro server.")
                    server_sdr_values = server_sdr_state.split("|")
                    if current_sdr['SDR_CLASS'] == 'temperature':
                        sdr_value = server_sdr_values[4]
                        sdr_value = sdr_value[:3]
                        sdr_value = sdr_value.strip()
                    elif current_sdr['SDR_CLASS'] == 'fan':
                        sdr_value = server_sdr_values[4]
                        sdr_value = sdr_value[:6]
                        sdr_value = sdr_value.strip()
                    elif current_sdr['SDR_CLASS'] == 'voltage':
                        sdr_value = server_sdr_values[4]
                        sdr_value = sdr_value[:6]
                        sdr_value = sdr_value.strip()
                    else:
                        print("The SDR class is not defined so we're gonna take the complete information from the column.")
           
                elif server ['BRAND'] == 'ASUS':
#                    print(server_nodename + " is an Asus server.")
                    sdr_subclass = current_sdr['SUBCLASS']
                    server_sdr_values = server_sdr_state.split("\n")
                    server_sdr_values = list(filter(lambda x: x.startswith(sdr_subclass), server_sdr_values))
                    server_sdr_values = server_sdr_values[0].split("|")
                    if current_sdr['SDR_CLASS'] == 'temperature':
                        sdr_value = server_sdr_values[4]
                        sdr_value = sdr_value[:3]
                        sdr_value = sdr_value.strip()
                    elif current_sdr['SDR_CLASS'] == 'fan':
                        sdr_value = server_sdr_values[4]
                        sdr_value = sdr_value[:6]
                        sdr_value = sdr_value.strip()
                    elif current_sdr['SDR_CLASS'] == 'voltage':
                        sdr_value = server_sdr_values[4]
                        sdr_value = sdr_value[:6]
                        sdr_value = sdr_value.strip()
                    else:
                        print("The SDR class is not defined so we're gonna take the complete information from the column.")
                #sdr_states[guid_list[server_number]] = server_sdr_state #I use the GUIDs as key with the server's power state as output
                if sdr_value == 'No':
                    sdr_value = ""
                sdr_topic = sdr_type
                sdr_server_dict[sdr_type] = sdr_value
                server_mqtt_state_topic = ha_sensor_topic + "/" + guid_list[server_number] + "_" + sdr_topic + "/" + "state"     
                client.connect(mqtt_ip, 1883, 60)
                client.publish(server_mqtt_state_topic, sdr_value)
                sdr_number = sdr_number + 1
           
            sdr_states[guid_list[server_number]] = sdr_server_dict
            server_number = server_number + 1 
except Exception as exception:
    print(f"There is an error in your SDR sensor collection. The error is the following: {exception}")

print(power_states)
print(sdr_states)

client.disconnect
#Publication of data

