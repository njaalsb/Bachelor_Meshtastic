import pandas as pd
import matplotlib.pyplot as plt

CSV_FILE = "meshtastic_rx.csv"

# Les CSV
df = pd.read_csv(CSV_FILE)

# Fjern rader uten RSSI eller payload
df = df.dropna(subset=["payload_bytes", "rssi_dbm"])

# Sørg for riktig datatype
df["payload_bytes"] = pd.to_numeric(df["payload_bytes"], errors="coerce")
df["rssi_dbm"] = pd.to_numeric(df["rssi_dbm"], errors="coerce")

# Fjern NaN etter konvertering
df = df.dropna(subset=["payload_bytes", "rssi_dbm"])

plt.figure()
plt.scatter(df["payload_bytes"], df["rssi_dbm"])
plt.xlabel("Packet size (bytes)")
plt.ylabel("RSSI (dBm)")
plt.title("Packet size vs RSSI")
plt.grid(True)
plt.show()
