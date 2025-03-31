#!/bin/bash
docker build -f DockerfileFog -t fog_nodes .
#docker build -f DockerfileMaster -t master_nodes .
docker build -f DockerfileCloud -t cloud_nodes .
docker build -f DockerfileIot -t iot_nodes .
