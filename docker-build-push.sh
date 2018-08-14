#!/bin/bash

docker build -t $DOCKER_REGISTRY_URL/teambot .
docker push $DOCKER_REGISTRY_URL/teambot
