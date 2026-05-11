#!/usr/bin/env python3
import sys
import meshtastic.serial_interface
import time
import struct
import threading

sdr_enabled = True 
sdr_freq = 869525000
sdr_gain = 'auto'
sdr_interval = 10
sdr_threshold = -20


def sdr_listen(iface):
    try:
        import numpy as np
        from rtlsdr import RtlSdr
    except ImportError:
        print("[sdr] mangler rtlsdr eller numpy, SDR deaktivert", flush=True)
        return

    sdr = RtlSdr()
    sdr.sample_rate = 2.048e6
    sdr.center_freq = sdr_freq
    sdr.gain        = sdr_gain

    print("[sdr] klar, lytter på {:.3f} MHz".format(sdr_freq / 1e6), flush=True)

    peak_freq  = None
    peak_power = -999.0
    deadline   = time.time() + sdr_interval

    while True:
        samples = sdr.read_samples(256 * 1024)

        psd    = np.abs(np.fft.fftshift(np.fft.fft(samples))) ** 2
        psd_db = 10 * np.log10(psd + 1e-10)
        freqs  = np.fft.fftshift(np.fft.fftfreq(len(samples), 1 / sdr.sample_rate))


        psd_db[np.abs(freqs) < 10_000] = -999.0

  
        idx = int(np.argmax(psd_db))
        if psd_db[idx] > peak_power:
            peak_power = float(psd_db[idx])
            peak_freq  = float(sdr.center_freq + freqs[idx])

        if time.time() >= deadline:
            if peak_freq is not None and peak_power > sdr_threshold:
                print("[sdr] peak {:.4f} MHz ({:.1f} dB)".format(peak_freq / 1e6, peak_power), flush=True)


                payload = bytes([0x03, 0x01]) + struct.pack('<f', peak_freq)
                try:
                    iface.sendData(payload, portNum=257, wantAck=False)
                except Exception as e:
                    print("[sdr] send feil: {}".format(e), flush=True)

            peak_freq  = None
            peak_power = -999.0
            deadline   = time.time() + sdr_interval

def main():
    try:
        iface1 = meshtastic.serial_interface.SerialInterface(devPath='/dev/ttyACM0')
        iface2 = meshtastic.serial_interface.SerialInterface(devPath='/dev/ttyACM1')
    except Exception as e:
        print("[bridge] feil ved åpning: {}".format(e), flush=True)
        sys.exit(1)

    print("[bridge] klar", flush=True)


    if sdr_enabled:
        t = threading.Thread(target=sdr_listen, args=(iface2,), daemon=True)
        t.start()

  
    try:
        for line in sys.stdin:
            msg = line.rstrip("\n")
            if not msg:
                continue
            try:
                if msg.startswith("DATA:"):
                    _, port_str, hex_str = msg.split(":", 2)
                    payload = bytes.fromhex(hex_str)
                    iface1.sendData(payload, portNum=int(port_str), wantAck=False)
                    print("[bridge] tx port={} bytes={}".format(port_str, len(payload)), flush=True)
                else:
                    iface1.sendText(msg)
                    print("[bridge] tx tekst: {}".format(msg[:40]), flush=True)
            except Exception as e:
                print("[bridge] send feil: {}".format(e), flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        iface1.close()
        print("[bridge] lukket", flush=True)


if __name__ == "__main__":
    main()