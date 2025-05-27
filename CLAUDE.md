# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Development
- `make` - Install dependencies and run the server on port 80
- `make install` - Install Python dependencies from requirements.txt
- `make run` - Run the server without installing dependencies
- `make run HOST=0.0.0.0` - Run with IPv4 if IPv6 unavailable
- `make run PORT=8080` - Run on specific port

### Docker
- `docker build -t lunarsensor .` - Build Docker image
- `docker run -p 127.0.0.1:8080:80 -d lunarsensor` - Run container on localhost:8080

## Architecture

This is an ambient light sensor server that provides lux readings to the Lunar macOS app for automatic monitor brightness control.

### Core Components

**FastAPI Server (`lunarsensor.py`)**
- Provides REST API endpoint `/sensor/ambient_light` for one-shot lux readings
- Provides EventSource endpoint `/events` that streams lux values every 2 seconds
- Uses global `last_lux` variable to track state and only send updates when values change
- Implements async/await pattern with aiohttp client session management

**Sensor Reading Logic**
- The `read_lux()` function at the bottom of `lunarsensor.py` is where actual sensor implementation goes
- Base implementation reads from `/tmp/lux` file or returns default 400.0 lux
- Uses `sensor_lock` for thread-safe access to potentially blocking I/O operations
- Offloads sync operations to executor to maintain async performance

**HomeAssistant Addon**
- Separate implementation in `homeassistant_addon/lunarsensor.py`
- Polls HomeAssistant sensor entities via REST API using supervisor token
- Configured via `SENSOR_ENTITY_ID` environment variable
- Runs on port 8899 inside HomeAssistant

### Data Flow
1. Lunar app connects to `lunarsensor.local` (configurable via macOS defaults)
2. Server streams lux readings via Server-Sent Events
3. Lunar adjusts monitor brightness based on ambient light levels

### Environment Variables
- `SENSOR_DEBUG=1` - Enable debug logging
- `HOST` - Server host (default: `::`)
- `PORT` - Server port (default: 80)
- `TD_USB_SCRIPT` - Path to td-usb script (default: `td-usb`)
- `SENSOR_ENTITY_ID` - HomeAssistant sensor entity ID (addon only)
- `SUPERVISOR_TOKEN` - HomeAssistant supervisor token (addon only)

### Auto-start Setup
- `./setup-autostart.sh` - Configure service to start automatically on login
- Service logs: `~/Library/Logs/lunarsensor.log`
- Stop service: `launchctl unload ~/Library/LaunchAgents/com.lunarsensor.plist`
- Start service: `launchctl load ~/Library/LaunchAgents/com.lunarsensor.plist`

### Testing
- One-shot: `curl lunarsensor.local/sensor/ambient_light`
- Streaming: `curl -N lunarsensor.local/events`