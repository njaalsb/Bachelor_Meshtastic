#!/usr/bin/env python3
"""
Meshtastic Battery Level Logger

Listens for incoming packets on a Meshtastic radio and logs battery
telemetry data (battery level, voltage, uptime) to a CSV file.

Requirements:
    pip install meshtastic

Usage:
    python3 meshtastic_battery_logger.py
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
    # "!8511ed74"  #heltec
    # "!08dc7aee"   #Sensecap
    # "!ba582d3c", #Tdeck
      "!27979824", #solar
]

# Path to the output CSV file
CSV_FILE = "battery_log_Solar_2min.csv"

# Serial device path (set to None for auto-detect)
SERIAL_DEVICE = "/dev/ttyACM0" #None  # e.g., "/dev/ttyUSB0" or "/dev/ttyACM0"

# =============================================================================
# END OF CONFIGURATION
# =============================================================================

CSV_HEADERS = [
    "timestamp",
    "node_id",
    "node_long_name",
    "node_short_name",
    "battery_level_pct",
    "voltage",
    "uptime_seconds",
    "uptime_human",
]


def format_uptime(seconds: int) -> str:
    """Convert seconds into a human-readable duration string."""
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


def init_csv(filepath: str) -> None:
    """Create the CSV file with headers if it doesn't already exist."""
    if not os.path.exists(filepath):
        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)
        print(f"[INFO] Created new CSV file: {filepath}")
    else:
        print(f"[INFO] Appending to existing CSV file: {filepath}")


def get_node_info(interface, node_id: str) -> dict:
    """Look up long name and short name for a node from the node DB."""
    info = {"long_name": "unknown", "short_name": "unknown"}
    if interface.nodes:
        node = interface.nodes.get(node_id)
        if node and "user" in node:
            info["long_name"] = node["user"].get("longName", "unknown")
            info["short_name"] = node["user"].get("shortName", "unknown")
    return info


def on_receive(packet, interface):
    """Callback for every received packet. Filters for device telemetry."""
    try:
        sender = packet.get("fromId", "")

        # Filter by monitored nodes if the list is not empty
        if MONITORED_NODES and sender not in MONITORED_NODES:
            return

        decoded = packet.get("decoded", {})
        portnum = decoded.get("portnum", "")

        # We only care about telemetry packets
        if portnum != "TELEMETRY_APP":
            return

        telemetry = decoded.get("telemetry", {})
        device_metrics = telemetry.get("deviceMetrics", {})

        # Only log if there is battery data present
        if "batteryLevel" not in device_metrics:
            return

        battery_level = device_metrics.get("batteryLevel", None)
        voltage = device_metrics.get("voltage", None)
        uptime_seconds = device_metrics.get("uptimeSeconds", 0)
        uptime_human = format_uptime(uptime_seconds)

        node_info = get_node_info(interface, sender)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        row = [
            timestamp,
            sender,
            node_info["long_name"],
            node_info["short_name"],
            battery_level,
            voltage,
            uptime_seconds,
            uptime_human,
        ]

        with open(CSV_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(row)

        print(
            f"[LOG] {timestamp} | {sender} ({node_info['short_name']}) | "
            f"Battery: {battery_level}% | Voltage: {voltage}V | "
            f"Uptime: {uptime_human}"
        )

    except Exception as e:
        print(f"[ERROR] Failed to process packet: {e}")


def main():
    print("=" * 60)
    print("  Meshtastic Battery Level Logger")
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

    print("[INFO] Connected. Listening for battery telemetry packets...")
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
