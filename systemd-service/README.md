# systemd service ipmi-mqtt
This folder contains a service script to run ipmi-mqtt as a service in linux with systemd.
The following steps will help you set it up in linux, specially in ubuntu, you should have installed all the dependencias and modules first (as outlined on the repos main readme):

First, we will create an user that will run the ipmi-mqtt, the default is ipmimqtt but any user can be created although you will have to modify the .service file:
```
adduser ipmimqtt
```
Next, we will clone this repo into the folder /usr/local/share/ipmi-mqtt

```
git clone https://github.com/arankwende/ipmi-mqtt /usr/local/ipmi-mqtt
```

We need to create the config.yaml file and populate it as specified on this repo:
```
nano /usr/local/ipmi-mqtt/config.yaml

```

We now make the user we created (in this example ipmimqtt) owner of the ipmi folder:
```
chown -R ipmimqtt /usr/local/ipmi-mqtt

```
and we make the folder executable:
```
chmod -R +x /usr/local/ipmi-mqtt

```

Now we copy the systemd example script into the user systemd folder:
```
cp /usr/local/ipmi-mqtt/systemd-service/ipmimqtt.service /etc/systemd/system/
```
If there are any changes from the guide we can edit it with:
```
nano /etc/systemd/system/ipmimqtt.service
```
And we make executable:
```
chmod +x /etc/systemd/system/ipmimqtt.service
```



We can now test it:
First we reload the systemctl daemon
```
sudo systemctl daemon-reload
```
then we start the service:
```
sudo systemctl start ipmimqtt.service

```

it should start and we can its status:
```
sudo systemctl status ipmimqtt.service

```
or check if the process with ipmi-mqtt.py is running_

```
ps -aux
```


Once everything is working, we can enable the service in order for it to work on reboot:

```
sudo systemctl enable ipmimqtt.service

```


