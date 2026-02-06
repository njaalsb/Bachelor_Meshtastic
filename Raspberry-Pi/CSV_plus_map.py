import meshtastic
import meshtastic.serial_interface
from pubsub import pub
from flask import Flask, jsonify, render_template_string, request
import threading
import time
from datetime import datetime
import logging
import asyncio
import discord
import csv
import os

# Skru av werkzeug-spam
logging.getLogger("werkzeug").setLevel(logging.ERROR)

# -------------------------
# Konfigurasjon
# -------------------------
DISCORD_TOKEN = "MTQ2ODI0Nzg0MDEzNTQ1MDc4OA.GdvdE1.Hovxx4XZD0UH9BUh-WZGwHUQLgjvkjQrD7bB38"
DISCORD_CHANNEL_ID = 1468248951076683847

RASPBERRY_PI_POS = (63.4184304, 10.4014815)

CSV_FILE = "meshtastic_log_v2.csv"

CSV_HEADERS = [
    "timestamp",
    "from_id",
    "from_name",
    "text",
    "rssi_dbm",
    "snr_db",
    "hops",
    "latitude",
    "longitude",
    "altitude_m",
    "channel",
]

DEBUG_PRINT_PACKETS = False

# -------------------------
# Discord setup
# -------------------------
intents = discord.Intents.default()
discord_client = discord.Client(intents=intents)
message_queue = asyncio.Queue()

@discord_client.event
async def on_ready():
    print("Discord-bot klar")

    async def send_loop():
        await discord_client.wait_until_ready()
        channel = discord_client.get_channel(DISCORD_CHANNEL_ID)
        if not channel:
            print("Fant ikke Discord-kanal")
            return
        while True:
            msg = await message_queue.get()
            try:
                await channel.send(msg)
            except Exception as e:
                print("Feil ved sending til Discord:", e)
            await asyncio.sleep(0.1)

    asyncio.create_task(send_loop())

# -------------------------
# Flask / kart
# -------------------------
app = Flask(__name__)

messages = []
message_id = 0
node_positions = {}
lock = threading.Lock()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Meshtastic GPS</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
<style>
html, body { margin:0; height:100%; }
#map { width:100%; height:100%; }
</style>
</head>
<body>
<div id="map"></div>
<script>
const map = L.map("map").setView([62, 10], 5);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(map);

L.marker([{{pi_lat}}, {{pi_lon}}]).addTo(map).bindPopup("Basestasjon");

let lastId = -1;

async function poll() {
  const res = await fetch(`/messages?after=${lastId}`);
  const data = await res.json();
  for (const m of data) {
    lastId = m.id;
    if (m.lat && m.lon) {
      L.circleMarker([m.lat, m.lon], {radius:6}).addTo(map)
        .bindPopup(m.text);
    }
  }
}
setInterval(poll, 1000);
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(
        HTML_TEMPLATE,
        pi_lat=RASPBERRY_PI_POS[0],
        pi_lon=RASPBERRY_PI_POS[1]
    )

@app.route("/messages")
def get_messages():
    after = int(request.args.get("after", -1))
    with lock:
        return jsonify([m for m in messages if m["id"] > after])

# -------------------------
# CSV
# -------------------------
def ensure_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=CSV_HEADERS).writeheader()

def append_csv(row):
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=CSV_HEADERS).writerow(row)

# -------------------------
# Helpers
# -------------------------
def get_node_user(interface, from_id):
    node = interface.nodes.get(from_id) or interface.nodes.get(str(from_id)) or {}
    user = node.get("user") or {}
    return node, user

def get_name(interface, from_id):
    _, user = get_node_user(interface, from_id)
    return user.get("longName") or user.get("shortName") or str(from_id)

def get_channel(packet, decoded):
    # Best-effort: finnes ikke alltid
    return (
        packet.get("channel")
        or packet.get("channelIndex")
        or decoded.get("channel")
        or decoded.get("channelIndex")
    )

def fmt_coord(x):
    try:
        return f"{float(x):.6f}"
    except Exception:
        return "?"

# -------------------------
# Meshtastic callback
# -------------------------
def on_receive(packet, interface):
    global message_id

    decoded = packet.get("decoded", {})
    if not decoded:
        return

    port = decoded.get("portnum")
    from_id = packet.get("from")

    if DEBUG_PRINT_PACKETS:
        print("PORT:", port)
        print("PACKET:", packet)
        print("DECODED:", decoded)

    # GPS
    if port == "POSITION_APP":
        pos = decoded.get("position", {}) or {}
        node_positions[from_id] = {
            "lat": pos.get("latitude"),
            "lon": pos.get("longitude"),
            "alt": pos.get("altitude") or pos.get("altitudeMeters") or pos.get("alt"),
            "time": time.time(),
        }
        return

    # Tekst
    if port != "TEXT_MESSAGE_APP":
        return

    text = decoded.get("text")
    if not text:
        return

    pos = node_positions.get(from_id, {}) or {}
    lat = pos.get("lat")
    lon = pos.get("lon")
    alt = pos.get("alt")

    name = get_name(interface, from_id)
    channel = get_channel(packet, decoded)

    with lock:
        messages.append({
            "id": message_id,
            "from": from_id,
            "text": text,
            "lat": lat,
            "lon": lon,
        })
        message_id += 1

    row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "from_id": from_id,
        "from_name": name,
        "text": text,
        "rssi_dbm": packet.get("rxRssi"),
        "snr_db": packet.get("rxSnr"),
        "hops": packet.get("hops"),
        "latitude": lat,
        "longitude": lon,
        "altitude_m": alt,
        "channel": channel,
    }

    with lock:
        append_csv(row)

    # Discord: inkluder posisjon hvis vi har den
    pos_line = ""
    if lat is not None and lon is not None:
        pos_line = f"\n📍 Lat: {fmt_coord(lat)} | Lon: {fmt_coord(lon)}"
        if alt is not None:
            pos_line += f" | Alt: {alt}"

    chan_line = f"\n🛰️ Kanal: {channel}" if channel is not None else ""

    discord_text = (
        f"📡 **Ny Meshtastic-melding**\n"
        f"👤 Fra: **{name}** (`{from_id}`)\n"
        f"💬 {text}"
        f"{pos_line}"
        f"\n📶 RSSI: {row['rssi_dbm']} dBm | 📊 SNR: {row['snr_db']} dB | 🔁 Hopp: {row['hops']}"
        f"{chan_line}"
    )

    asyncio.run_coroutine_threadsafe(
        message_queue.put(discord_text),
        discord_client.loop
    )

# -------------------------
# Start
# -------------------------
def start_meshtastic():
    ensure_csv()
    iface = meshtastic.serial_interface.SerialInterface()
    pub.subscribe(on_receive, "meshtastic.receive")
    while True:
        time.sleep(1)

if __name__ == "__main__":
    ensure_csv()

    threading.Thread(target=start_meshtastic, daemon=True).start()
    threading.Thread(target=lambda: discord_client.run(DISCORD_TOKEN), daemon=True).start()

    print("Nettside: http://<raspberrypi-ip>:5000")
    app.run(host="0.0.0.0", port=5000)
