# FreeBSD service for ipmi-mqtt
This folder contains a script to run on Freebsd directly as an rc.d service using the freebsd daemon.
The following steps will help you set it up on freebsd, specially in a jail:
First install some utilities
```
pkg install nano git python
```

Then python and the modules required (they are on ports so no need for pip)

```
pkg install py38-daemon py38-yaml py38-paho-mqttp ipmitool
```
Now, we will create an user that will run the ipmi-mqtt, the default is ipmimqtt but any user can be created as long as it's modified via rc.config:
```
adduser
```
Next, we will clone this repo into the folder /usr/local/share/ipmi-mqtt

```
git clone https://github.com/arankwende/ipmi-mqtt /usr/local/share/ipmi-mqtt
```

And make the user we created (in this example ipmimqtt) owner of the folder (so that it can write the logs):

```
chown -R ipmimqtt /usr/local/share/ipmi-mqtt
```

We need to create the config.yaml file and populate it as specified on this repo:
```
nano /usr/local/share/ipmi-mqtt/config/config.yaml

```

We now make the user we created (in this example ipmimqtt) owner of the ipmi folder:
```
chown -R ipmimqtt /usr/local/share/ipmi-mqtt

```
and we make the folder executable:
```
chmod -R +x /usr/local/share/ipmi-mqtt

```

Now we copy the rc.d example script into the user rc.d folder:
```
cp /usr/local/share/ipmi-mqtt/freebsd-service/ipmimqtt /usr/local/etc/rc.d/
```
If there are any changes from the guide we can edit it with:
```
nano /usr/local/etc/rc.d/ipmimqtt
```
And we make executable:
```
chmod +x /usr/local/etc/rc.d/ipmimqtt
```
If we created a user different from ipmimqtt, we need to modify rc.config:
```
nano /etc/rc.config
```
And add the following line (for the user we created who will be executing the program):

```
ipmimqtt_localuser="USER"
```

We can now test it:
```
service ipmimqtt onestart
```
it should start and we can see if the processes are running:
```
ps -aux
```
If there is any trouble, we can check the daemon's log here:
```
/var/log/ipmi-mqtt.py.log
```
And the program's log here:

```
/usr/local/share/ipmi-mqtt/config/config.log
```

Once everything is working, we can enable the service in order for it to work on reboot:

```
service ipmimqtt enable
```


