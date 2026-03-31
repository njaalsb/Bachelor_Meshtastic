import meshtastic
import meshtastic.serial_interface
import time

# ── Configuration ──
SERIAL_PORT = "/dev/ttyACM1"
DESTINATION_NODE = "!9eeff3c4"  # Node ID to send to
MESSAGE_BYTES = 200             # Size of each message in bytes
DELAY_SECONDS = 0.5               # Delay between messages

# ── Setup ──
interface = meshtastic.serial_interface.SerialInterface(devPath=SERIAL_PORT)

def run():
    print(f"Sending {MESSAGE_BYTES}-byte messages to {DESTINATION_NODE} every {DELAY_SECONDS}s")
    print("Press Ctrl+C to stop.\n")

    count = 0
    padding = "X" * MESSAGE_BYTES  # pre-build oversized padding

    try:
        while True:
            count += 1
            header = f"#{count} "
            message = (header + padding)[:MESSAGE_BYTES]

            print(f"[{count}] Sending {len(message.encode('utf-8'))} bytes to {DESTINATION_NODE}")
            interface.sendText(message, destinationId=DESTINATION_NODE)
            time.sleep(DELAY_SECONDS)

    except KeyboardInterrupt:
        print(f"\nStopped after {count} packets.")
    finally:
        interface.close()

if __name__ == "__main__":
    run()
