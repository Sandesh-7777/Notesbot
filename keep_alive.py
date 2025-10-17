#smart keep alive prg
#flask for pinged by uptime robot and self ping if idel for too long
import asyncio
import logging
import aiohttp
import time
from flask import Flask, request
from threading import Thread

# === CONFIG ===
URL = "https://notesbot-0r6v.onrender.com"  # <-- replace with your Render web URL
PING_INTERVAL = 300  # 5 minutes
INACTIVITY_LIMIT = 900  # 15 minutes; stop self-pings if site is already active

app = Flask(__name__)
last_activity = time.time()

@app.route('/')
def home():
    global last_activity
    last_activity = time.time()  # update when anyone (or UptimeRobot) hits it
    return "Bot is alive!"

@app.route('/ping')
def manual_ping():
    return "Ping OK"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

async def ping_server():
    """Periodically ping the Render URL if idle for too long."""
    global last_activity
    while True:
        await asyncio.sleep(PING_INTERVAL)
        idle_time = time.time() - last_activity
        if idle_time < INACTIVITY_LIMIT:
            logging.info("Skipping ping — recent activity detected.")
            continue  # don’t ping if already active
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(URL) as resp:
                    logging.info(f"Self-ping successful ({resp.status})")
        except Exception as e:
            logging.warning(f"Self-ping failed: {e}")

def start_keep_alive():
    """Start the Flask webserver and background ping task."""
    Thread(target=run_flask).start()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(ping_server())
    loop.run_forever()
