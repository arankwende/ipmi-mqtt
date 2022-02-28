#!/bin/python 
# Las dependencias:
from logging import NullHandler
import yaml
import json
import subprocess
import argparse
import paho.mqtt.client as mqtt
import time
import os
import sys
import daemon
import logging
import logging.handlers as handlers

#We define some arguments to be parsed as well as help messages and description for the script.
parser = argparse.ArgumentParser(description='This is a simple python script that uses IPMITools in order to connect to your servers, review their power states and SDRs, if defined, and then send them through mqtt to an mqtt broker in order for Home Assistant to use them. In order for it to work, you must have filled your mqtt connetion information and your IPMI server connection information.')
parser.add_argument('-i', action='store_true', help='Run once to only create the entities in your MQTT broker (and see them in home assistant).')
parser.add_argument('-o', action='store_true', help='Run once and quit.')
parser.add_argument('-d', action='store_true', help='Run as a daemon.')
parser.add_argument('-DEBUG', action='store_true', help='Add Debug messages to log.')
args = parser.parse_args()
#We define the logic and place where we're gonna log things
log_dir = os.path.dirname(os.path.realpath(__file__))  
log_fname = os.path.join(log_dir, 'ipmi-mqtt.log') #I define a relative path for the log to be saved on the same folder as my py
formatter = logging.Formatter("[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s")
logger = logging.getLogger() # I define format and instantiate first logger

if getattr(args,'DEBUG'):
    logger.setLevel(logging.DEBUG)  #I create an option to run the program in debug mode and receive more information on the logs
else:
    logger.setLevel(logging.INFO)

fh = handlers.RotatingFileHandler(log_fname, mode='w', maxBytes=10000000, backupCount=3) #This handler is important as I need a handler to pass to my daemon when run in daemon mode
fh.setFormatter(formatter) 
logger.addHandler(fh)

if getattr(args,'DEBUG'): # I set the debug option for the handler too
    fh.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)

# Connect to MQTT funcionts - this I took directly from the paho docs.
# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    logger.info("Connected with result code "+str(rc))
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("$SYS/#")
# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    logger.info(msg.topic+" "+str(msg.payload))

def on_publish(client, userdata,mid):
    logger.info("the published message id is:" + str(mid))


def main(): # Here i have the main program
    """Main function to run ipmi-mqtt in a loop."""
    try:
        #Here I load yaml configuration files and create variables for the elements in the yaml
            try:
                mqtt_dict = config['MQTT']
                mqtt_ip = mqtt_dict['MQTT_ip']
                mqtt_user = mqtt_dict['MQTT_USER']
                mqtt_pass = mqtt_dict['MQTT_PW']
                period = mqtt_dict['TIME_PERIOD']
                logging.debug("This is your mqqt dictionary:" + str(mqtt_dict))
                if 'HA_BINARY' in mqtt_dict:
                    ha_binary_topic= mqtt_dict['HA_BINARY']
                else:
                    logging.warning('There is no binary topic in your YAML file.')
                if 'HA_SENSOR' in mqtt_dict:
                    ha_sensor_topic= mqtt_dict['HA_SENSOR']
                else:
                    logging.warning('There is no sensor topic in your YAML file.')
                if 'HA_SWITCH' in mqtt_dict:
                    ha_switch_topic= mqtt_dict['HA_SWITCH']
                else:
                    logging.warning('There is no switch topic in your YAML file.')
            except Exception as exception:
                logging.critical(f'Your YAML is missing something in the MQTT section. You get the following error: {exception} ')
            try:
                topic_dict = config ['TOPICS']
                if 'POWER' in topic_dict: 
                    power_topic = topic_dict['POWER']
                    logging.debug("This is your power topic:" + str(power_topic))
                else:
                    logging.warning('There is no power topic in your YAML file.')

                if 'SDR_TYPES' in topic_dict:

                    sdr_topic_types = topic_dict['SDR_TYPES']
                    sdr_count = len(sdr_topic_types)
                    logging.debug("This are your SDR topics:" + str(sdr_topic_types))
                else:
                    logging.warning('There are no SDR topics in your YAML file.')
                    sdr_count = 0
            except Exception as exception:
                logging.critical(f'Your YAML is missing something in the TOPICS section. You get the following error: {exception} ')
            logging.info(f'You have {sdr_count} SDRs in your YAML file.')           
            try:
                server_config = config['SERVERS']
                if server_config is None:
                    logging.warning("You have no servers.")  
                else:
                    server_count = len(server_config)
                    logging.info(f"You have {server_count} servers.")
                    logging.debug(f"This is the configuration information they have: {str(server_config)}")
            except Exception as exception:
                logging.critical(f'Your YAML is missing something in the SERVERS section. You get the following error: {exception} ')
 
    except Exception as exception:
        logging.critical(f"Please check your YAML, it might be missing some parts. The exception is {exception}")


    #MQTT Config example from PAHO Docs
    client = mqtt.Client("ipmi-mqtt-server")
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_publish= on_publish
    client.username_pw_set(mqtt_user, password=mqtt_pass)
    
    #Get GUID for each server
    try:
        guid_dict = {}
        for server in server_config:
            server_nodename = server['IPMI_NODENAME']
            server_ip = server['IPMI_IP']
            server_user = server['IPMI_USER']
            server_pass = server['IPMI_PASSWORD']
            ipmi_guid_command = f"ipmitool -I lanplus -H \"{server_ip}\" -L User -U \"{server_user}\" -P \"{server_pass}\" mc guid|grep -i guid"
            ipmi_command_subprocess = subprocess.run(ipmi_guid_command, shell=True, capture_output=True)
            ipmi_guid_pure = ipmi_command_subprocess.stdout.decode("utf-8") #I decode the shell output with UTF-8
            if ipmi_guid_pure == '':
                logging.error(f"The server {server_nodename} has returned no GUID when connected through IPMI. There probably is a connection error.")
            ipmi_guid_pure = ipmi_guid_pure[15:] # I strip the sentence System GUID : 
            guid_dict[server_ip]=ipmi_guid_pure.strip() #I add this server's guid to the list on the position equal to the number of the server on the loop  
        logging.debug("The following GUIDs have been found:" + str(guid_dict))
    except Exception as exception:
        logging.critical(f"There is an error generating your server's guid. The error is the following: {exception}")
    
    while(True):
        #First run - power device initialization on HA
        try:    
            power_payload = {}
            for server in server_config:
                server_nodename = server['IPMI_NODENAME']
                server_ip = server['IPMI_IP']
                server_identifier = str("".join([guid_dict[server_ip]]))
                if server_identifier == '':
                    logging.warning(f"Power initialization for {server_nodename} has been skipped because no GUID was generated.")
                else:
                    device_mqtt_config = {"identifiers" : server_identifier, "configuration_url" : "http://" + server['IPMI_IP'], "manufacturer" : server['BRAND'], "name" : server_nodename}
                    server_mqtt_config_topic = ha_binary_topic + "/" + server_identifier + "_" + power_topic + "/" + "config"
                    server_mqtt_state_topic = ha_binary_topic + "/" + server_identifier + "_" + power_topic + "/" + "state"
                    mqtt_payload = {"device" : device_mqtt_config, "device_class" : "power", "name" : server_nodename + " " + power_topic , "unique_id" : server_identifier + "_power_", "force_update" : True, "payload_on" : "on", "payload_off" : "off" , "retain" : True, "state_topic" : server_mqtt_state_topic }
                    mqtt_payload = json.dumps(mqtt_payload)  
                    power_payload[server_mqtt_config_topic] = mqtt_payload
                for x, y in power_payload.items():
                        client.connect(mqtt_ip, 1883, 60)
                        client.publish(str(x), str(y), qos=1)
                        client.disconnect
                        logging.debug("You have sent the following payload: " + str(y))
                        logging.debug("To the configuration topic: " + x)
                        logging.debug("On the server with IP: " + mqtt_ip)
                        time.sleep(5)
        except Exception as exception:
            logging.critical(f"There was an error sending your device configuration.The error is: {exception}")
        # First run Sensor initialization
        try:    
            for server in server_config:
                server_nodename = server['IPMI_NODENAME']
                server_ip = str(server['IPMI_IP'])
                server_identifier = str("".join([guid_dict[server_ip]]))
                if server_identifier == '':
                    logging.warning(f"SDR initialization for {server_nodename} has been skipped because no GUID was generated.")
                else:
                    server_identifier = str("".join([guid_dict[server_ip]]))
                    sdr_list = server['SDRS']
                    sdr_payload = {}       
                    device_mqtt_config = {"identifiers" : server_identifier, "configuration_url" : "http://" + server['IPMI_IP'], "manufacturer" : server['BRAND'], "name" : server_nodename} 
                    for current_sdr in sdr_list:
                        sdr_type = str(current_sdr['SDR_TYPE'])
                        sdr_class = str(current_sdr['SDR_CLASS'])
                        sdr_topic = str(sdr_topic_types[int(sdr_type)])
                        server_mqtt_config_topic = ha_sensor_topic + "/" + server_identifier + "_" + sdr_topic + "/" + "config"
                        server_mqtt_state_topic = ha_sensor_topic + "/" + server_identifier + "_" + sdr_topic + "/" + "state" 
                        if sdr_class == 'temperature':
                            unit = "°C"
                            mqtt_payload = {"device" : device_mqtt_config, "device_class" : sdr_class, "name" : server_nodename + " " + sdr_topic , "unique_id" : server_identifier + "_sdr" + sdr_type, "unit_of_meas" : unit, "force_update" : True, "retain" : True, "state_topic" : server_mqtt_state_topic }
                        elif sdr_class == 'temperaturef':
                            unit = "°F"
                            mqtt_payload = {"device" : device_mqtt_config, "device_class" : sdr_class, "name" : server_nodename + " " + sdr_topic , "unique_id" : server_identifier + "_sdr" + sdr_type, "unit_of_meas" : unit, "force_update" : True, "retain" : True, "state_topic" : server_mqtt_state_topic }
                        elif sdr_class == 'voltage':
                            unit = "V"
                            mqtt_payload = {"device" : device_mqtt_config, "device_class" : sdr_class, "name" : server_nodename + " " + sdr_topic , "unique_id" : server_identifier + "_sdr" + sdr_type, 'unit_of_meas' : unit, "force_update" : True,  "retain" : True, "state_topic" : server_mqtt_state_topic }
                        elif sdr_class == 'fan':
                            unit = "RPM"
                            mqtt_payload = {"device" : device_mqtt_config, "device_class" : 'frequency', "name" : server_nodename + " " + sdr_topic , "unique_id" : server_identifier + "_sdr" + sdr_type, 'unit_of_meas' : unit, "force_update" : True,  "retain" : True, "state_topic" : server_mqtt_state_topic }                    
                        elif sdr_class == 'frequency':
                            unit = "Hz"
                            mqtt_payload = {"device" : device_mqtt_config, "device_class" : sdr_class, "name" : server_nodename + " " + sdr_topic , "unique_id" : server_identifier + "_sdr" + sdr_type, 'unit_of_meas' : unit, "force_update" : True, "retain" : True, "state_topic" : server_mqtt_state_topic }
                        else:
                            logging.warning("no unit defined for this type")
                            mqtt_payload = {"device" : device_mqtt_config,  "name" : server_nodename + " " + sdr_topic , "unique_id" : server_identifier + "_sdr" + sdr_type,  "force_update" : True, "retain" : True, "state_topic" : server_mqtt_state_topic }
                        mqtt_payload = json.dumps(mqtt_payload)  
                        sdr_payload[server_mqtt_config_topic] =  mqtt_payload
                    for x, y in sdr_payload.items():
                        client.connect(mqtt_ip, 1883, 60)
                        client.publish(x, str(y), qos=1).wait_for_publish
                        logging.debug("You have sent the following payload: " + str(y))
                        logging.debug("To the configuration topic: " + str(x))
                        logging.debug("On the server with IP: " + mqtt_ip)
                        client.disconnect
                        time.sleep(5)
        except Exception as exception:
            logging.error(f"There is an error in your SDR sensor collection. The error is the following: {exception}")
        logging.info("Initialization complete.")
        if getattr(args,'i'):
            logging.info("Started in iniatilization mode, so stopping now.")
            client.disconnect
            quit()
        else:
        #Sensor data gathering
            # Get Power data for each server if power topic is declared
            try:
                if 'POWER' not in topic_dict:
                    logging.info("You have no power topic.")
                else:
                    power_states = {} #I create a dictionary
                    for server in server_config:
                        server_nodename = server['IPMI_NODENAME']
                        server_ip = str(server['IPMI_IP'])
                        server_identifier = str("".join([guid_dict[server_ip]]))
                        if server_identifier == "":
                            logging.warning(f"Power sensor data collection for {server_nodename} has been skipped because no GUID was generated.")
                        else:
                            server_user = server['IPMI_USER']
                            server_pass = server['IPMI_PASSWORD']
                            server_mqtt_topic = ha_binary_topic + "/" + server_identifier + "_" + power_topic + "/" + "state"
                            ipmi_power_command = f"ipmitool -I lanplus -L User -H \"{server_ip}\" -U \"{server_user}\" -P \"{server_pass}\" chassis power status | cut -b 18-20"
                            ipmi_command_subprocess = subprocess.run(ipmi_power_command, shell=True, capture_output=True)
                            server_power_state = ipmi_command_subprocess.stdout.decode("utf-8").strip()
                            power_states[server_identifier] = server_power_state #I use the GUIDs as key with the server's power state as output
                            client.connect(mqtt_ip, 1883, 60)
                            client.publish(server_mqtt_topic, server_power_state, qos=1)
                            logging.debug("You have sent the following payload: " + str(server_power_state))
                            logging.debug("To the power state topic: " + str(server_mqtt_topic))
                            logging.debug("On the server with IP: " + mqtt_ip)
                            client.disconnect
                            time.sleep(5)
                logging.info(str(power_states))
            except Exception as exception:
                logging.error(f"There is an error in your power sensor collection. The error is the following: {exception}")
            # Get SDR DATA for each server if SDR topic is declared
            try:
                if 'SDR_TYPES' not in topic_dict:
                    logging.info("You have no SDRs.")
                else:
                    sdr_states = {} #I create a dictionary for all the servers


                    for server in server_config:
                        server_nodename = str(server['IPMI_NODENAME'])
                        server_ip = str(server['IPMI_IP'])
                        server_identifier = str("".join([guid_dict[server_ip]]))
                        if server_identifier == "":
                            logging.warning(f"SDR sensor data collection for {server_nodename} has been skipped because no GUID was generated.")
                        else:
                            server_user = str(server['IPMI_USER'])
                            server_pass = str(server['IPMI_PASSWORD'])
                            sdr_list = server['SDRS']
                            sdr_server_dict = {} # I create a dictionary with all of the servers values
                            sdr_sensor_mqtt_dict = {}
                            for current_sdr in sdr_list:                        
                                sdr_entity = current_sdr['VALUE']
                                ipmi_sdr_command = f"ipmitool -I lanplus -L User -H \"{server_ip}\" -U \"{server_user}\" -P \"{server_pass}\" sdr entity \"{sdr_entity}\""                            
                                ipmi_command_subprocess = subprocess.run(ipmi_sdr_command, shell=True, capture_output=True)
                                server_sdr_state = ipmi_command_subprocess.stdout.decode("utf-8").strip()                           
                                sdr_type = current_sdr['SDR_TYPE']
                                sdr_type = sdr_topic_types[sdr_type]
                                if server_sdr_state == '':
                                    logging.warning(f" Server {server_nodename} has returned no SDR information over IPMI, a connection problem is likely.")
                                else:
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
                                            logging.info(f"The SDR class {current_sdr['SDR_CLASS']} is not defined so we're gonna take the complete information from the column.")
                                    elif server['BRAND'] == 'ASUS':
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
                                            logging.info(f"The SDR class {current_sdr['SDR_CLASS']} is not defined so we're gonna take the complete information from the column.")
                                    if sdr_value == 'No' or sdr_value == 'Di':
                                        sdr_value = ""
                                        logging.warning(f"IPMI returned an empty value for server {server_nodename}it is likely the server is OFF and so no sensor data is being collected.")
                                    sdr_topic = sdr_type
                                    sdr_server_dict[sdr_type] = sdr_value
                                    server_mqtt_state_topic = ha_sensor_topic + "/" + server_identifier + "_" + sdr_topic + "/" + "state"     
                                    sdr_sensor_mqtt_dict[server_mqtt_state_topic] = sdr_value
                                sdr_states[server_identifier] = sdr_server_dict
                                for x, y in sdr_sensor_mqtt_dict.items():
                                        client.connect(mqtt_ip, 1883, 60) 
                                        client.publish(x,str(y), qos=1).wait_for_publish
                                        logging.debug("You have sent the following payload: " + str(y))
                                        logging.debug("To the SDR topic: " + str(x))
                                        logging.debug("On the server with IP: " + mqtt_ip)
                                        client.disconnect
                                        time.sleep(5)                        
                logging.debug("These are the SDR States collected:" + str(sdr_states))
            except Exception as exception:
                logging.error(f"There is an error in your SDR sensor collection. The error is the following: {exception}")
            client.disconnect
            if period == 0:  #If period set to 0, the script ends.
                logging.info("The time period in the YAML file is set to 0, so the script will end.")
                quit()
            elif getattr(args,'o'):
                logging.info("Started in run once mode, so stopping now.")
                client.disconnect
                quit()
            else:
                logging.info(f"Collection complete, will wait {period} seconds to start again")
                time.sleep(period)




try: # This loads the config file
    if getattr(args,'i'):
        logging.info("Running with -i in initialization mode.")
    if getattr(args,'o'):
        logging.info("Running with -o in run once mode.")
    if getattr(args,'d'):
        logging.info("Running with -d in daemon mode.")
    if getattr(args,'DEBUG'):
        logging.info("Running with -DEBUG in DEBUG log mode.")
    config_dir = os.path.dirname(os.path.realpath(__file__)) 
    config_file = os.path.join(config_dir, 'config.yaml')
    configuration = open(config_file, 'r')
    logging.info(f"Opening the following file: {config_file}")
    config = yaml.safe_load(configuration)
except Exception as exception:
    logging.critical(f"There's an error accessing your config.yml file, the error is the following: {exception}")
    print("There's no config yaml file in the program's folder, please check the logs.")
    sys.exit()

if getattr(args,'d'):
    context = daemon.DaemonContext(files_preserve = [configuration, fh.stream] )
    with context:
        main()

elif __name__== '__main__':
        main()



