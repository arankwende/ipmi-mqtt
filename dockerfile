# syntax=docker/dockerfile:1
FROM ubuntu:latest
WORKDIR /ipmi-mqtt
RUN apt update && apt install -y python3 python3-pip ipmitool git python3 && rm -rf /var/lib/apt/lists/*
RUN pip install pyyaml paho-mqtt python-daemon
COPY . .
#RUN git clone https://github.com/arankwende/ipmi-mqtt /ipmi-mqtt
EXPOSE 1886
CMD python3 /ipmi-mqtt/ipmi-mqtt.py