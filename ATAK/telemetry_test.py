# Overforing av telemetri fra 72da -> a0f9 (preset ShortFast)


"""
Send dummy frequency readings to the ATAK Meshtastic plugin for testing.

Packet format (6 bytes, port 257 / ATAK_FORWARDER):
  byte 0   : 0x03  (TRANSFER_TYPE_SENSOR)
  byte 1   : 0x01  (sensor type ID — frequency)
  bytes 2-5: float32 little-endian, frequency in Hz

Usage:
  python telemetry_test.py            # auto-detect USB port
  python telemetry_test.py /dev/ttyUSB0
"""

import sys
import struct
import time
import meshtastic
import meshtastic.serial_interface

SENSOR_TYPE_FREQUENCY = 0x01
ATAK_FORWARDER_PORT = 257

# Dummy frequencies to cycle through
DUMMY_FREQUENCIES_HZ = [
    433_920_000.0,   # 433.920 MHz
    868_000_000.0,   # 868.000 MHz
    915_000_000.0,   # 915.000 MHz
    2_400_000_000.0, # 2.400 GHz
    144_800_000.0,   # 144.800 MHz (2m amateur)
]


def build_packet(frequency_hz: float) -> bytes:
    return bytes([0x03, SENSOR_TYPE_FREQUENCY]) + struct.pack('<f', frequency_hz)


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else None

    print(f"Connecting to Meshtastic device{' on ' + port if port else ' (auto-detect)'}...")
    iface = meshtastic.serial_interface.SerialInterface(devPath=port)
    print("Connected.")

    try:
        for i, freq_hz in enumerate(DUMMY_FREQUENCIES_HZ):
            payload = build_packet(freq_hz)
            freq_mhz = freq_hz / 1e6
            print(f"[{i+1}/{len(DUMMY_FREQUENCIES_HZ)}] Sending {freq_mhz:.3f} MHz  ({payload.hex()})")
            iface.sendData(payload, portNum=ATAK_FORWARDER_PORT, wantAck=False)
            time.sleep(3)

        print("Done. All dummy packets sent.")
    finally:
        iface.close()


if __name__ == "__main__":
    main()
