#!/bin/bash

# Start the static file server in the background
python /app/static_server.py &

# Start the Rasa action server
exec python -m rasa_sdk --actions actions