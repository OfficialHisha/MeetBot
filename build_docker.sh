#!/bin/bash
docker stop meetbot
docker rm meetbot
docker rmi meetbot
docker build -t meetbot .
