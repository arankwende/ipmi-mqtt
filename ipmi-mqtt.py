#!/bin/python 
# Las dependencias:
from logging import NullHandler
import yaml
import json
import subprocess
import argparse
import paho.mqtt.client as mqtt
import time
import sys
import os
import daemon

parser = argparse.ArgumentParser(description='This is a simple python script that uses IPMITools in order to connect to your servers, review their power states and SDRs, if defined, and then send them through mqtt to an mqtt broker in order for Home Assistant to use them. In order for it to work, you must have filled your mqtt connetion information and your IPMI server connection information.')
parser.add_argument('-i', action='store_true', help='initialization run')
parser.add_argument('-d', action='store_true', help='run as daemon')
args = parser.parse_args()

def main():
    try:
        #Here I load yaml configuration files and create variables for the elements in the yaml
            try:
                mqtt_dict = config['MQTT']
                mqtt_ip = mqtt_dict['MQTT_ip']
                mqtt_user = mqtt_dict['MQTT_USER']
                mqtt_pass = mqtt_dict['MQTT_PW']
                period = mqtt_dict['TIME_PERIOD']
                if 'HA_BINARY' in mqtt_dict:
                    ha_binary_topic= mqtt_dict['HA_BINARY']
                else:
                    print('No binary topic selected.')
                if 'HA_SENSOR' in mqtt_dict:
                    ha_sensor_topic= mqtt_dict['HA_SENSOR']
                else:
                    print('No sensor topic selected.')
                if 'HA_SWITCH' in mqtt_dict:
                    ha_switch_topic= mqtt_dict['HA_SWITCH']
                else:
                    print('No switch topic selected.')
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
    
    def on_publish(client, userdata,mid):
        print("the published message is:" + str(y))

    #MQTT Config
    client = mqtt.Client("ipmi-mqtt-server")
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_publish= on_publish
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
        #First run - power device initialization on HA
    try:    
        server_number = 0
        power_payload = {}
        for i in server_config:
            server = server_config[server_number]
            server_nodename = server['IPMI_NODENAME']
            server_identifier = [guid_list[server_number]]
            device_mqtt_config = {"identifiers" : server_identifier, "configuration_url" : "http://" + server['IPMI_IP'], "manufacturer" : server['BRAND'], "name" : server_nodename}
            server_mqtt_config_topic = ha_binary_topic + "/" + guid_list[server_number] + "_" + power_topic + "/" + "config"
            server_mqtt_state_topic = ha_binary_topic + "/" + guid_list[server_number] + "_" + power_topic + "/" + "state"
            mqtt_payload = {"device" : device_mqtt_config, "device_class" : "power", "name" : server_nodename + " " + power_topic , "unique_id" : guid_list[server_number] + "_power_", "force_update" : True, "payload_on" : "on", "payload_off" : "off" , "retain" : True, "state_topic" : server_mqtt_state_topic }
            mqtt_payload = json.dumps(mqtt_payload)  
            power_payload[mqtt_payload] = server_mqtt_config_topic
            server_number = server_number + 1

        for x, y in power_payload.items():
                client.connect(mqtt_ip, 1883, 60)
                client_publisher = client.publish(y, str(x), qos=1)
                client_publisher.wait_for_publish
                client.disconnect
    except Exception as exception:
        print(f"There was an error sending your device configuration.The error is: {exception}")
    # First run Sensor initialization
    try:    
        server_number = 0
        for i in server_config:
            sdr_number = 0
            server = server_config[server_number]
            server_nodename = server['IPMI_NODENAME']
            sdr_list = server['SDRS']
            sdr_payload = {}       
            device_mqtt_config = {"identifiers" : server_identifier, "configuration_url" : "http://" + server['IPMI_IP'], "manufacturer" : server['BRAND'], "name" : server_nodename}      
            for e in sdr_list:
                current_sdr = sdr_list[sdr_number]
                sdr_type = current_sdr['SDR_TYPE']
                sdr_class = current_sdr['SDR_CLASS']
                sdr_topic = sdr_topic_types[sdr_type]
                server_mqtt_config_topic = ha_sensor_topic + "/" + guid_list[server_number] + "_" + sdr_topic + "/" + "config"
                server_mqtt_state_topic = ha_sensor_topic + "/" + guid_list[server_number] + "_" + sdr_topic + "/" + "state" 
                if sdr_class == 'temperature':
                    unit = "°C"
                    mqtt_payload = {"device" : device_mqtt_config, "device_class" : sdr_class, "name" : server_nodename + " " + sdr_topic , "unique_id" : guid_list[server_number] + "_sdr" + str(sdr_number), "unit_of_meas" : unit, "force_update" : True, "retain" : True, "state_topic" : server_mqtt_state_topic }
                elif sdr_class == 'temperaturef':
                    unit = "°F"
                    mqtt_payload = {"device" : device_mqtt_config, "device_class" : sdr_class, "name" : server_nodename + " " + sdr_topic , "unique_id" : guid_list[server_number] + "_sdr" + str(sdr_number), "unit_of_meas" : unit, "force_update" : True, "retain" : True, "state_topic" : server_mqtt_state_topic }
                elif sdr_class == 'voltage':
                    unit = "V"
                    mqtt_payload = {"device" : device_mqtt_config, "device_class" : sdr_class, "name" : server_nodename + " " + sdr_topic , "unique_id" : guid_list[server_number] + "_sdr" + str(sdr_number), 'unit_of_meas' : unit, "force_update" : True,  "retain" : True, "state_topic" : server_mqtt_state_topic }
                elif sdr_class == 'fan':
                    unit = "RPM"
                    mqtt_payload = {"device" : device_mqtt_config, "device_class" : 'frequency', "name" : server_nodename + " " + sdr_topic , "unique_id" : guid_list[server_number] + "_sdr" + str(sdr_number), 'unit_of_meas' : unit, "force_update" : True,  "retain" : True, "state_topic" : server_mqtt_state_topic }                    
                elif sdr_class == 'frequency':
                    unit = "Hz"
                    mqtt_payload = {"device" : device_mqtt_config, "device_class" : sdr_class, "name" : server_nodename + " " + sdr_topic , "unique_id" : guid_list[server_number] + "_sdr" + str(sdr_number), 'unit_of_meas' : unit, "force_update" : True, "retain" : True, "state_topic" : server_mqtt_state_topic }

                else:
                    print("no unit defined for this type")
                    mqtt_payload = {"device" : device_mqtt_config,  "name" : server_nodename + " " + sdr_topic , "unique_id" : guid_list[server_number] + "_sdr" + str(sdr_number),  "force_update" : True, "retain" : True, "state_topic" : server_mqtt_state_topic }
                mqtt_payload = json.dumps(mqtt_payload)  
                sdr_payload[server_mqtt_config_topic] =  mqtt_payload
                sdr_number = sdr_number + 1
            server_number = server_number + 1 

            for x, y in sdr_payload.items():
                client.connect(mqtt_ip, 1883, 60)
                client.publish(x, str(y), qos=1).wait_for_publish
                client.disconnect
    except Exception as exception:
        print(f"There is an error in your SDR sensor collection. The error is the following: {exception}")
    if getattr(args,'i'):
        client.disconnect
        quit()
    else:
        #Sensor data gathering
        while(True):
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
                        client.publish(server_mqtt_topic, server_power_state, qos=2).wait_for_publish
                        client.disconnect
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
                        sdr_sensor_mqtt_dict = {}
                        for e in sdr_list:                        
                            current_sdr = sdr_list[sdr_number]
                            sdr_entity = current_sdr['VALUE']
                            ipmi_sdr_command = f"ipmitool -I lanplus -L User -H \"{server_ip}\" -U \"{server_user}\" -P \"{server_pass}\" sdr entity \"{sdr_entity}\""                            
                            ipmi_command_subprocess = subprocess.run(ipmi_sdr_command, shell=True, capture_output=True)
                            server_sdr_state = ipmi_command_subprocess.stdout.decode("utf-8").strip()                            
                            sdr_type = current_sdr['SDR_TYPE']
                            sdr_type = sdr_topic_types[sdr_type]
                            if server['BRAND'] == 'SUPERMICRO':
                                server_sdr_values = server_sdr_state.split("|")
                                if current_sdr['SDR_CLASS'] == 'temperature':
                                    sdr_value = server_sdr_values[4]
                                    sdr_value = sdr_value[:3]
                                    sdr_value = sdr_value.strip()
                                elif current_sdr['SDR_CLASS'] == 'fan':
                                    sdr_value = server_sdr_values[4]
                                    sdr_value = sdr_value[:6]
                                    sdr_value = sdr_value.strip()
       #                             sdr_value = int(sdr_value)/60
                                elif current_sdr['SDR_CLASS'] == 'frequency':
                                    sdr_value = server_sdr_values[4]
                                    sdr_value = sdr_value[:6]
                                    sdr_value = sdr_value.strip()
                                    sdr_value = int(sdr_value)/60
                                elif current_sdr['SDR_CLASS'] == 'voltage':
                                    sdr_value = server_sdr_values[4]
                                    sdr_value = sdr_value[:6]
                                    sdr_value = sdr_value.strip()
                                else:
                                    sdr_value = server_sdr_values[4]
                                    print("The SDR class is not defined so we're gonna take the complete information from the column.")
                            elif server ['BRAND'] == 'ASUS':
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
                                elif current_sdr['SDR_CLASS'] == 'frequency':
                                    sdr_value = server_sdr_values[4]
                                    sdr_value = sdr_value[:6]
                                    sdr_value = sdr_value.strip()
                                    sdr_value = int(sdr_value)/60
                                elif current_sdr['SDR_CLASS'] == 'voltage':
                                    sdr_value = server_sdr_values[4]
                                    sdr_value = sdr_value[:6]
                                    sdr_value = sdr_value.strip()
                                else:
                                    sdr_value = server_sdr_values[4]
                                    print("The SDR class is not defined so we're gonna take the complete information from the column.")
                            if sdr_value == 'No' or sdr_value == 'Di':
                                sdr_value = ""
                            sdr_topic = sdr_type
                            sdr_server_dict[sdr_type] = sdr_value
                            server_mqtt_state_topic = ha_sensor_topic + "/" + guid_list[server_number] + "_" + sdr_topic + "/" + "state"     
                            sdr_sensor_mqtt_dict[server_mqtt_state_topic] = sdr_value
                            sdr_number = sdr_number + 1
                        sdr_states[guid_list[server_number]] = sdr_server_dict
   
                        for x, y in sdr_sensor_mqtt_dict.items():
                                client.connect(mqtt_ip, 1883, 60) 
                                client.publish(x,str(y), qos=1).wait_for_publish
                                client.disconnect                        
                        server_number = server_number + 1 
            except Exception as exception:
                print(f"There is an error in your SDR sensor collection. The error is the following: {exception}")

            client.disconnect
            if period == 0:  #If period set to 0, the script ends.
                quit()
            else:
                time.sleep(period)
configuration = open(sys.path[0] + '/config.yaml', 'r')
config = yaml.safe_load(configuration)
if getattr(args,'d'):
    context = daemon.DaemonContext(files_preserve = [configuration])
    with context:
        main()
elif __name__== '__main__':
        main()
