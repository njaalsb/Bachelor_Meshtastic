import meshtastic
import meshtastic.serial_interface
from pubsub import pub
import time

def on_receive(packet, interface):
    # Sjekk om pakken har "decoded"
    decoded = packet.get("decoded", {})
    if not decoded:
        return

    # Tekstmeldinger har type "TEXT" eller "text"
    if decoded.get("type", "").lower() == "text":
        # Tekst kan ligge under decoded["text"] eller decoded["data"]["text"]
        text = decoded.get("text") or decoded.get("data", {}).get("text")
        sender = packet.get("from", "ukjent")
        if text:
            print(f"Mottatt melding fra {sender}: {text}")
    else:
        # For debugging, print alle andre pakker
        print("Annen pakke mottatt:", decoded)

def main():
    iface = meshtastic.serial_interface.SerialInterface()
    print("Lytter etter meldinger... Ctrl+C for å avslutte")

    # Abonner på alle innkommende pakker
    pub.subscribe(on_receive, "meshtastic.receive")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Avslutter...")
        iface.close()

if __name__ == "__main__":
    main()
