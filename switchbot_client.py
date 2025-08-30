import hashlib
import hmac
import time
import json
import base64
import uuid
import requests
from typing import Dict, Optional


class SwitchBotClient:
    def __init__(self, token: str, secret: str):
        self.token = token
        self.secret = secret
        self.base_url = "https://api.switch-bot.com/v1.1"
    
    def _generate_signature(self, token: str, secret: str, nonce: str, timestamp: str) -> str:
        """Generate signature for SwitchBot API authentication"""
        string_to_sign = token + timestamp + nonce
        string_to_sign_b = bytes(string_to_sign, 'utf-8')
        secret_b = bytes(secret, 'utf-8')
        sign = base64.b64encode(hmac.new(secret_b, string_to_sign_b, hashlib.sha256).digest())
        return str(sign, 'utf-8')
    
    def _get_headers(self) -> Dict[str, str]:
        """Generate authentication headers for API requests"""
        nonce = str(uuid.uuid4())
        timestamp = str(int(round(time.time() * 1000)))
        sign = self._generate_signature(self.token, self.secret, nonce, timestamp)
        
        return {
            "Authorization": self.token,
            "Content-Type": "application/json",
            "charset": "utf8",
            "t": timestamp,
            "sign": sign,
            "nonce": nonce
        }
    
    def get_devices(self) -> Optional[Dict]:
        """Get list of all devices"""
        try:
            headers = self._get_headers()
            response = requests.get(f"{self.base_url}/devices", headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error getting devices: {e}")
            return None
    
    def get_device_status(self, device_id: str) -> Optional[Dict]:
        """Get status of a specific device"""
        try:
            headers = self._get_headers()
            response = requests.get(f"{self.base_url}/devices/{device_id}/status", headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error getting device status: {e}")
            return None
    
    def get_plug_power_data(self, device_id: str) -> Optional[Dict]:
        """Get power consumption data from SwitchBot Plug Mini"""
        status = self.get_device_status(device_id)
        if status and "body" in status:
            body = status["body"]
            
            power_data = {
                "device_id": device_id,
                "timestamp": int(time.time()),
                "voltage": body.get("voltage"),
                "electric_current": body.get("electricCurrent"), 
                "power": body.get("weight"),  # weight field contains instant power
                "electricity_of_day": body.get("electricityOfDay", 0),
                "power_on": body.get("power") == "on"
            }
            return power_data
        return None