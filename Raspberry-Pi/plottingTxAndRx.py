#!/usr/bin/env python3
import argparse
import re
import pandas as pd
import matplotlib.pyplot as plt

HEADER_RE = re.compile(r"SZ=(\d+);SEQ=(\d+);TS=(\d+);")

def parse_from_text(s: str):
    """Return (size, seq, ts_ms) hvis teksten matcher header, ellers (None,None,None)."""
    if not isinstance(s, str):
        return None, None, None
    m = HEADER_RE.search(s)
    if not m:
        return None, None, None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tx", default="tx_log.csv", help="TX log CSV (fra tx_payload_sweep.py)")
    ap.add_argument("--rx", default="rx_all.csv", help="RX log CSV (fra rx_log_all_working.py)")
    ap.add_argument("--only_sweep", action="store_true", help="Filtrer RX til kun SZ=... meldinger")
    args = ap.parse_args()

    tx = pd.read_csv(args.tx)
    rx = pd.read_csv(args.rx)

    # --- TX sanity + typer ---
    required_tx = {"seq", "size_bytes", "send_ms"}
    if not required_tx.issubset(set(tx.columns)):
        raise SystemExit(f"TX CSV mangler kolonner: {sorted(list(required_tx - set(tx.columns)))}")

    tx["seq"] = pd.to_numeric(tx["seq"], errors="coerce")
    tx["size_bytes"] = pd.to_numeric(tx["size_bytes"], errors="coerce")
    tx["send_ms"] = pd.to_numeric(tx["send_ms"], errors="coerce")
    tx = tx.dropna(subset=["seq", "size_bytes", "send_ms"]).copy()
    tx["seq"] = tx["seq"].astype(int)

    # --- RX: må ha text for å parse header ---
    if "text" not in rx.columns:
        raise SystemExit("RX CSV mangler kolonnen 'text'.")

    rx = rx.copy()
    rx["text"] = rx["text"].fillna("").astype(str)

    # Filtrer til tekstmeldinger hvis portnum finnes
    if "portnum" in rx.columns:
        rx = rx[rx["portnum"] == "TEXT_MESSAGE_APP"].copy()

    # Valgfritt: kun sweep-meldinger
    if args.only_sweep:
        rx = rx[rx["text"].str.startswith("SZ=")].copy()

    if len(rx) == 0:
        raise SystemExit("Ingen RX-tekstrader igjen etter filtrering.")

    # --- Parse SZ/SEQ/TS fra RX text ---
    parsed = rx["text"].apply(parse_from_text)
    rx["size_claimed"] = parsed.apply(lambda t: t[0])
    rx["seq"] = parsed.apply(lambda t: t[1])
    rx["ts_ms"] = parsed.apply(lambda t: t[2])

    rx_hdr = rx.dropna(subset=["seq", "size_claimed", "ts_ms"]).copy()
    rx_hdr["seq"] = rx_hdr["seq"].astype(int)
    rx_hdr["size_claimed"] = rx_hdr["size_claimed"].astype(int)
    rx_hdr["ts_ms"] = pd.to_numeric(rx_hdr["ts_ms"], errors="coerce")

    if len(rx_hdr) == 0:
        raise SystemExit("Fant ingen RX-meldinger med SZ/SEQ/TS header (bruk sweep-senderen).")

    # RSSI/SNR
    if "rssi_dbm" in rx_hdr.columns:
        rx_hdr["rssi_dbm"] = pd.to_numeric(rx_hdr["rssi_dbm"], errors="coerce")
    if "snr_db" in rx_hdr.columns:
        rx_hdr["snr_db"] = pd.to_numeric(rx_hdr["snr_db"], errors="coerce")

    # --- KORRIGERT: rx_timestamp -> epoch ms ---
    if "rx_timestamp" in rx_hdr.columns:
        rx_hdr["rx_time"] = pd.to_datetime(rx_hdr["rx_timestamp"], errors="coerce")
        rx_hdr["rx_ms"] = rx_hdr["rx_time"].astype("int64") / 1e6  # ns -> ms
    else:
        raise SystemExit("RX CSV mangler 'rx_timestamp' som trengs for latency.")

    # --- Merge på seq ---
    merged = tx.merge(
        rx_hdr[["seq", "size_claimed", "ts_ms", "rx_ms", "rssi_dbm", "snr_db"]],
        on="seq",
        how="left",
    )
    merged["received"] = merged["rx_ms"].notna()

    # --- PDR per size ---
    sent_per_size = merged.groupby("size_bytes")["seq"].count()
    recv_per_size = merged[merged["received"]].groupby("size_bytes")["seq"].count()
    pdr = (recv_per_size / sent_per_size).fillna(0.0)

    plt.figure()
    plt.plot(pdr.index, pdr.values)
    plt.xlabel("Payload size (bytes)")
    plt.ylabel("PDR (received/sent)")
    plt.title("Packet Delivery Ratio vs payload size")
    plt.ylim(-0.05, 1.05)
    plt.grid(True)
    plt.show()

    # --- Latency per size (KORRIGERT) ---
    merged["latency_ms"] = merged["rx_ms"] - merged["ts_ms"]
    lat = merged.dropna(subset=["latency_ms"]).copy()

    if len(lat) == 0:
        print("Ingen latency-punkter funnet.")
    else:
        grp = lat.groupby("size_bytes")["latency_ms"]
        med = grp.median()
        p10 = grp.quantile(0.10)
        p90 = grp.quantile(0.90)

        plt.figure()
        plt.plot(med.index, med.values)
        plt.plot(p10.index, p10.values, linestyle="--")
        plt.plot(p90.index, p90.values, linestyle="--")
        plt.xlabel("Payload size (bytes)")
        plt.ylabel("Latency (ms)")
        plt.title("Latency vs payload size")
        plt.grid(True)
        plt.show()

    # --- RSSI mean per size (received only) ---
    if "rssi_dbm" in merged.columns:
        rssi = merged.dropna(subset=["rssi_dbm"]).copy()
        if len(rssi) > 0:
            rssi_mean = rssi.groupby("size_bytes")["rssi_dbm"].mean()
            plt.figure()
            plt.plot(rssi_mean.index, rssi_mean.values)
            plt.xlabel("Payload size (bytes)")
            plt.ylabel("RSSI (dBm)")
            plt.title("Mean RSSI vs payload size")
            plt.grid(True)
            plt.show()

    # --- SNR mean per size (received only) ---
    if "snr_db" in merged.columns:
        snr = merged.dropna(subset=["snr_db"]).copy()
        if len(snr) > 0:
            snr_mean = snr.groupby("size_bytes")["snr_db"].mean()
            plt.figure()
            plt.plot(snr_mean.index, snr_mean.values)
            plt.xlabel("Payload size (bytes)")
            plt.ylabel("SNR (dB)")
            plt.title("Mean SNR vs payload size")
            plt.grid(True)
            plt.show()

    # --- Summary ---
    print("\n--- Summary ---")
    print("TX messages:", len(tx))
    print("RX parsed sweep messages:", len(rx_hdr))
    print("PDR min/max:", float(pdr.min()), float(pdr.max()))
    if len(lat) > 0:
        print("Latency median min/max (ms):", float(med.min()), float(med.max()))

if __name__ == "__main__":
    main()
