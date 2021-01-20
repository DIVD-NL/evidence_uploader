#!/bin/bash
export DEBIAN_FRONTEND=noninteractive
ln -fs /usr/share/zoneinfo/Europe/Amsterdam /etc/localtime
apt-get update
apt-get install -y python3 python3-pip 
pip3 install google-api-python-client google-auth-httplib2 google-auth-oauthlib
