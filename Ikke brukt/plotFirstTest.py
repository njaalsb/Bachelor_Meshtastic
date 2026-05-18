#!/usr/bin/env python3
"""
Meshtastic log plotter

- Plots RSSI vs time (one line per node)
- Plots SNR vs time  (one line per node)
- Plots a simple "map" centered at the base station:
    (63.4184304, 10.4014815)
  and draws lines from the base station to every received GPS point.

Usage:
  python plot_meshtastic.py --csv meshtastic_log.csv
  python plot_meshtastic.py --csv meshtastic_log.csv --outdir plots --show

Dependencies:
  pip install pandas matplotlib
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
        # Prefer name if it looks like a real name; otherwise include id
        if self.from_name and str(self.from_name) != str(self.from_id):
            return f"{self.from_name} ({self.from_id})"
        return str(self.from_id)


def build_color_map(keys, cmap_name="tab20") -> Dict[NodeKey, Tuple[float, float, float, float]]:
    cmap = plt.get_cmap(cmap_name)
    keys = list(keys)
    n = max(1, len(keys))
    return {k: cmap(i % cmap.N) for i, k in enumerate(keys)}


def read_and_clean(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    # Normalize expected columns
    required = ["timestamp", "from_id", "from_name", "rssi_dbm", "snr_db", "latitude", "longitude"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"CSV is missing columns: {missing}\nFound columns: {list(df.columns)}")

    # Parse time
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=False)
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp")

    # Ensure ids are strings (stable legend / grouping)
    df["from_id"] = df["from_id"].astype(str)
    df["from_name"] = df["from_name"].astype(str)

    # Numeric columns
    for col in ["rssi_dbm", "snr_db", "latitude", "longitude"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def plot_time_series(df: pd.DataFrame, value_col: str, ylabel: str, title: str,
                     color_map: Dict[NodeKey, Tuple[float, float, float, float]],
                     outpath: str | None = None, show: bool = False) -> None:
    plt.figure(figsize=(12, 5))

    # group by node
    for (from_id, from_name), g in df.groupby(["from_id", "from_name"], sort=False):
        key = NodeKey(from_id=from_id, from_name=from_name)
        gg = g.dropna(subset=[value_col])
        if gg.empty:
            continue
        plt.plot(gg["timestamp"], gg[value_col], label=key.label, color=color_map.get(key, None))

    plt.title(title)
    plt.xlabel("Time")
    plt.ylabel(ylabel)
    plt.grid(True, alpha=0.3)
    plt.legend(loc="best", fontsize=9)
    plt.tight_layout()

    if outpath:
        plt.savefig(outpath, dpi=200)
    if show:
        plt.show()
    plt.close()


def plot_map(df: pd.DataFrame,
             color_map: Dict[NodeKey, Tuple[float, float, float, float]],
             outpath: str | None = None, show: bool = False) -> None:
    # Only rows with GPS
    gps = df.dropna(subset=["latitude", "longitude"]).copy()
    if gps.empty:
        print("No latitude/longitude data found; skipping map plot.")
        return

    # Local “flat” projection around base: scale longitude by cos(lat0)
    lat0 = np.deg2rad(BASE_LAT)
    x = (gps["longitude"].values - BASE_LON) * np.cos(lat0)
    y = (gps["latitude"].values - BASE_LAT)

    gps["x"] = x
    gps["y"] = y

    plt.figure(figsize=(7, 7))

    # Plot base station at origin
    plt.scatter([0], [0], marker="*", s=220, label="Base station", zorder=5)
    plt.annotate("Base", (0, 0), textcoords="offset points", xytext=(6, 6))

    # Draw lines and points per node (color-coded)
    for (from_id, from_name), g in gps.groupby(["from_id", "from_name"], sort=False):
        key = NodeKey(from_id=from_id, from_name=from_name)
        c = color_map.get(key, None)

        # Lines from base to every point
        for xi, yi in zip(g["x"].values, g["y"].values):
            plt.plot([0, xi], [0, yi], linewidth=0.8, alpha=0.25, color=c)

        # Points
        plt.scatter(g["x"], g["y"], s=18, alpha=0.9, label=key.label, color=c)

    plt.title(f"GPS points (centered at {BASE_LAT:.7f}, {BASE_LON:.7f})")
    plt.xlabel("ΔLongitude (deg) × cos(lat0)")
    plt.ylabel("ΔLatitude (deg)")
    plt.grid(True, alpha=0.3)
    plt.axis("equal")
    plt.legend(loc="best", fontsize=9)
    plt.tight_layout()

    if outpath:
        plt.savefig(outpath, dpi=200)
    if show:
        plt.show()
    plt.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="Path to meshtastic_log.csv")
    ap.add_argument("--outdir", default="", help="Optional folder to save PNG plots")
    ap.add_argument("--show", action="store_true", help="Show plots interactively")
    args = ap.parse_args()

    df = read_and_clean(args.csv)

    node_keys = [NodeKey(fid, fname) for fid, fname in df[["from_id", "from_name"]].drop_duplicates().itertuples(index=False)]
    color_map = build_color_map(node_keys, cmap_name="tab20")

    outdir = args.outdir.strip()
    if outdir:
        os.makedirs(outdir, exist_ok=True)

    rssi_out = os.path.join(outdir, "rssi_vs_time.png") if outdir else None
    snr_out = os.path.join(outdir, "snr_vs_time.png") if outdir else None
    map_out = os.path.join(outdir, "gps_map.png") if outdir else None

    plot_time_series(
        df=df,
        value_col="rssi_dbm",
        ylabel="RSSI (dBm)",
        title="Meshtastic RSSI vs time",
        color_map=color_map,
        outpath=rssi_out,
        show=args.show,
    )

    plot_time_series(
        df=df,
        value_col="snr_db",
        ylabel="SNR (dB)",
        title="Meshtastic SNR vs time",
        color_map=color_map,
        outpath=snr_out,
        show=args.show,
    )

    plot_map(
        df=df,
        color_map=color_map,
        outpath=map_out,
        show=args.show,
    )

    if outdir:
        print(f"Saved plots to: {outdir}")


if __name__ == "__main__":
    main()
