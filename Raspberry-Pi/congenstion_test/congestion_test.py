#!/usr/bin/env python3
"""
Meshtastic Telemetry Logger

Listens for incoming Meshtastic messages via a serial-connected radio,
filters for Telemetry App packets from specified node IDs, and logs
timing information to a CSV file.

Additionally, sends telemetry requests to tracked nodes every minute.

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
import threading
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
SERIAL_DEVICE = "/dev/ttyACM0"

# CSV output file name (created in the working directory).
CSV_FILENAME = "no_congestion.csv"

# Node IDs to log. Use the hex node ID strings (with or without '!' prefix).
# Examples: ["!a1b2c3d4", "!deadbeef"]
# Set to an empty list [] to log ALL nodes (but requests will only be sent
# to explicitly listed nodes).
TRACKED_NODE_IDS = [
    "!9eeff3a4"
    #"!6ba526c6",
    #""
]

# Interval in seconds between telemetry requests.
REQUEST_INTERVAL_SECONDS = 60

# =============================================================================
# END OF CONFIGURATION
# =============================================================================

CSV_HEADER = [
    "node_id",
    "message_sent_utc",
    "message_received_utc",
    "latency_seconds",
]

# Global reference to the interface (set in main)
_interface = None
_stop_event = threading.Event()


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


def request_telemetry_loop() -> None:
    """Background thread: sends telemetry requests to tracked nodes periodically."""
    global _interface

    while not _stop_event.is_set():
        if _interface is not None and TRACKED_NODE_IDS:
            for node_id in TRACKED_NODE_IDS:
                node_id = normalize_node_id(node_id)
                if not node_id or node_id == "!":
                    continue
                try:
                    # Convert node ID to integer (remove '!' prefix, parse hex)
                    node_num = int(node_id[1:], 16)
                    print(f"[request] Requesting telemetry from {node_id}")
                    _interface.sendTelemetry(destinationId=node_num, wantResponse=True)
                except Exception as exc:
                    print(f"[error] Failed to request telemetry from {node_id}: {exc}")

        # Wait for the interval, but check stop_event frequently for clean shutdown
        for _ in range(REQUEST_INTERVAL_SECONDS):
            if _stop_event.is_set():
                break
            time.sleep(1)


def main() -> None:
    global _interface

    print("=" * 60)
    print("  Meshtastic Telemetry Logger")
    print("=" * 60)
    print(f"  Serial device      : {SERIAL_DEVICE}")
    print(f"  CSV file           : {CSV_FILENAME}")
    print(f"  Request interval   : {REQUEST_INTERVAL_SECONDS}s")
    if TRACKED_NODE_IDS:
        print(f"  Tracking nodes     : {', '.join(TRACKED_NODE_IDS)}")
    else:
        print("  Tracking nodes     : ALL (no requests will be sent)")
    print("=" * 60)

    init_csv(CSV_FILENAME)

    # Subscribe to all received packets.
    pub.subscribe(on_receive, "meshtastic.receive")

    print(f"[init] Connecting to Meshtastic radio on {SERIAL_DEVICE} ...")
    try:
        _interface = meshtastic.serial_interface.SerialInterface(devPath=SERIAL_DEVICE)
    except Exception as exc:
        print(f"[fatal] Could not open serial device: {exc}")
        sys.exit(1)

    # Start the background thread for sending telemetry requests
    request_thread = threading.Thread(target=request_telemetry_loop, daemon=True)
    request_thread.start()
    print("[init] Started telemetry request thread.")

    print("[ready] Listening for telemetry packets. Press Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[exit] Shutting down ...")
        _stop_event.set()
        request_thread.join(timeout=5)
        _interface.close()
        print("[exit] Done.")


if __name__ == "__main__":
    main()
