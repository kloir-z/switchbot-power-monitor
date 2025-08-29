#!/bin/bash
# Automatic data collection script for SwitchBot Power Monitor

DEVICE_ID="48CA43C49E36"
API_URL="http://localhost:8001"

# Collect power data
curl -X POST "${API_URL}/power/collect/${DEVICE_ID}" -s > /dev/null

# Log the collection (optional)
# echo "$(date): Power data collected" >> /home/user/switchbot-power-monitor/collection.log