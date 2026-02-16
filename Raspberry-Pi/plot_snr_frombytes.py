import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

CSV_FILE = "meshtastic_rx.csv"

df = pd.read_csv(CSV_FILE)

df["payload_bytes"] = pd.to_numeric(df["payload_bytes"])
df["snr_db"] = pd.to_numeric(df["snr_db"])

x = df["payload_bytes"]
y = df["snr_db"]

mean_df = df.groupby("payload_bytes")["snr_db"].mean().reset_index()

coef = np.polyfit(x, y, 1)
poly = np.poly1d(coef)

plt.figure()

plt.scatter(x, y, alpha=0.2)
plt.plot(mean_df["payload_bytes"],
         mean_df["snr_db"],
         linewidth=3)

x_line = np.linspace(x.min(), x.max(), 200)
plt.plot(x_line, poly(x_line), linestyle="--")

plt.xlabel("Packet size (bytes)")
plt.ylabel("SNR (dB)")
plt.title("Packet size vs SNR")
plt.grid(True)
plt.show()

print("SNR trend (dB per byte):", coef[0])
