#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import math
import re
from pathlib import Path

CSV_FILE = Path("Rangetest-taket.csv")
OUT_HTML = Path("heatmap_leaflet.html")

SEQ_RE = re.compile(r"^seq\s+(\d+)\s*$", re.IGNORECASE)

def safe_float(s: str):
    try:
        x = float(s)
        if math.isfinite(x):
            return x
    except Exception:
        pass
    return None

def safe_int(s: str):
    try:
        return int(s)
    except Exception:
        return None

def main():
    if not CSV_FILE.exists():
        raise SystemExit(f"Fant ikke {CSV_FILE}. Legg scriptet i samme mappe som CSV-en.")

    points = []  # (lat, lon, intensity, seq, snr)
    with CSV_FILE.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            payload = (r.get("payload") or "").strip()
            m = SEQ_RE.match(payload)
            if not m:
                continue

            seq = safe_int(m.group(1))
            lat = safe_float((r.get("rx lat") or "").strip())
            lon = safe_float((r.get("rx long") or "").strip())
            snr = safe_float((r.get("rx snr") or "").strip())

            if lat is None or lon is None or seq is None:
                continue

            # Intensity choice:
            # A) use seq as intensity (as you asked earlier)
            intensity = float(seq)

            # If you’d rather use SNR as intensity (recommended), swap to:
            # intensity = max(0.0, (snr if snr is not None else 0.0) + 20.0)

            points.append((lat, lon, intensity, seq, snr))

    points.sort(key=lambda x: x[3])  # sort by seq

    if not points:
        raise SystemExit("Fant ingen rader med payload = 'seq N' og gyldig rx lat/rx long.")

    # center map at first point, fallback near Gløshaugen
    center_lat, center_lon = points[0][0], points[0][1]

    heat_js = ",\n      ".join(
        f"[{lat:.7f}, {lon:.7f}, {intensity:.6f}]"
        for (lat, lon, intensity, seq, snr) in points
    )

    marker_js = "\n      ".join(
        f"""L.circleMarker([{lat:.7f}, {lon:.7f}], {{radius:4, weight:1}})
        .bindTooltip("seq {seq}" + ({'true' if snr is not None else 'false'} ? " | snr {snr}" : ""), {{direction:"top", offset:[0,-6]}})
        .addTo(markerGroup);"""
        for (lat, lon, intensity, seq, snr) in points
    )

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Meshtastic seq heatmap (Leaflet)</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <style>
    html, body, #map {{ height: 100%; margin: 0; padding: 0; }}
    .panel {{
      position:absolute; top:12px; left:12px; z-index:9999;
      background:#fff; padding:10px 12px; border-radius:10px;
      box-shadow:0 6px 18px rgba(0,0,0,.18);
      font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;
      font-size:14px;
      max-width: 420px;
    }}
    .panel button{{ margin-right:8px; margin-top:6px; }}
    .muted{{ font-size:12px; opacity:.75; margin-top:6px; }}
  </style>
</head>
<body>
  <div id="map"></div>
  <div class="panel">
    <div><b>Meshtastic seq heatmap</b></div>
    <div id="stats"></div>
    <button id="toggleHeat">Toggle heat</button>
    <button id="toggleMarkers">Toggle markers</button>
    <div class="muted">Tiles: OpenStreetMap (no API key). Intensity = seq.</div>
  </div>

  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script src="https://unpkg.com/leaflet.heat/dist/leaflet-heat.js"></script>

  <script>
    const points = [
      {heat_js}
    ];

    const map = L.map("map").setView([{center_lat:.7f}, {center_lon:.7f}], 17);

    L.tileLayer("https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png", {{
      maxZoom: 20,
      attribution: "&copy; OpenStreetMap contributors"
    }}).addTo(map);

    const heat = L.heatLayer(points, {{
      radius: 28,
      blur: 20,
      maxZoom: 20
    }}).addTo(map);

    const markerGroup = L.layerGroup().addTo(map);
    {marker_js}

    // Fit bounds
    if (points.length >= 2) {{
      const bounds = L.latLngBounds(points.map(p => [p[0], p[1]]));
      map.fitBounds(bounds, {{ padding: [25, 25] }});
    }}

    document.getElementById("stats").textContent =
      `${{points.length}} seq-points`;

    let heatOn = true;
    let markersOn = true;

    document.getElementById("toggleHeat").onclick = () => {{
      heatOn = !heatOn;
      if (heatOn) heat.addTo(map); else map.removeLayer(heat);
    }};

    document.getElementById("toggleMarkers").onclick = () => {{
      markersOn = !markersOn;
      if (markersOn) markerGroup.addTo(map); else map.removeLayer(markerGroup);
    }};
  </script>
</body>
</html>
"""

    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"Skrev {OUT_HTML} med {len(points)} seq-punkter.")

if __name__ == "__main__":
    main()