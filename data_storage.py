import json
import sqlite3
import os
from datetime import datetime
from typing import Dict, List, Optional


class PowerDataStorage:
    def __init__(self, db_path: str = "power_data.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database for power data storage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS power_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                voltage REAL,
                electric_current REAL,
                power REAL,
                electricity_of_day REAL,
                power_on BOOLEAN,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_power_data(self, data: Dict) -> bool:
        """Save power data to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO power_readings 
                (device_id, timestamp, voltage, electric_current, power, electricity_of_day, power_on)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get("device_id"),
                data.get("timestamp"),
                data.get("voltage"),
                data.get("electric_current"),
                data.get("power"),
                data.get("electricity_of_day"),
                data.get("power_on")
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving data: {e}")
            return False
    
    def get_latest_reading(self, device_id: str) -> Optional[Dict]:
        """Get the latest power reading for a device"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM power_readings 
                WHERE device_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 1
            ''', (device_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return dict(row)
            return None
        except Exception as e:
            print(f"Error getting latest reading: {e}")
            return None
    
    def get_readings_by_timerange(self, device_id: str, hours: int = 24) -> List[Dict]:
        """Get power readings within specified hours"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Calculate timestamp for N hours ago
            hours_ago = int(datetime.now().timestamp()) - (hours * 3600)
            
            cursor.execute('''
                SELECT * FROM power_readings 
                WHERE device_id = ? AND timestamp >= ?
                ORDER BY timestamp DESC
            ''', (device_id, hours_ago))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting readings by timerange: {e}")
            return []
    
    def get_all_readings(self, device_id: str, limit: int = 1000) -> List[Dict]:
        """Get all power readings for a device"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM power_readings 
                WHERE device_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (device_id, limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting all readings: {e}")
            return []