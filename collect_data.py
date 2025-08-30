#!/usr/bin/env python3
"""
Data collection script for multiple SwitchBot Plug Mini devices
This script is called by systemd timer to collect power data from all devices
"""

import requests
import sys
import os
from datetime import datetime

def collect_all_power_data():
    """Collect power data from all Plug Mini devices"""
    try:
        # Call the API to collect data from all devices
        response = requests.post("http://localhost:8001/power/collect/all", timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print(f"{datetime.now().isoformat()}: {data['message']}")
            
            # Log individual device results
            for device_id, result in data.get('results', {}).items():
                device_name = result.get('name', device_id)
                success = result.get('success', False)
                if success:
                    power = result.get('data', {}).get('power', 'N/A')
                    print(f"  - {device_name} ({device_id}): {power}W")
                else:
                    error = result.get('error', 'Unknown error')
                    print(f"  - {device_name} ({device_id}): FAILED - {error}")
                    
            return True
        else:
            print(f"Error: HTTP {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to API: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = collect_all_power_data()
    sys.exit(0 if success else 1)