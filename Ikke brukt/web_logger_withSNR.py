import meshtastic
import meshtastic.serial_interface
from pubsub import pub
from flask import Flask, jsonify, render_template_string, request
import threading
import time
from datetime import datetime
import logging

# Skru av werkzeug-spam
logging.getLogger("werkzeug").setLevel(logging.ERROR)

app = Flask(__name__)

messages = []
message_id = 0
lock = threading.Lock()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Meshtastic logg</title>
    <style>
        body { font-family: monospace; background: #111; color: #0f0; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #0f0; padding: 4px; }
        th { background: #030; }
    </style>
</head>
<body>
<h2>Meshtastic meldingslogg</h2>
<table id="log">
    <tr>
        <th>ID</th>
        <th>Tid</th>
        <th>Node</th>
        <th>Melding</th>
        <th>SNR (dB)</th>
        <th>RSSI (dBm)</th>
    </tr>
</table>

<script>
let lastId = -1;

async function poll() {
    const res = await fetch(`/messages?after=${lastId}`);
    const data = await res.json();

    for (const msg of data) {
        lastId = msg.id;
        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${msg.id}</td>
            <td>${msg.time}</td>
            <td>${msg.from}</td>
            <td>${msg.text}</td>
            <td>${msg.snr ?? "-"}</td>
            <td>${msg.rssi ?? "-"}</td>
        `;
        document.getElementById("log").appendChild(row);
    }
}

setInterval(poll, 1000);
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/messages")
def get_messages():
    after = int(request.args.get("after", -1))
    with lock:
        return jsonify([m for m in messages if m["id"] > after])

def on_receive(packet, interface):
    global message_id

    decoded = packet.get("decoded", {})
    if not decoded:
        return

    if decoded.get("portnum") != "TEXT_MESSAGE_APP":
        return

    text = decoded.get("text")
    if not text:
        return

    with lock:
        messages.append({
            "id": message_id,
            "time": datetime.now().strftime("%H:%M:%S"),
            "from": packet.get("from", "ukjent"),
            "text": text,
            "snr": packet.get("rxSnr"),
            "rssi": packet.get("rxRssi"),
        })
        message_id += 1

    print(f"Melding mottatt | SNR={packet.get('rxSnr')} RSSI={packet.get('rxRssi')}")

def start_meshtastic():
    iface = meshtastic.serial_interface.SerialInterface()
    pub.subscribe(on_receive, "meshtastic.receive")
    while True:
        time.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=start_meshtastic, daemon=True).start()
    print("Nettside: http://<raspberrypi-ip>:5000")
    app.run(host="0.0.0.0", port=5000)
