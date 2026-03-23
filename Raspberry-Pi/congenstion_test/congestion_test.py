#!/usr/bin/env python3
"""
Meshtastic Telemetry Logger

Listens for incoming Meshtastic messages via a serial-connected radio,
filters for Telemetry App packets from specified node IDs, and logs
timing information to a CSV file.

Requirements:
    pip install meshtastic

Usage:
    python meshtastic_telemetry_logger.py

Configure the settings in the CONFIGURATION section below.
"""

import csv
import os
import sys
import time
from datetime import datetime, timezone

try:
    import meshtastic
    import meshtastic.serial_interface
    from pubsub import pub
except ImportError:
    print("ERROR: Required packages not installed.")
    print("Install with:  pip install meshtastic")
    sys.exit(1)


# =============================================================================
# CONFIGURATION — Edit these values to suit your setup
# =============================================================================

# Serial device path to the Meshtastic radio.
# Common values:
#   Raspberry Pi:  "/dev/ttyUSB0" or "/dev/ttyACM0"
#   macOS:         "/dev/cu.usbmodem*" or "/dev/cu.SLAB_USBtoUART"
#   Windows:       "COM3"
SERIAL_DEVICE = "/dev/ttyACM1"

# CSV output file name (created in the working directory).
CSV_FILENAME = "congestion_log_v1.csv"

# Node IDs to log. Use the hex node ID strings (with or without '!' prefix).
# Examples: ["!a1b2c3d4", "!deadbeef"]
# Set to an empty list [] to log ALL nodes.
TRACKED_NODE_IDS = [
	#"!6ba526c6",
	#""
]

# =============================================================================
# END OF CONFIGURATION
# =============================================================================

CSV_HEADER = [
    "node_id",
    "message_sent_utc",
    "message_received_utc",
    "latency_seconds",
]


def normalize_node_id(node_id: str) -> str:
    """Ensure node ID has the '!' prefix and is lowercase."""
    node_id = str(node_id).strip().lower()
    if not node_id.startswith("!"):
        node_id = "!" + node_id
    return node_id


def init_csv(filepath: str) -> None:
    """Create the CSV file with a header row if it doesn't already exist."""
    if not os.path.isfile(filepath):
        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADER)
        print(f"[init] Created new CSV file: {filepath}")
    else:
        print(f"[init] Appending to existing CSV file: {filepath}")


def append_row(filepath: str, row: list) -> None:
    """Append a single data row to the CSV file."""
    with open(filepath, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(row)


def on_receive(packet, interface) -> None:  # noqa: ARG001
    """Callback invoked for every received Meshtastic packet."""

    try:
        # --- Filter: only Telemetry App packets ---
        port_num = packet.get("decoded", {}).get("portnum", "")
        if port_num != "TELEMETRY_APP":
            return

        # --- Extract sender node ID ---
        from_id = packet.get("fromId", "")
        node_id = normalize_node_id(from_id)

        # --- Filter: only tracked nodes (if list is non-empty) ---
        if TRACKED_NODE_IDS:
            tracked = [normalize_node_id(n) for n in TRACKED_NODE_IDS]
            if node_id not in tracked:
                return

        # --- Extract the device metrics timestamp ---
        # The 'rxTime' or the telemetry 'time' field carries the Unix
        # timestamp set by the sending node when the packet was created.
        telemetry = packet.get("decoded", {}).get("telemetry", {})
        sent_timestamp = telemetry.get("time", None)

        # Fallback: some firmware versions put the send time in rxTime
        if sent_timestamp is None:
            sent_timestamp = packet.get("rxTime", None)

        if sent_timestamp is None:
            print(f"[warn] Telemetry packet from {node_id} has no timestamp — skipping.")
            return

        # --- Compute times ---
        sent_dt = datetime.fromtimestamp(sent_timestamp, tz=timezone.utc)
        received_dt = datetime.now(tz=timezone.utc)
        latency = (received_dt - sent_dt).total_seconds()

        sent_str = sent_dt.strftime("%Y-%m-%d %H:%M:%S")
        received_str = received_dt.strftime("%Y-%m-%d %H:%M:%S")

        # --- Log to CSV ---
        row = [node_id, sent_str, received_str, f"{latency:.2f}"]
        append_row(CSV_FILENAME, row)

        print(
            f"[log] Node {node_id}  |  sent {sent_str}  |  "
            f"received {received_str}  |  latency {latency:.2f}s"
        )

    except Exception as exc:
        print(f"[error] Failed to process packet: {exc}")


def main() -> None:
    print("=" * 60)
    print("  Meshtastic Telemetry Logger")
    print("=" * 60)
    print(f"  Serial device : {SERIAL_DEVICE}")
    print(f"  CSV file      : {CSV_FILENAME}")
    if TRACKED_NODE_IDS:
        print(f"  Tracking nodes: {', '.join(TRACKED_NODE_IDS)}")
    else:
        print("  Tracking nodes: ALL")
    print("=" * 60)

    init_csv(CSV_FILENAME)

    # Subscribe to all received packets.
    pub.subscribe(on_receive, "meshtastic.receive")

    print(f"[init] Connecting to Meshtastic radio on {SERIAL_DEVICE} ...")
    try:
        interface = meshtastic.serial_interface.SerialInterface(devPath=SERIAL_DEVICE)
    except Exception as exc:
        print(f"[fatal] Could not open serial device: {exc}")
        sys.exit(1)

    print("[ready] Listening for telemetry packets. Press Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[exit] Shutting down ...")
        interface.close()
        print("[exit] Done.")


if __name__ == "__main__":
    main()
