#!/usr/bin/env python3
import os, random, csv, subprocess, sys

DEVICES = ["tdeck", "sensecap", "heltec", "lilygo"]
OUT_DIR = "./demo_data"
os.makedirs(OUT_DIR, exist_ok=True)

# Simulating your specific scenarios
# (Mean SNR, Std Dev)
SNR_PROFILES = {
    # T-Deck sends best to SenseCap
    ("tdeck", "tdeck"):    (2.5, 1),
    ("tdeck", "sensecap"): (9.0, 1), # High SNR
    ("tdeck", "heltec"):   (4.0, 2),
    ("tdeck", "lilygo"):   (1.0, 2),
    
    # Heltec sends best to Heltec
    ("heltec", "heltec"):   (11.0, 1), # Very High SNR
    ("heltec", "tdeck"):    (3.0, 2),
    ("heltec", "sensecap"): (5.0, 1),
    ("heltec", "lilygo"):   (2.0, 3),

    # Other random samples
    ("sensecap", "sensecap"): (8.0, 1),
    ("sensecap", "tdeck"):    (4.0, 1),
    ("sensecap", "heltec"):   (6.0, 1),
    ("sensecap", "lilygo"):   (3.0, 2),
    
    ("lilygo", "lilygo"):   (7.0, 1),
    ("lilygo", "tdeck"):    (-2.0, 2),
    ("lilygo", "sensecap"): (4.0, 1),
    ("lilygo", "heltec"):   (5.0, 1),
}

print(f"Generating 16 CSV files in {OUT_DIR}...")
for tx in DEVICES:
    for rx in DEVICES:
        fname = os.path.join(OUT_DIR, f"tx_{tx}_rx_{rx}.csv")
        mean, std = SNR_PROFILES.get((tx, rx), (0, 3))
        n_msgs = random.randint(20, 40)
        
        with open(fname, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["timestamp", "snr"])
            writer.writeheader()
            for _ in range(n_msgs):
                writer.writerow({
                    "timestamp": "2026-05-01 12:00:00",
                    "snr": round(random.gauss(mean, std), 2)
                })

print("\nRunning Analysis...")
subprocess.run([sys.executable, "matrix_plot.py", "--csv-dir", OUT_DIR], check=True)