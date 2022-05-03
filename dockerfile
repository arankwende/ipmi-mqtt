# syntax=docker/dockerfile:1
FROM python:3.11.0a7-bullseye
ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /ipmi-mqtt
RUN apt update && apt install -y ipmitool git && rm -rf /var/lib/apt/lists/*
RUN pip install pyyaml paho-mqtt python-daemon
RUN git clone https://github.com/arankwende/ipmi-mqtt .
EXPOSE 1886
CMD ["python3", "ipmi-mqtt.py"]