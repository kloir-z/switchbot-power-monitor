# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SwitchBot Power Monitor is a real-time power monitoring system for SwitchBot Plug Mini devices running on Raspberry Pi. The system consists of:

- **FastAPI web server** (`main.py`) - REST API and web dashboard on port 8001
- **SwitchBot API client** (`switchbot_client.py`) - Handles authentication and device communication
- **SQLite data storage** (`data_storage.py`) - Stores power readings with timestamps
- **Web dashboard** (`templates/dashboard.html`) - Chart.js-based real-time monitoring interface (database-only)
- **systemd services** - Auto-start API server and 20-second interval data collection
- **Database management** - CSV export, data deletion, statistics functions

## Development Commands

```bash
# Install dependencies
uv sync

# Run the server locally
uv run main.py

# Test API endpoints (database-only)
curl http://localhost:8001/power/db/current
curl http://localhost:8001/power/history/DEVICE_ID?hours=24
curl http://localhost:8001/database/stats

# Access web dashboard
# http://localhost:8001/dashboard
```

## System Architecture

### Core Components

1. **Main FastAPI Application** (`main.py:15`)
   - Initializes SwitchBot client on startup (`main.py:33`)
   - Global variables: `switchbot_client`, `storage`, `DEVICE_ID`
   - Runs on host 0.0.0.0, port 8001

2. **SwitchBot Client** (`switchbot_client.py:11`)
   - HMAC-SHA256 signature authentication (`switchbot_client.py:17`)
   - Base URL: `https://api.switch-bot.com/v1.1`
   - Power data mapping: `weight` field contains instant power (`switchbot_client.py:72`)

3. **Data Storage** (`data_storage.py:8`)
   - SQLite database: `power_data.db`
   - Schema: device_id, timestamp, voltage, electric_current, power, electricity_of_day, power_on
   - Row factory for dict conversion (`data_storage.py:66`)

### API Endpoints

**Data Access (Database-only):**
- `GET /` - API information
- `GET /power/history/{device_id}?hours=24` - Historical data from database
- `GET /power/latest/{device_id}` - Latest stored reading
- `GET /power/db/current` - Current data for all devices (database-only)
- `GET /power/db/latest` - Latest data for all devices (database-only)
- `GET /dashboard` - Web interface
- `GET /health` - Health check

**Database Management:**
- `GET /database/stats` - Database statistics and file info
- `POST /database/export/all?hours=24` - Export all devices data as CSV
- `POST /database/export/{device_id}?hours=24` - Export single device data as CSV
- `DELETE /database/delete/{device_id}?confirm=true` - Delete all data for device
- `DELETE /database/delete/old?minutes=1440&confirm=true` - Delete old data

**System Internal (SwitchBot API calls):**
- `POST /power/collect/all` - Collect data from all known devices (used by systemd timer)

### Environment Configuration

Required `.env` variables:
- `SWITCHBOT_TOKEN` - API token
- `SWITCHBOT_SECRET` - API secret  
- `SWITCHBOT_DEVICE_ID` - Target device ID

### systemd Integration

- **API Server**: `switchbot-power-monitor.service` - Runs main.py as daemon
- **Data Collection**: `switchbot-data-collector.timer` + `.service` - 20-second interval collection
- Working directory: `/home/user/switchbot-power-monitor`
- Virtual environment path: `.venv/bin/python`

### Data Flow

1. systemd timer triggers collection service every 20 seconds
2. Collection service calls `POST /power/collect/all` 
3. API fetches current data from SwitchBot API for all known devices via authenticated client
4. Data stored in SQLite with timestamp
5. Dashboard polls `/power/db/current` (10s) and `/power/history` (30s) for real-time updates from database only

### SwitchBot API Usage Optimization

The system is designed to minimize SwitchBot API calls while maintaining real-time monitoring:

- **Total API calls**: 20-second intervals × 2 devices = 8,640 calls/day (86.4% of 10,000 limit)
- **WebUI access**: 0 API calls (database-only)
- **Removed endpoints**: All unnecessary SwitchBot API endpoints deleted
- **Optimized collection**: Uses database to determine known devices instead of device list API

## Development Notes

- No test framework currently configured
- Uses uv for dependency management
- FastAPI with Jinja2 templates for web interface  
- Chart.js for dashboard visualizations
- SQLite row factory returns dict objects for JSON serialization
- Authentication headers include timestamp, nonce, and HMAC signature