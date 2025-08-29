from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import asyncio
import os
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
from switchbot_client import SwitchBotClient
from data_storage import PowerDataStorage

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="SwitchBot Power Monitor", version="1.0.0")
templates = Jinja2Templates(directory="templates")

# Global variables for configuration
switchbot_client: Optional[SwitchBotClient] = None
storage = PowerDataStorage()
DEVICE_ID = os.getenv("SWITCHBOT_DEVICE_ID", "")

def init_switchbot_client():
    """Initialize SwitchBot client with environment variables"""
    token = os.getenv("SWITCHBOT_TOKEN")
    secret = os.getenv("SWITCHBOT_SECRET")
    
    if not token or not secret:
        return None
    
    return SwitchBotClient(token, secret)

@app.on_event("startup")
async def startup_event():
    """Initialize the SwitchBot client on startup"""
    global switchbot_client
    switchbot_client = init_switchbot_client()
    if not switchbot_client:
        print("Warning: SwitchBot credentials not configured")

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "SwitchBot Power Monitor API",
        "version": "1.0.0",
        "endpoints": [
            "/devices - List all SwitchBot devices",
            "/power/current/{device_id} - Get current power reading",
            "/power/history/{device_id} - Get power history",
            "/power/collect/{device_id} - Manually collect power data"
        ]
    }

@app.get("/devices")
async def get_devices():
    """Get all SwitchBot devices"""
    if not switchbot_client:
        raise HTTPException(status_code=500, detail="SwitchBot client not configured")
    
    devices = switchbot_client.get_devices()
    if devices is None:
        raise HTTPException(status_code=500, detail="Failed to fetch devices")
    
    return devices

@app.get("/power/current/{device_id}")
async def get_current_power(device_id: str):
    """Get current power reading for a device"""
    if not switchbot_client:
        raise HTTPException(status_code=500, detail="SwitchBot client not configured")
    
    power_data = switchbot_client.get_plug_power_data(device_id)
    if power_data is None:
        raise HTTPException(status_code=404, detail="Device not found or no data available")
    
    return power_data

@app.get("/power/history/{device_id}")
async def get_power_history(device_id: str, hours: int = 24, limit: int = 1000):
    """Get power history for a device"""
    if hours > 0:
        readings = storage.get_readings_by_timerange(device_id, hours)
    else:
        readings = storage.get_all_readings(device_id, limit)
    
    return {
        "device_id": device_id,
        "total_readings": len(readings),
        "timerange_hours": hours if hours > 0 else "all",
        "readings": readings
    }

@app.post("/power/collect/{device_id}")
async def collect_power_data(device_id: str):
    """Manually collect and store power data for a device"""
    if not switchbot_client:
        raise HTTPException(status_code=500, detail="SwitchBot client not configured")
    
    power_data = switchbot_client.get_plug_power_data(device_id)
    if power_data is None:
        raise HTTPException(status_code=404, detail="Device not found or no data available")
    
    success = storage.save_power_data(power_data)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save power data")
    
    return {
        "message": "Power data collected successfully",
        "data": power_data
    }

@app.get("/power/latest/{device_id}")
async def get_latest_reading(device_id: str):
    """Get the latest stored reading for a device"""
    latest = storage.get_latest_reading(device_id)
    if latest is None:
        raise HTTPException(status_code=404, detail="No readings found for this device")
    
    return latest

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Dashboard UI for power monitoring"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "switchbot_configured": switchbot_client is not None
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
