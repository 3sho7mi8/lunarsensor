import json
import logging
import os
import time
import asyncio

import aiohttp
from fastapi import FastAPI, Request
from sse_starlette.sse import EventSourceResponse

app = FastAPI()
logging.basicConfig()
log = logging.getLogger("lunarsensor")
log.level = logging.DEBUG if os.getenv("SENSOR_DEBUG") == "1" else logging.INFO

POLLING_SECONDS = 2
CLIENT = None
last_lux = 400
sensor_lock = asyncio.Lock()  # serialize sensor or file access

@app.on_event("startup")
async def startup_event():
    global CLIENT
    CLIENT = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8))

@app.on_event("shutdown")
async def shutdown() -> None:
    if CLIENT:
        await CLIENT.close()

async def make_lux_response():
    global last_lux
    try:
        lux = await read_lux()
    except Exception as exc:
        log.exception(exc)
    else:
        if lux is not None and lux != last_lux:
            log.debug(f"Sending {lux} lux")
            last_lux = lux

    return {"id": "sensor-ambient_light", "state": f"{last_lux} lx", "value": last_lux}

async def sensor_reader(request):
    while not await request.is_disconnected():
        yield {"event": "state", "data": json.dumps(await make_lux_response())}
        await asyncio.sleep(POLLING_SECONDS)

@app.get("/sensor/ambient_light")
async def sensor():
    return await make_lux_response()

@app.get("/events")
async def events(request: Request):
    event_generator = sensor_reader(request)
    return EventSourceResponse(event_generator)

# Synchronous helper for reading lux (e.g. from file or sensor)
def _sync_read_lux():
    import subprocess
    
    # Get td-usb command path from environment or use default
    td_usb_script = os.getenv("TD_USB_SCRIPT", "td-usb")
    
    try:
        # Try to get lux value from td-usb iws660 sensor
        result = subprocess.run(
            [td_usb_script, "iws660", "get"],
            capture_output=True,
            text=True,
            timeout=3,  # Short timeout to fail quickly
            stdin=subprocess.DEVNULL  # Don't wait for password input
        )
        
        if result.returncode == 0:
            # Parse the output to extract lux value
            output = result.stdout.strip()
            
            # Try to extract numeric value from output
            import re
            
            # Try different patterns for lux values
            patterns = [
                r'(\d+\.?\d*)\s*lux',  # "123.45 lux"
                r'lux:\s*(\d+\.?\d*)',  # "lux: 123.45"
                r'(\d+\.?\d*)',  # Just a number
            ]
            
            lux_value = None
            for pattern in patterns:
                match = re.search(pattern, output, re.IGNORECASE)
                if match:
                    lux_value = float(match.group(1))
                    break
            
            if lux_value is not None:
                log.debug(f"td-usb iws660 lux reading: {lux_value}")
                return lux_value
            else:
                log.warning(f"Could not parse lux value from td-usb output: {output}")
        else:
            log.warning(f"td-usb command failed: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        log.warning("td-usb command timed out")
    except Exception as e:
        log.warning(f"Error reading from td-usb: {e}")
    
    # Fallback: try reading from file
    if os.path.exists("/tmp/lux"):
        with open("/tmp/lux") as f:
            return float(f.read().strip() or "400.0")
    
    # Default fallback value
    return 400.0

async def read_lux():
    # Offload potentially blocking I/O into executor, serializing with a lock
    loop = asyncio.get_running_loop()
    async with sensor_lock:
        lux = await loop.run_in_executor(None, _sync_read_lux)
    return lux
