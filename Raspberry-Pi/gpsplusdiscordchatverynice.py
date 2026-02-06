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

# Skru av werkzeug-spam
logging.getLogger("werkzeug").setLevel(logging.ERROR)

# -------------------------
# Konfigurasjon
# -------------------------
DISCORD_TOKEN = "MTQ2ODI0Nzg0MDEzNTQ1MDc4OA.GdvdE1.Hovxx4XZD0UH9BUh-WZGwHUQLgjvkjQrD7bB38"
DISCORD_CHANNEL_ID = 1468248951076683847  # Discord kanal

RASPBERRY_PI_POS = (63.4184304, 10.4014815)  # A366

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
            print(f"FEIL: Finner ikke kanalen {DISCORD_CHANNEL_ID}")
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
# Flask / kart-oppsett
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
    <title>Meshtastic GPS Norge</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
    <style>
        body, html { margin: 0; height: 100%; }
        #map { width: 100%; height: 100%; }
    </style>
</head>
<body>
<div id="map"></div>
<script>
const norwayCenter = [62.0, 10.0];
const map = L.map("map").setView(norwayCenter, 5);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(map);

const houseIcon = L.icon({
    iconUrl: 'https://cdn-icons-png.flaticon.com/512/25/25694.png',
    iconSize: [32, 32],
    iconAnchor: [16, 32]
});

L.marker([{{pi_lat}}, {{pi_lon}}], {icon: houseIcon})
 .addTo(map)
 .bindPopup("<b>Basestasjon (Pi)</b>");

let lastId = -1;
let nodeColors = {};

async function poll() {
    const res = await fetch(`/messages?after=${lastId}`);
    const data = await res.json();

    for (const msg of data) {
        lastId = msg.id;
        if (msg.lat && msg.lon) {
            if (!nodeColors[msg.from]) {
                nodeColors[msg.from] =
                    '#' + Math.floor(Math.random()*16777215).toString(16);
            }
            const color = nodeColors[msg.from];

            L.circleMarker([msg.lat, msg.lon], {
                radius: 8,
                color: color,
                fillColor: color,
                fillOpacity: 0.7
            }).addTo(map)
              .bindPopup(`<b>${msg.from}</b><br>${msg.text}<br>${msg.time}`);

            L.polyline([[{{pi_lat}}, {{pi_lon}}], [msg.lat, msg.lon]], {
                color: color,
                weight: 2,
                opacity: 0.7
            }).addTo(map);
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
# Meshtastic callback
# -------------------------
def on_receive(packet, interface):
    global message_id

    decoded = packet.get("decoded", {})
    if not decoded:
        return

    port = decoded.get("portnum")

    # GPS-posisjon
    if port == "POSITION_APP":
        pos = decoded.get("position", {})
        lat = pos.get("latitude")
        lon = pos.get("longitude")
        if lat and lon:
            node_positions[packet["from"]] = {
                "lat": lat,
                "lon": lon,
                "time": time.time()
            }
        return

    # Tekstmeldinger
    if port != "TEXT_MESSAGE_APP":
        return

    text = decoded.get("text")
    if not text:
        return

    pos = node_positions.get(packet["from"])

    # Lagre for kart
    with lock:
        messages.append({
            "id": message_id,
            "time": datetime.now().strftime("%H:%M:%S"),
            "from": packet["from"],
            "text": text,
            "lat": pos["lat"] if pos else None,
            "lon": pos["lon"] if pos else None,
        })
        message_id += 1

    # Metadata
    rssi = packet.get("rxRssi")
    snr = packet.get("rxSnr")

    node = interface.nodes.get(packet["from"], {})
    user = node.get("user", {})
    long_name = user.get("longName", packet["from"])
    hops = packet.get("hops", "0")

    discord_message = (
        f"📡 **Ny Meshtastic-melding**\n"
        f"👤 Fra: **{long_name}** (`{packet['from']}`)\n"
        f"💬 {text}\n"
        f"📶 RSSI: {rssi} dBm\n"
        f"📊 SNR: {snr} dB\n"
        f"🔁 Hopp: {hops}\n"
    )

    # Legg i queue for Discord
    asyncio.run_coroutine_threadsafe(
        message_queue.put(discord_message),
        discord_client.loop
    )

    print(f"Melding fra {long_name}: {text}")

# -------------------------
# Start Meshtastic
# -------------------------
def start_meshtastic():
    iface = meshtastic.serial_interface.SerialInterface()
    pub.subscribe(on_receive, "meshtastic.receive")
    while True:
        time.sleep(1)

# -------------------------
# Main
# -------------------------
if __name__ == "__main__":
    threading.Thread(target=start_meshtastic, daemon=True).start()

    threading.Thread(
        target=lambda: discord_client.run(DISCORD_TOKEN),
        daemon=True
    ).start()

    print("Nettside: http://<raspberrypi-ip>:5000")
    app.run(host="0.0.0.0", port=5000)
