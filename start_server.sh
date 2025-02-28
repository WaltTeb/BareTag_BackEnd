#!/bin/bash

# Activate virtual environment for using flask
source ~/Documents/BareTag_BackEnd/venv/bin/activate

sleep 1

# Turn on the flask server (e.g. test_app.py)
nohup python app.py > flask.log 2>&1 &

sleep 1

# Kills any running ngrok processes
pkill -f ngrok  

# Turn on the ngrok server
ngrok http --domain=vital-dear-rattler.ngrok-free.app 5000 > ngrok.log 2>&1 &
# ngrok http 5000 > ngrok.log 2>&1 &

# Wait for ngrok to initialize
sleep 2

# Get the ngrok URL automatically
NGROK_URL=$(curl -s http://127.0.0.1:4040/api/tunnels | jq -r '.tunnels[0].public_url')

# Print the correct ngrok URL
echo "✅ Your ngrok URL is: $NGROK_URL"