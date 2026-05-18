import paho.mqtt.client as mqtt
import time

# --- DIN INFO ---
MQTT_BROKER = "127.0.0.1" 
NODE_ID = "!720472da"
TOPIC = f"msh/2/c/LongFast/{NODE_ID}" # Vi antar kanalen heter LongFast
IMAGE_PATH = "onMyMama.jpg"

def on_connect(client, userdata, flags, rc):
    print(f"Koblet til Mosquitto med resultat: {rc}")

client = mqtt.Client()
client.on_connect = on_connect

try:
    client.connect(MQTT_BROKER, 1883, 60)
except:
    print("Kunne ikke koble til Mosquitto. Er tjenesten startet?")

while True:
    try:
        if os.path.exists(IMAGE_PATH):
            with open(IMAGE_PATH, "rb") as f:
                image_data = f.read()
            
            # Sender bildet som en binær "blob"
            client.publish(TOPIC, image_data)
            print(f"[{time.ctime()}] Bilde dyttet til MQTT-køen.")
        else:
            print(f"Fant ikke {IMAGE_PATH}")
            
    except Exception as e:
        print(f"Feil: {e}")
    
    time.sleep(60)
