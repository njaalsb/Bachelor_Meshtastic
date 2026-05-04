#!/usr/bin/env python3
import os, csv, argparse, re
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors


def discover_devices(csv_dir):
    """Auto-discover device names from filenames like tx_DEVICE1_rx_DEVICE2.csv"""
    pattern = re.compile(r"^tx_(.+)_rx_(.+)\.csv$")
    devices = set()
    for fname in os.listdir(csv_dir):
        m = pattern.match(fname)
        if m:
            devices.add(m.group(1))
            devices.add(m.group(2))
    return sorted(devices)


def find_snr_col(headers, hint):
    lmap = {h.lower().strip(): h for h in headers}
    for c in [hint.lower(), "rx snr", "rssi_snr", "lora_snr", "snr"]:
        if c in lmap:
            return lmap[c]
    return None


def read_avg_snr(path, snr_hint):
    if not os.path.exists(path):
        return None, 0
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            col = find_snr_col(reader.fieldnames or [], snr_hint)
            if not col:
                return None, 0
            vals = []
            for row in reader:
                raw = row.get(col, "").strip()
                if raw:
                    try:
                        vals.append(float(raw))
                    except ValueError:
                        pass  # skip malformed values
        return (sum(vals) / len(vals) if vals else None), len(vals)
    except Exception as e:
        print(f"  Warning: could not read {path}: {e}")
        return None, 0


def build_matrix(csv_dir, snr_col, devices):
    n = len(devices)
    snr = np.full((n, n), np.nan)
    msgs = np.zeros((n, n), dtype=int)

    for i, tx in enumerate(devices):
        for j, rx in enumerate(devices):
            fp = os.path.join(csv_dir, f"tx_{tx}_rx_{rx}.csv")
            avg, count = read_avg_snr(fp, snr_col)
            if avg is not None:
                snr[i, j] = avg
                msgs[i, j] = count
    return snr, msgs


def plot_matrix(snr, msgs, devices, out_path):
    n = len(devices)
    # Title-case device names for labels
    labels = [d.replace("_", " ").title() for d in devices]

    cmap = mcolors.LinearSegmentedColormap.from_list(
        "snr_map",
        ["#c00000", "#c06000", "#c0c000", "#80c000", "#00c000"],
        N=256,
    )

    valid = snr[~np.isnan(snr)]
    vmin, vmax = (valid.min(), valid.max()) if len(valid) else (-10, 10)
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)

    fig, ax = plt.subplots(figsize=(max(6, n * 1.8), max(5, n * 1.6)))
    fig.patch.set_facecolor("#f7f9fc")

    for i in range(n):
        for j in range(n):
            val = snr[i, j]
            color = cmap(norm(val)) if not np.isnan(val) else "#e8edf5"
            ax.add_patch(plt.Rectangle([j - 0.5, i - 0.5], 1, 1, color=color))

            if not np.isnan(val):
                ax.text(
                    j, i, f"{val:+.1f} dB\nn={msgs[i,j]}",
                    ha="center", va="center",
                    color="black", weight="bold", fontsize=10,
                )
            else:
                ax.text(j, i, "N/A", ha="center", va="center", color="#9aaccc")

    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.xaxis.set_label_position("top")
    ax.xaxis.tick_top()
    ax.set_xticklabels(labels, rotation=30, ha="left", fontweight="bold")
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
    parser.add_argument("--csv-dir", default="./data",
                        help="Directory containing tx_X_rx_Y.csv files")
    parser.add_argument("--snr-col", default="rx snr",
                        help="SNR column name hint (default: 'rx snr')")
    parser.add_argument("--out", default="snr_matrix.png",
                        help="Output image path")
    args = parser.parse_args()

    devices = discover_devices(args.csv_dir)
    if not devices:
        print(f"No tx_*_rx_*.csv files found in '{args.csv_dir}'. Check --csv-dir.")
        raise SystemExit(1)

    print(f"Discovered devices: {devices}")
    snr_data, msg_counts = build_matrix(args.csv_dir, args.snr_col, devices)
    plot_matrix(snr_data, msg_counts, devices, args.out)