#!/usr/bin/env python3
import os, csv, argparse
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# ── Configuration ────────────────────────────────────────────────────────────
DEVICES = ["tdeck", "sensecap", "heltec", "lilygo"]
LABELS  = {"tdeck": "T-Deck", "sensecap": "SenseCap",
           "heltec": "Heltec", "lilygo":  "Lilygo"}

def find_snr_col(headers, hint):
    lmap = {h.lower(): h for h in headers}
    for c in [hint.lower(), "snr", "rssi_snr", "lora_snr"]:
        if c in lmap: return lmap[c]
    return None

def read_avg_snr(path, snr_hint):
    if not os.path.exists(path):
        return None, 0
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            col = find_snr_col(reader.fieldnames or [], snr_hint)
            if not col: return None, 0
            vals = [float(row[col]) for row in reader if row.get(col)]
        return (sum(vals) / len(vals) if vals else None), len(vals)
    except Exception:
        return None, 0

def build_matrix(csv_dir, snr_col):
    n = len(DEVICES)
    snr = np.full((n, n), np.nan)
    msgs = np.zeros((n, n), dtype=int)
    
    for i, tx in enumerate(DEVICES):
        for j, rx in enumerate(DEVICES):
            # REMOVED: if tx == rx skip logic. 
            # We now process all pairs to find the best transmitter/receiver combos.
            fp = os.path.join(csv_dir, f"tx_{tx}_rx_{rx}.csv")
            avg, count = read_avg_snr(fp, snr_col)
            if avg is not None:
                snr[i, j] = avg
                msgs[i, j] = count
    return snr, msgs

def plot_matrix(snr, msgs, out_path):
    n = len(DEVICES)
    labels = [LABELS[d] for d in DEVICES]
    cmap = mcolors.LinearSegmentedColormap.from_list("snr_map", 
        ["#f0f4ff", "#c6d4f0", "#5a82c8", "#1a3a7a", "#0b1f4a"], N=256)

    valid = snr[~np.isnan(snr)]
    vmin, vmax = (valid.min(), valid.max()) if len(valid) else (-10, 10)
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)

    fig, ax = plt.subplots(figsize=(8, 7))
    fig.patch.set_facecolor("#f7f9fc")

    for i in range(n):
        for j in range(n):
            val = snr[i, j]
            # If data is missing, use a light grey background
            color = cmap(norm(val)) if not np.isnan(val) else "#e8edf5"
            ax.add_patch(plt.Rectangle([j-0.5, i-0.5], 1, 1, color=color))

            if not np.isnan(val):
                brightness = 0.299*color[0] + 0.587*color[1] + 0.114*color[2]
                txt_c = "white" if brightness < 0.5 else "#1a2a4a"
                ax.text(j, i, f"{val:+.1f} dB\nn={msgs[i,j]}", 
                        ha="center", va="center", color=txt_c, weight="bold", fontsize=10)
            else:
                ax.text(j, i, "N/A", ha="center", va="center", color="#9aaccc")

    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(labels, rotation=30, ha="right", fontweight="bold")
    ax.set_yticklabels(labels, fontweight="bold")
    ax.set_xlabel("Receiver (RX)", fontsize=12, fontweight="bold")
    ax.set_ylabel("Transmitter (TX)", fontsize=12, fontweight="bold")
    ax.set_xlim(-0.5, n - 0.5)
    ax.set_ylim(n - 0.5, -0.5)
    
    plt.title("Meshtastic SNR Matrix: All Combinations", pad=20, fontweight="bold", fontsize=14)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    plt.colorbar(sm, ax=ax, label="Avg SNR (dB)")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    print(f"✓ Saved plot to {out_path}")
    plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv-dir", default="./data")
    parser.add_argument("--snr-col", default="snr")
    parser.add_argument("--out", default="snr_matrix.png")
    args = parser.parse_args()
    
    snr_data, msg_counts = build_matrix(args.csv_dir, args.snr_col)
    plot_matrix(snr_data, msg_counts, args.out)