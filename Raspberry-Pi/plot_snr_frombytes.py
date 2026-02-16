import pandas as pd
import matplotlib.pyplot as plt

CSV_FILE = "meshtastic_rx.csv"

# Les CSV
df = pd.read_csv(CSV_FILE)

# Fjern rader uten SNR eller payload
df = df.dropna(subset=["payload_bytes", "snr_db"])

df["payload_bytes"] = pd.to_numeric(df["payload_bytes"], errors="coerce")
df["snr_db"] = pd.to_numeric(df["snr_db"], errors="coerce")

df = df.dropna(subset=["payload_bytes", "snr_db"])

plt.figure()
plt.scatter(df["payload_bytes"], df["snr_db"])
plt.xlabel("Packet size (bytes)")
plt.ylabel("SNR (dB)")
plt.title("Packet size vs SNR")
plt.grid(True)
plt.show()
