#!/bin/bash
# Lunar Sensor Auto-start Setup Script

set -e

USER_HOME="${HOME}"
CURRENT_DIR="$(pwd)"
VENV_UVICORN="${CURRENT_DIR}/venv/bin/uvicorn"

# Check if uvicorn exists in venv
if [ ! -f "${VENV_UVICORN}" ]; then
    echo "Error: uvicorn not found at ${VENV_UVICORN}"
    echo "Please run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi
PLIST_FILE="${USER_HOME}/Library/LaunchAgents/com.lunarsensor.plist"
LOG_DIR="${USER_HOME}/Library/Logs"

echo "Setting up Lunar Sensor auto-start service..."

# Create log directory if it doesn't exist
mkdir -p "${LOG_DIR}"

# Create the plist file
cat > "${PLIST_FILE}" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.lunarsensor</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>${VENV_UVICORN}</string>
        <string>lunarsensor:app</string>
        <string>--host</string>
        <string>0.0.0.0</string>
        <string>--port</string>
        <string>8080</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>${CURRENT_DIR}</string>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <true/>
    
    <key>StandardOutPath</key>
    <string>${LOG_DIR}/lunarsensor.log</string>
    
    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/lunarsensor.error.log</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
EOF

echo "Created plist file: ${PLIST_FILE}"

# Load the service
launchctl load "${PLIST_FILE}"

echo "Loaded service. Checking status..."
sleep 2

# Check if service is running
if launchctl list | grep -q "com.lunarsensor"; then
    echo "✅ Lunar Sensor service is running"
    echo "Service will auto-start on login"
    echo ""
    echo "Management commands:"
    echo "  Stop:  launchctl unload ${PLIST_FILE}"
    echo "  Start: launchctl load ${PLIST_FILE}"
    echo "  Logs:  tail -f ${LOG_DIR}/lunarsensor.log"
else
    echo "❌ Failed to start service"
    exit 1
fi