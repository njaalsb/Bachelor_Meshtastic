import meshtastic
import meshtastic.serial_interface
from pubsub import pub
import plotext as plt
import time

# Lister for logging
snr_values = []
rssi_values = []
packet_count = []

PLOT_AFTER = 2  # plotter etter 10 pakker

def on_receive(packet, interface):
    decoded = packet.get("decoded", {})
    text = decoded.get("text") or decoded.get("data", {}).get("text")
    sender = packet.get("from", "ukjent")

    if text:
        print(f"Mottatt melding fra {sender}: {text}")
        try:
            interface.sendText(f"Echo: {text}")  # sender tilbake på aktiv kanal
            print(f"Sendt tilbake til {sender}: {text}")
        except Exception as e:
            print("Feil ved sending:", e)

    telemetry = packet.get("telemetry", {})
    if telemetry:
        rssi = telemetry.get("rssi")
        snr = telemetry.get("snr")
        if rssi is not None and snr is not None:
            rssi_values.append(rssi)
            snr_values.append(snr)
            packet_count.append(len(packet_count)+1)
            print(f"RSSI: {rssi}, SNR: {snr}")

            # Når vi har 10 pakker, plotter vi i terminal
            if len(packet_count) >= PLOT_AFTER:
                plt.clp()  # clear previous plot
                plt.plot(packet_count, rssi_values, label="RSSI (dB)")
                plt.plot(packet_count, snr_values, label="SNR (dB)")
                plt.title("Radiokvalitet siste 10 pakker")
                plt.xlabel("Pakke #")
                plt.ylabel("dB")
                plt.legend()
                plt.show()
                print("\n--- Plot ferdig ---\n")

                # Nullstill for neste batch
                snr_values.clear()
                rssi_values.clear()
                packet_count.clear()

def main():
    iface = meshtastic.serial_interface.SerialInterface()
    print("Lytter etter meldinger... Ctrl+C for å avslutte")

    pub.subscribe(on_receive, "meshtastic.receive")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Avslutter...")
        iface.close()

if __name__ == "__main__":
    main()
