# syntax=docker/dockerfile:1
FROM python:3.11.0a7-bullseye
WORKDIR /ipmi-mqtt
RUN apt install ipmitool git
RUN pip install yaml paho-mqtt python-daemon
RUN git clone https://github.com/arankwende/ipmi-mqtt .
EXPOSE 1886
CMD ["python3", "ipmi-mqtt.py", "-d"]