# Telemetry transfer ATAK test:

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
import numpy as np
from rtlsdr import RtlSdr



SENSOR_TYPE_FREQUENCY = 0x01
ATAK_FORWARDER_PORT = 257

# SDR delen
sdr = RtlSdr()
sdr.sample_rate = 2.048e6    
sdr.center_freq = 868.0e6    
sdr.gain = 'auto'

def frequency_readings():
    samples = sdr.read_samples(256*1024)

    #Fjern DC-komponent
    samples = samples - np.mean(samples)

    #FFT av samples
    spectrum = np.fft.fftshift(np.fft.fft(samples))
    power = np.abs(spectrum)


    # Fjerne dc-komponent og nærliggende frekvenser sånn at testen ikke alltid finner 868.000 MHz som toppfrekvens
    mid = len(power)//2
    power[mid-20:mid+20] = 0

    # Finn frekvensen med høyest effekt
    peak_index = np.argmax(power)

    # Finn offset fra senterfrekvensen
    freq_offset = (peak_index - len(power) // 2) * (sdr.sample_rate / len(power))
    
    # Finn den faktiske frekvensen
    return sdr.center_freq + freq_offset
    

def build_packet(frequency_hz: float) -> bytes:
    return bytes([0x03, SENSOR_TYPE_FREQUENCY]) + struct.pack('<f', frequency_hz)


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else None

    print(f"Connecting to Meshtastic device{' on ' + port if port else ' (auto-detect)'}...")
    iface = meshtastic.serial_interface.SerialInterface(devPath=port)
    print("Connected.")

    try:
        i = 0
        while True:
            i += 1

            freq_hz = frequency_readings()
            payload = build_packet(freq_hz)

            freq_mhz = freq_hz / 1e6

            print(f"[{i}] Sending {freq_mhz:.3f} MHz ")

            iface.sendData(payload, portNum=ATAK_FORWARDER_PORT, wantAck=False)

            time.sleep(5)

    finally:
        iface.close()
        sdr.close()


if __name__ == "__main__":
    main()

