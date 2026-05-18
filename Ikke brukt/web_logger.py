import meshtastic
import meshtastic.serial_interface
from pubsub import pub

from flask import Flask, jsonify, render_template_string, request
import threading
import time
from datetime import datetime
import logging

# Skru av Flask/werkzeug spam
logging.getLogger("werkzeug").setLevel(logging.ERROR)

app = Flask(__name__)

# Lagring av meldinger
messages = []
message_id = 0
lock = threading.Lock()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Meshtastic logger</title>
    <style>
        body { font-family: monospace; background: #111; color: #0f0; }
        h1 { color: #6f6; }
        .msg { margin-bottom: 8px; }
    </style>
</head>
<body>
<h1>Meshtastic – mottatte meldinger</h1>
<div id="log"></div>

<script>
let lastId = 0;

async function fetchMessages() {
    const res = await fetch(`/messages?after=${lastId}`);
    const data = await res.json();

    if (data.length > 0) {
        data.forEach(m => {
            const div = document.createElement("div");
            div.className = "msg";
            div.textContent =
                `[${m.time}] fra ${m.from}: ${m.text}`;
            document.getElementById("log").appendChild(div);
            lastId = m.id;
        });
    }
}

setInterval(fetchMessages, 1000);
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/messages")
def get_messages():
    after = int(request.args.get("after", 0))
    with lock:
        new_msgs = [m for m in messages if m["id"] > after]
    return jsonify(new_msgs)

def on_receive(packet, interface):
    global message_id

    if packet.get("decoded", {}).get("text"):
        with lock:
            message_id += 1
            messages.append({
                "id": message_id,
                "time": datetime.now().strftime("%H:%M:%S"),
                "from": packet["from"],
                "text": packet["decoded"]["text"],
            })

        print("Melding mottatt:", packet["decoded"]["text"])

def start_meshtastic():
    try:
        iface = meshtastic.serial_interface.SerialInterface()
        pub.subscribe(on_receive, "meshtastic.receive")
        print("Meshtastic koblet til")

        while True:
            time.sleep(1)

    except Exception as e:
        print("Meshtastic-feil:", e)

if __name__ == "__main__":
    t = threading.Thread(target=start_meshtastic, daemon=True)
    t.start()

    print("Nettside tilgjengelig på http://<raspberrypi-ip>:5000")
    app.run(host="0.0.0.0", port=5000)
