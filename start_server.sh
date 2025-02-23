#!/bin/bash

# Activate virtual environment for using flask
source ~/venv/bin/activate

sleep 1

# Turn on the flask server (e.g. test_app.py)
nohup python app.py > flask.log 2>&1 &

sleep 1

# Turn on the ngrok server
ngrok http --domain=vital-dear-rattler.ngrok-free.app 5000 > ngrok.log 2>&1 &
