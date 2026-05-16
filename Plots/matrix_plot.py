#!/usr/bin/env python3
import os, csv, argparse, re
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors


def discover_devices(csv_dir):
    """Auto-discover TX and RX devices separately from filenames like tx_DEVICE1_rx_DEVICE2.csv"""
    pattern = re.compile(r"^u_tx_(.+)_rx_(.+)\.csv$")
    tx_devices = set()
    rx_devices = set()
    for fname in os.listdir(csv_dir):
        m = pattern.match(fname)
        if m:
            tx_devices.add(m.group(1))
            rx_devices.add(m.group(2))
    # Sort alphabetically but put 'solar' last
    sort_key = lambda d: (d == "solar", d)
    return sorted(tx_devices, key=sort_key), sorted(rx_devices, key=sort_key)


def device_to_label(device):
    """Convert device name to display label."""
    if device == "t3s3":
        return "T3S3 (d)"
    if device == "t3s3m":
        return "T3S3 (m)"
    if device == "solar":
        return "Solar"
    return device.replace("_", " ").title()


def find_col(headers, hint):
    lmap = {h.lower().strip(): h for h in headers}
    if hint.lower() in lmap:
        return lmap[hint.lower()]
    return None


def read_avg(path, col_hint):
    if not os.path.exists(path):
        return None, 0
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            col = find_col(reader.fieldnames or [], col_hint)
            if not col:
                return None, 0
            vals = []
            for row in reader:
                raw = row.get(col, "").strip()
                if raw:
                    try:
                        vals.append(float(raw))
                    except ValueError:
                        pass
        return (sum(vals) / len(vals) if vals else None), len(vals)
    except Exception as e:
        print(f"  Warning: could not read {path}: {e}")
        return None, 0


def build_matrix(csv_dir, col_hint, tx_devices, rx_devices):
    data = np.full((len(tx_devices), len(rx_devices)), np.nan)
    msgs = np.zeros((len(tx_devices), len(rx_devices)), dtype=int)

    for i, tx in enumerate(tx_devices):
        for j, rx in enumerate(rx_devices):
            fp = os.path.join(csv_dir, f"u_tx_{tx}_rx_{rx}.csv")
            avg, count = read_avg(fp, col_hint)
            if avg is not None:
                data[i, j] = avg
                msgs[i, j] = count
    return data, msgs


def plot_matrix(data, msgs, tx_devices, rx_devices, out_path, col_hint):
    n_tx = len(tx_devices)
    n_rx = len(rx_devices)
    tx_labels = [device_to_label(d) for d in tx_devices]
    rx_labels = [device_to_label(d) for d in rx_devices]

    cmap = mcolors.LinearSegmentedColormap.from_list(
        "data_map",
        ["#c00000", "#c06000", "#c0c000", "#80c000", "#00c000"],
        N=256,
    )

    is_rssi = col_hint.lower() == "rssi"
    vmin, vmax = (-128, -90) if is_rssi else (-20, 10)
    unit = "dBm" if is_rssi else "dB"
    colorbar_label = f"Avg RSSI ({unit})" if is_rssi else f"Avg SNR ({unit})"
    title = "Meshtastic RSSI Matrix: All Combinations" if is_rssi else "Meshtastic SNR Matrix: All Combinations"

    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)

    fig, ax = plt.subplots(figsize=(max(6, n_rx * 1.8), max(5, n_tx * 1.6)))
    fig.patch.set_facecolor("#f7f9fc")

    for i in range(n_tx):
        for j in range(n_rx):
            val = data[i, j]
            color = cmap(norm(val)) if not np.isnan(val) else "#e8edf5"
            ax.add_patch(plt.Rectangle([j - 0.5, i - 0.5], 1, 1, color=color))

            if not np.isnan(val):
                ax.text(
                    j, i, f"{val:+.1f} {unit}",
                    ha="center", va="center",
                    color="black", weight="bold", fontsize=10,
                )
            else:
                ax.text(j, i, "N/A", ha="center", va="center", color="#9aaccc")

    ax.set_xticks(range(n_rx))
    ax.set_yticks(range(n_tx))
    ax.xaxis.set_label_position("top")
    ax.xaxis.tick_top()
    ax.set_xticklabels(rx_labels, rotation=30, ha="left", fontweight="bold")
    ax.set_yticklabels(tx_labels, fontweight="bold")
    ax.set_xlabel("Receiver (RX)", fontsize=12, fontweight="bold")
    ax.set_ylabel("Transmitter (TX)", fontsize=12, fontweight="bold")
    ax.set_xlim(-0.5, n_rx - 0.5)
    ax.set_ylim(n_tx - 0.5, -0.5)

    plt.title(title, pad=20, fontweight="bold", fontsize=14)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    plt.colorbar(sm, ax=ax, label=colorbar_label)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    print(f"✓ Saved plot to {out_path}")
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv-dir", default="./data",
                        help="Directory containing tx_X_rx_Y.csv files")
    parser.add_argument("--col", default=None,
                        help="Column to plot, e.g. 'rssi' or 'rx snr'. "
                             "If omitted, plots SNR then RSSI sequentially.")
    parser.add_argument("--out", default=None,
                        help="Output image path. If omitted, defaults to "
                             "'matrix_snr.png' / 'matrix_rssi.png' for sequential mode, "
                             "or 'matrix.png' for single-col mode.")
    args = parser.parse_args()

    tx_devices, rx_devices = discover_devices(args.csv_dir)
    if not tx_devices:
        print(f"No tx_*_rx_*.csv files found in '{args.csv_dir}'. Check --csv-dir.")
        raise SystemExit(1)

    print(f"TX devices: {tx_devices}")
    print(f"RX devices: {rx_devices}")

    if args.col is not None:
        # Single-metric mode (original behaviour)
        out = args.out or "matrix.png"
        data, msg_counts = build_matrix(args.csv_dir, args.col, tx_devices, rx_devices)
        plot_matrix(data, msg_counts, tx_devices, rx_devices, out, args.col)
    else:
        # Sequential mode: SNR first, then RSSI after the window is closed
        for col_hint, default_out in [("rx snr", "matrix_snr.png"), ("rssi", "matrix_rssi.png")]:
            out = args.out or default_out
            print(f"\nPlotting {col_hint.upper()} → {out}")
            data, msg_counts = build_matrix(args.csv_dir, col_hint, tx_devices, rx_devices)
            plot_matrix(data, msg_counts, tx_devices, rx_devices, out, col_hint)