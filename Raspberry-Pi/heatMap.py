#!/usr/bin/env python3
"""
Meshtastic map with per-node RSSI/SNR annotations.

Keeps the same "map look" as before:
- center at base station (63.4184304, 10.4014815)
- plot GPS points per node in different colors
- draw lines from base to each point

Adds text labels near each node's points showing RSSI and SNR.
Default behavior:
- annotate ONLY the latest point per node (cleaner)
Optional:
- --annotate all  (will label every point, can get messy)

Usage:
  python map_with_metrics.py --csv meshtastic_log.csv --outdir plots --show
  python map_with_metrics.py --csv meshtastic_log.csv --outdir plots
  python map_with_metrics.py --csv meshtastic_log.csv --annotate all
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

BASE_LAT = 63.4184304
BASE_LON = 10.4014815


@dataclass(frozen=True)
class NodeKey:
    from_id: str
    from_name: str

    @property
    def label(self) -> str:
        # Prefer name if it is different than id and not NaN
        if self.from_name and self.from_name.lower() != "nan" and str(self.from_name) != str(self.from_id):
            return f"{self.from_name} ({self.from_id})"
        return str(self.from_id)


def build_color_map(keys, cmap_name="tab20") -> Dict[NodeKey, Tuple[float, float, float, float]]:
    cmap = plt.get_cmap(cmap_name)
    keys = list(keys)
    return {k: cmap(i % cmap.N) for i, k in enumerate(keys)}


def read_and_clean(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    required = ["timestamp", "from_id", "from_name", "rssi_dbm", "snr_db", "latitude", "longitude"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"CSV is missing columns: {missing}\nFound columns: {list(df.columns)}")

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp")

    df["from_id"] = df["from_id"].astype(str)
    df["from_name"] = df["from_name"].astype(str)

    for col in ["rssi_dbm", "snr_db", "latitude", "longitude"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # keep only rows with GPS
    df = df.dropna(subset=["latitude", "longitude"])

    return df


def plot_map_with_metrics(
    df: pd.DataFrame,
    color_map: Dict[NodeKey, Tuple[float, float, float, float]],
    outpath: str,
    annotate_mode: str = "latest",
    show: bool = False,
) -> None:
    if df.empty:
        print("No GPS rows found; skipping map.")
        return

    lat0 = np.deg2rad(BASE_LAT)
    df = df.copy()
    df["x"] = (df["longitude"] - BASE_LON) * np.cos(lat0)
    df["y"] = (df["latitude"] - BASE_LAT)

    fig = plt.figure(figsize=(7, 7))
    ax = fig.add_subplot(111)

    # base station at origin
    ax.scatter([0], [0], marker="*", s=220, label="Base station", zorder=6)
    ax.annotate("Base", (0, 0), textcoords="offset points", xytext=(6, 6))

    for (from_id, from_name), g in df.groupby(["from_id", "from_name"], sort=False):
        key = NodeKey(from_id=from_id, from_name=from_name)
        c = color_map.get(key, None)

        # lines from base to each point
        for xi, yi in zip(g["x"].values, g["y"].values):
            ax.plot([0, xi], [0, yi], linewidth=0.8, alpha=0.25, color=c)

        # plot points
        ax.scatter(g["x"], g["y"], s=18, alpha=0.9, label=key.label, color=c)

        # annotation rows selection
        if annotate_mode == "all":
            ann_rows = g
        else:
            # latest point per node (by timestamp)
            ann_rows = g.sort_values("timestamp").tail(1)

        for _, row in ann_rows.iterrows():
            rssi = row.get("rssi_dbm")
            snr = row.get("snr_db")
            xi, yi = float(row["x"]), float(row["y"])

            parts = [key.label]
            if pd.notna(rssi):
                parts.append(f"RSSI {rssi:.0f} dBm")
            if pd.notna(snr):
                parts.append(f"SNR {snr:.1f} dB")
            text = "\n".join(parts)

            # small offset so text doesn't sit directly on point
            ax.annotate(
                text,
                (xi, yi),
                textcoords="offset points",
                xytext=(8, 8),
                fontsize=8,
                bbox=dict(boxstyle="round,pad=0.25", alpha=0.75),
            )

    ax.set_title(f"GPS map with RSSI/SNR (center {BASE_LAT:.7f}, {BASE_LON:.7f})")
    ax.set_xlabel("ΔLongitude (deg) × cos(lat0)")
    ax.set_ylabel("ΔLatitude (deg)")
    ax.grid(True, alpha=0.3)
    ax.axis("equal")

    # Legend can get huge; keep it, but you can comment it out if you prefer
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(outpath, dpi=220)

    if show:
        plt.show()
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="Path to meshtastic_log.csv")
    ap.add_argument("--outdir", default="plots", help="Folder to save PNG (default: plots)")
    ap.add_argument("--show", action="store_true")
    ap.add_argument(
        "--annotate",
        choices=["latest", "all"],
        default="latest",
        help="Annotate latest point per node (default) or all points",
    )
    args = ap.parse_args()

    df = read_and_clean(args.csv)
    if df.empty:
        print("No GPS rows found in CSV.")
        return

    node_keys = [
        NodeKey(fid, fname)
        for fid, fname in df[["from_id", "from_name"]].drop_duplicates().itertuples(index=False)
    ]
    color_map = build_color_map(node_keys)

    os.makedirs(args.outdir, exist_ok=True)
    outpath = os.path.join(args.outdir, "gps_map_with_rssi_snr.png")

    plot_map_with_metrics(
        df=df,
        color_map=color_map,
        outpath=outpath,
        annotate_mode=args.annotate,
        show=args.show,
    )

    print(f"Saved: {outpath}")


if __name__ == "__main__":
    main()
