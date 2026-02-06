import meshtastic
import meshtastic.serial_interface
from pubsub import pub
import time

def on_receive(packet, interface):
    decoded = packet.get("decoded", {})

    # Hvis pakken har "text", uansett type
    text = decoded.get("text") or decoded.get("data", {}).get("text")
    if text:
        sender = packet.get("from", "ukjent")
        print(f"Mottatt melding fra {sender}: {text}")

        # Send tilbake samme tekst
        try:
            interface.sendText(f"Echo: {text}")
            print(f"Sendt tilbake til {sender}: {text}")
        except Exception as e:
            print("Feil ved sending:", e)
    else:
        # For debugging
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


