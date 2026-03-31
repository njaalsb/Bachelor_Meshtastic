#!/usr/bin/env python3
"""
Meshtastic Transmission Time Logger

Listens for incoming telemetry packets on a Meshtastic radio and logs
the packet's sent timestamp, local receive timestamp, and the
transmission time difference to a CSV file.

Requirements:
    pip install meshtastic

Usage:
    python3 transmission_time_logger.py
"""

import csv
import os
import time
from datetime import datetime, timezone

import meshtastic
import meshtastic.serial_interface
from pubsub import pub

# =============================================================================
# CONFIGURATION
# =============================================================================

# Node IDs to monitor. Add node IDs as hex strings (e.g., "!a1b2c3d4").
# Leave the list empty to log packets from ALL nodes.
MONITORED_NODES: list[str] = [
    "!9eeff3a4"
    # "!a1b2c3de",
    # "!deadbeef",
]

# Path to the output CSV file
CSV_FILE = "no_congestion.csv" #"transmission_time_log.csv"

# Serial device path (set to None for auto-detect)
SERIAL_DEVICE = "/dev/ttyACM0"  # e.g., "/dev/ttyUSB0" or "/dev/ttyACM0"

# =============================================================================
# END OF CONFIGURATION
# =============================================================================

CSV_HEADERS = [
    "node_id",
    "packet_timestamp",
    "receive_timestamp",
    "transmission_time_seconds",
]


def init_csv(filepath: str) -> None:
    """Create the CSV file with headers if it doesn't already exist."""
    if not os.path.exists(filepath):
        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)
        print(f"[INFO] Created new CSV file: {filepath}")
    else:
        print(f"[INFO] Appending to existing CSV file: {filepath}")


def on_receive(packet, interface):
    """Callback for every received packet. Filters for telemetry and logs timing."""
    try:
        # Record local receive time immediately
        receive_time_unix = time.time()
        receive_dt = datetime.fromtimestamp(receive_time_unix, tz=timezone.utc)

        sender = packet.get("fromId", "")

        # Filter by monitored nodes if the list is not empty
        if MONITORED_NODES and sender not in MONITORED_NODES:
            return

        decoded = packet.get("decoded", {})
        portnum = decoded.get("portnum", "")

        # We only care about telemetry packets
        if portnum != "TELEMETRY_APP":
            return

        # Extract the packet's sent timestamp (Unix epoch)
        # Meshtastic packets include 'rxTime' (set by the receiving radio)
        # and the telemetry data itself may include a 'time' field.
        # The top-level 'rxTime' is the time the local radio received it,
        # while decoded.telemetry.time is the sender's timestamp.
        # We prefer the telemetry time as it reflects when the sender created the packet.
        telemetry = decoded.get("telemetry", {})
        packet_time_unix = telemetry.get("time", None)

        # Fallback: use the top-level packet 'rxTime' if telemetry has no time
        if packet_time_unix is None:
            packet_time_unix = packet.get("rxTime", None)

        if packet_time_unix is None:
            print(f"[WARN] No timestamp found in packet from {sender}, skipping.")
            return

        packet_dt = datetime.fromtimestamp(packet_time_unix, tz=timezone.utc)

        # Compute transmission time (receive time - packet sent time)
        transmission_time = receive_time_unix - packet_time_unix

        # Format timestamps for CSV / display
        packet_ts_str = packet_dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        receive_ts_str = receive_dt.strftime("%Y-%m-%d %H:%M:%S UTC")

        row = [
            sender,
            packet_ts_str,
            receive_ts_str,
            round(transmission_time, 3),
        ]

        with open(CSV_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(row)

        print(
            f"[LOG] {sender} | Sent: {packet_ts_str} | "
            f"Received: {receive_ts_str} | "
            f"Transmission time: {transmission_time:.3f}s"
        )

    except Exception as e:
        print(f"[ERROR] Failed to process packet: {e}")


def main():
    print("=" * 60)
    print("  Meshtastic Transmission Time Logger")
    print("=" * 60)

    if MONITORED_NODES:
        print(f"[INFO] Monitoring nodes: {', '.join(MONITORED_NODES)}")
    else:
        print("[INFO] Monitoring ALL nodes (no filter set)")

    print(f"[INFO] Logging to: {CSV_FILE}")

    init_csv(CSV_FILE)

    # Subscribe to all received packets
    pub.subscribe(on_receive, "meshtastic.receive")

    print("[INFO] Connecting to Meshtastic device...")
    try:
        if SERIAL_DEVICE:
            interface = meshtastic.serial_interface.SerialInterface(SERIAL_DEVICE)
        else:
            interface = meshtastic.serial_interface.SerialInterface()
    except Exception as e:
        print(f"[FATAL] Could not connect to Meshtastic device: {e}")
        print("        Make sure the device is plugged in and accessible.")
        print("        You may need to specify SERIAL_DEVICE in the script.")
        return

    print("[INFO] Connected. Listening for telemetry packets...")
    print("[INFO] Press Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down...")
    finally:
        interface.close()
        print("[INFO] Done.")


if __name__ == "__main__":
    main()
