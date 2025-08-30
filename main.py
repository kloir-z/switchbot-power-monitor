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
            "/power/history/{device_id} - Get power history from database",
            "/power/latest/{device_id} - Get latest stored reading",
            "/power/db/current - Get current readings from database",
            "/database/stats - Get database statistics",
            "/dashboard - Web monitoring interface"
        ]
    }



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

@app.post("/power/collect/all")
async def collect_all_power_data():
    """Collect and store power data for known devices (optimized - no device list fetching)"""
    if not switchbot_client:
        raise HTTPException(status_code=500, detail="SwitchBot client not configured")
    
    # Get known device IDs from database instead of API
    try:
        import sqlite3
        conn = sqlite3.connect(storage.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT device_id FROM power_readings WHERE device_id != 'all'")
        known_device_ids = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if not known_device_ids:
            # Fallback to environment variable if no devices in DB
            env_device_id = os.getenv("SWITCHBOT_DEVICE_ID")
            if env_device_id:
                known_device_ids = [env_device_id]
            else:
                raise HTTPException(status_code=500, detail="No known devices found in database or environment")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get known devices: {str(e)}")
    
    results = {}
    success_count = 0
    
    # Collect power data for each known device (no device list API call needed)
    for device_id in known_device_ids:
        power_data = switchbot_client.get_plug_power_data(device_id)
        if power_data:
            success = storage.save_power_data(power_data)
            device_name = f"SwitchBot Plug Mini ({device_id[-4:]})"
            results[device_id] = {
                "name": device_name,
                "success": success,
                "data": power_data if success else None
            }
            if success:
                success_count += 1
        else:
            results[device_id] = {
                "name": f"SwitchBot Plug Mini ({device_id[-4:]})",
                "success": False,
                "error": "Failed to get power data"
            }
    
    return {
        "message": f"Collected data for {success_count}/{len(known_device_ids)} devices",
        "results": results
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



@app.get("/power/db/latest")
async def get_db_latest_readings():
    """Get latest stored readings from database only (no API calls)"""
    try:
        import sqlite3
        conn = sqlite3.connect(storage.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get latest reading for each device
        cursor.execute("""
            SELECT device_id, MAX(timestamp) as latest_timestamp
            FROM power_readings 
            WHERE device_id != 'all'
            GROUP BY device_id
        """)
        
        results = {}
        for row in cursor.fetchall():
            device_id = row['device_id']
            latest = storage.get_latest_reading(device_id)
            if latest:
                results[device_id] = {
                    "name": f"SwitchBot Plug Mini ({device_id[-4:]})",  # Show last 4 chars for identification
                    "data": latest
                }
        
        conn.close()
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/power/db/current")
async def get_db_current_readings():
    """Get current readings from database only (alias for latest)"""
    return await get_db_latest_readings()

@app.get("/database/stats")
async def get_database_stats():
    """Get database statistics"""
    try:
        import sqlite3
        import os
        
        db_path = storage.db_path
        if not os.path.exists(db_path):
            raise HTTPException(status_code=404, detail="Database file not found")
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get file size
        file_size = os.path.getsize(db_path)
        
        # Get total records count (exclude 'all' device)
        cursor.execute("SELECT COUNT(*) as total FROM power_readings WHERE device_id != 'all'")
        total_records = cursor.fetchone()[0]
        
        # Get records count by device (exclude 'all' device)
        cursor.execute("""
            SELECT device_id, COUNT(*) as count, 
                   MIN(timestamp) as first_record, 
                   MAX(timestamp) as last_record
            FROM power_readings 
            WHERE device_id != 'all'
            GROUP BY device_id 
            ORDER BY device_id
        """)
        device_stats = []
        for row in cursor.fetchall():
            device_stats.append({
                "device_id": row[0],
                "record_count": row[1],
                "first_record": row[2],
                "last_record": row[3],
                "first_record_date": datetime.fromtimestamp(row[2]).isoformat() if row[2] else None,
                "last_record_date": datetime.fromtimestamp(row[3]).isoformat() if row[3] else None
            })
        
        # Get recent activity (last 24 hours, exclude 'all' device)
        cursor.execute("""
            SELECT device_id, COUNT(*) as count 
            FROM power_readings 
            WHERE timestamp >= ? AND device_id != 'all'
            GROUP BY device_id
        """, (int(datetime.now().timestamp()) - 86400,))
        recent_activity = {row[0]: row[1] for row in cursor.fetchall()}
        
        conn.close()
        
        # Format file size with appropriate units
        def format_file_size(size_bytes):
            if size_bytes < 1024:
                return f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                return f"{round(size_bytes / 1024, 2)} KB"
            elif size_bytes < 1024 * 1024 * 1024:
                return f"{round(size_bytes / 1024 / 1024, 2)} MB"
            else:
                return f"{round(size_bytes / 1024 / 1024 / 1024, 2)} GB"
        
        return {
            "database_file": db_path,
            "file_size_bytes": file_size,
            "file_size_formatted": format_file_size(file_size),
            "file_size_mb": round(file_size / 1024 / 1024, 2),
            "total_records": total_records,
            "device_statistics": device_stats,
            "recent_activity_24h": recent_activity,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.post("/database/export/all")
async def export_all_data(hours: int = 24):
    """Export all device data as CSV"""
    try:
        from fastapi.responses import StreamingResponse
        import csv
        import io
        import sqlite3
        
        conn = sqlite3.connect(storage.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if hours > 0:
            hours_ago = int(datetime.now().timestamp()) - (hours * 3600)
            cursor.execute("""
                SELECT * FROM power_readings 
                WHERE timestamp >= ? AND device_id != ?
                ORDER BY timestamp DESC
            """, (hours_ago, 'all'))
        else:
            cursor.execute("SELECT * FROM power_readings WHERE device_id != ? ORDER BY timestamp DESC", ('all',))
        
        readings = cursor.fetchall()
        conn.close()
        
        if not readings:
            raise HTTPException(status_code=404, detail="No data found for ALL DEVICES in the specified time range")
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['timestamp', 'datetime', 'device_id', 'voltage', 'electric_current', 'power', 'electricity_of_day', 'power_on'])
        
        # Write data
        for reading in readings:
            dt_str = datetime.fromtimestamp(reading['timestamp']).isoformat()
            writer.writerow([
                reading['timestamp'],
                dt_str,
                reading['device_id'],
                reading['voltage'],
                reading['electric_current'],
                reading['power'],
                reading['electricity_of_day'],
                reading['power_on']
            ])
        
        output.seek(0)
        
        # Create filename
        timerange_str = f"{hours}h" if hours > 0 else "all"
        filename = f"switchbot_data_all_devices_{timerange_str}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8')),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"All devices export error: {str(e)}")

@app.post("/database/export/{device_id}")
async def export_device_data(device_id: str, hours: int = 24):
    """Export device data as CSV"""
    try:
        from fastapi.responses import StreamingResponse
        import csv
        import io
        
        readings = storage.get_readings_by_timerange(device_id, hours) if hours > 0 else storage.get_all_readings(device_id)
        
        if not readings:
            raise HTTPException(status_code=404, detail="No data found for this device")
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['timestamp', 'datetime', 'device_id', 'voltage', 'electric_current', 'power', 'electricity_of_day', 'power_on'])
        
        # Write data
        for reading in readings:
            dt_str = datetime.fromtimestamp(reading['timestamp']).isoformat()
            writer.writerow([
                reading['timestamp'],
                dt_str,
                reading['device_id'],
                reading['voltage'],
                reading['electric_current'],
                reading['power'],
                reading['electricity_of_day'],
                reading['power_on']
            ])
        
        output.seek(0)
        
        # Create filename
        timerange_str = f"{hours}h" if hours > 0 else "all"
        filename = f"switchbot_data_{device_id}_{timerange_str}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8')),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export error: {str(e)}")

@app.delete("/database/delete/{device_id}")
async def delete_device_data(device_id: str, confirm: bool = False):
    """Delete all data for a specific device"""
    if not confirm:
        raise HTTPException(status_code=400, detail="Confirmation required. Add ?confirm=true to delete data.")
    
    try:
        import sqlite3
        conn = sqlite3.connect(storage.db_path)
        cursor = conn.cursor()
        
        # Get count before deletion
        cursor.execute("SELECT COUNT(*) FROM power_readings WHERE device_id = ?", (device_id,))
        count_before = cursor.fetchone()[0]
        
        if count_before == 0:
            raise HTTPException(status_code=404, detail="No data found for this device")
        
        # Delete data
        cursor.execute("DELETE FROM power_readings WHERE device_id = ?", (device_id,))
        conn.commit()
        conn.close()
        
        return {
            "message": f"Deleted {count_before} records for device {device_id}",
            "device_id": device_id,
            "deleted_records": count_before,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deletion error: {str(e)}")

@app.delete("/database/delete/old")
async def delete_old_data(minutes: int = 1440, confirm: bool = False):
    """Delete data older than specified minutes (default: 1440 minutes = 24 hours)"""
    if not confirm:
        raise HTTPException(status_code=400, detail="Confirmation required. Add ?confirm=true to delete data.")
    
    if minutes < 1:
        raise HTTPException(status_code=400, detail="Minutes must be at least 1")
    
    try:
        import sqlite3
        conn = sqlite3.connect(storage.db_path)
        cursor = conn.cursor()
        
        # Calculate cutoff timestamp
        cutoff_timestamp = int(datetime.now().timestamp()) - (minutes * 60)
        
        # Get count before deletion
        cursor.execute("SELECT COUNT(*) FROM power_readings WHERE timestamp < ?", (cutoff_timestamp,))
        count_before = cursor.fetchone()[0]
        
        if count_before == 0:
            return {
                "message": f"No records older than {minutes} minutes found",
                "deleted_records": 0,
                "timestamp": datetime.now().isoformat()
            }
        
        # Delete old data
        cursor.execute("DELETE FROM power_readings WHERE timestamp < ?", (cutoff_timestamp,))
        conn.commit()
        conn.close()
        
        return {
            "message": f"Deleted {count_before} records older than {minutes} minutes",
            "deleted_records": count_before,
            "cutoff_minutes": minutes,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Old data deletion error: {str(e)}")

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
