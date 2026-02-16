#!/usr/bin/env python3
import argparse
import time
import meshtastic.serial_interface

def main():
    ap = argparse.ArgumentParser(description="Send 1..255 byte TEXT messages over Meshtastic")
    ap.add_argument("--dev", default=None, help="Serial device path, e.g. COM6 or /dev/ttyACM0 (optional)")
    ap.add_argument("--channel", type=int, default=0, help="Channel index (default 0)")
    ap.add_argument("--delay", type=float, default=1.0, help="Seconds between sends (default 1.0)")
    ap.add_argument("--repeat", type=int, default=1, help="How many times to run 1..255 (default 1)")
    ap.add_argument("--dest", default=None, help="Optional destination node id. If omitted, normal/broadcast behavior.")
    args = ap.parse_args()

    iface = meshtastic.serial_interface.SerialInterface(devPath=args.dev) if args.dev else meshtastic.serial_interface.SerialInterface()
    print("Koblet til Meshtastic.")

    try:
        for r in range(args.repeat):
            if args.repeat > 1:
                print(f"\n--- Runde {r+1}/{args.repeat} ---")

            for n in range(1, 256):
                payload = "A" * n  # 1 byte per tegn (ASCII/UTF-8)

                try:
                    kwargs = {"channelIndex": args.channel}
                    if args.dest:
                        kwargs["destinationId"] = args.dest  # bare hvis satt

                    iface.sendText(payload, **kwargs)
                    print(f"Sendt {n:3d} bytes")
                except Exception as e:
                    print(f"FEIL på {n} bytes: {e}")

                time.sleep(args.delay)

    finally:
        try:
            iface.close()
        except Exception:
            pass
        print("Avsluttet.")

if __name__ == "__main__":
    main()
