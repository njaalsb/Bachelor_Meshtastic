import meshtastic
import meshtastic.serial_interface
import time

# Opprett interface til den første tilgjengelige noden
iface = meshtastic.serial_interface.SerialInterface()

try:
    while True:
        iface.sendText(f"Kjør da!")
        print("Ping sendt!")
        time.sleep(15)  # sender hvert 15. sekund
except KeyboardInterrupt:
    print("Avslutter...")
    iface.close()
