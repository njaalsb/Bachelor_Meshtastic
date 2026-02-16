import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

CSV_FILE = "meshtastic_rx.csv"

df = pd.read_csv(CSV_FILE)

# Konverter til tall (selv om de allerede er det)
df["payload_bytes"] = pd.to_numeric(df["payload_bytes"])
df["rssi_dbm"] = pd.to_numeric(df["rssi_dbm"])

x = df["payload_bytes"]
y = df["rssi_dbm"]

# Gjennomsnitt per packet-størrelse
mean_df = df.groupby("payload_bytes")["rssi_dbm"].mean().reset_index()

# Lineær regresjon
coef = np.polyfit(x, y, 1)
poly = np.poly1d(coef)

plt.figure()

# Alle datapunkter (svake)
plt.scatter(x, y, alpha=0.2)

# Gjennomsnittslinje
plt.plot(mean_df["payload_bytes"],
         mean_df["rssi_dbm"],
         linewidth=3)

# Trendlinje
x_line = np.linspace(x.min(), x.max(), 200)
plt.plot(x_line, poly(x_line), linestyle="--")

plt.xlabel("Packet size (bytes)")
plt.ylabel("RSSI (dBm)")
plt.title("Packet size vs RSSI")
plt.grid(True)
plt.show()

print("RSSI trend (dBm per byte):", coef[0])
