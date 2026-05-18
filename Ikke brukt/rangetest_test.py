import pandas as pd
from pathlib import Path
import math
import json
import re

CSV_PATH = Path("Rangetest-taket.csv")   
OUT_HTML = Path("map.html")

# (valgfritt) basestasjon-markør på kartet
BASE_LAT = 63.4184304
BASE_LON = 10.4014815

def fnum(x):
    try:
        if x is None:
            return None
        if isinstance(x, str) and x.strip() == "":
            return None
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except Exception:
        return None

def s(x):
    return "" if x is None else str(x)

seq_re = re.compile(r"^\s*seq\s*(\d+)\s*$", re.IGNORECASE)

df = pd.read_csv(CSV_PATH)
df.columns = [c.strip() for c in df.columns]

required = ["date", "time", "from", "sender name", "sender lat", "sender long", "rx lat", "rx long", "payload"]
missing = [c for c in required if c not in df.columns]
if missing:
    raise SystemExit(f"Mangler kolonner i CSV: {missing}")

seq_rows = []
for _, row in df.iterrows():
    payload = s(row["payload"]).strip()
    m = seq_re.match(payload)
    if not m:
        continue

    sender_lat = fnum(row["sender lat"])
    sender_lon = fnum(row["sender long"])
    rx_lat = fnum(row["rx lat"])
    rx_lon = fnum(row["rx long"])

    # Må ha begge punkter for å vise "sender ↔ rx"
    if sender_lat is None or sender_lon is None or rx_lat is None or rx_lon is None:
        continue

    seq_rows.append({
        "seq": int(m.group(1)),
        "date": s(row["date"]),
        "time": s(row["time"]),
        "from": s(row["from"]),
        "sender_name": s(row["sender name"]),
        "sender_lat": sender_lat,
        "sender_lon": sender_lon,
        "rx_lat": rx_lat,
        "rx_lon": rx_lon,
        "rx_snr": fnum(row.get("rx snr")),
        "distance_m": fnum(row.get("distance(m)")),
        "hop_limit": s(row.get("hop limit")),
    })

seq_rows.sort(key=lambda x: x["seq"])

if not seq_rows:
    raise SystemExit("Fant ingen 'seq X'-rader med både sender og rx lat/long.")

# center
all_lats = [r["sender_lat"] for r in seq_rows] + [r["rx_lat"] for r in seq_rows]
all_lons = [r["sender_lon"] for r in seq_rows] + [r["rx_lon"] for r in seq_rows]
center_lat = sum(all_lats) / len(all_lats)
center_lon = sum(all_lons) / len(all_lons)

rows_json = json.dumps(seq_rows, ensure_ascii=False)

HTML = r"""<!DOCTYPE html>
<html lang="no">
<head>
  <meta charset="utf-8" />
  <title>RangeTest seq – kart</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
  <style>
    html, body { height: 100%; margin: 0; }
    #map { height: 100%; width: 100%; }
    .panel {
      position: absolute; top: 12px; left: 12px; z-index: 999;
      background: white; padding: 10px 12px; border-radius: 10px;
      box-shadow: 0 6px 18px rgba(0,0,0,0.15);
      font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
      max-width: 520px;
    }
    .muted { color: #666; font-size: 13px; }
    .row { display:flex; gap:10px; align-items:center; flex-wrap:wrap; }
    select { padding: 6px 8px; border-radius: 8px; border: 1px solid #ccc; }
    button { padding: 6px 10px; border-radius: 8px; border: 1px solid #ccc; background: #fff; cursor: pointer; }
    code { background:#f3f3f3; padding:2px 6px; border-radius:6px; }
  </style>
</head>
<body>
  <div class="panel">
    <div><strong>RangeTest: seq X (sender ↔ mottaker)</strong></div>
    <div class="muted">Rader: <span id="nrows"></span></div>
    <div class="muted">Basestasjon (ref): __BASE_LAT__, __BASE_LON__</div>
    <div style="margin-top:8px;" class="row">
      <label for="seqSel" class="muted">Velg:</label>
      <select id="seqSel"></select>
      <button id="prevBtn">←</button>
      <button id="nextBtn">→</button>
      <button id="allBtn">Vis alle</button>
    </div>
    <div class="muted" id="info" style="margin-top:6px;"></div>
  </div>

  <div id="map"></div>

<script>
  const BASE = [__BASE_LAT_NUM__, __BASE_LON_NUM__];
  const rows = __ROWS_JSON__;
  document.getElementById("nrows").textContent = rows.length;

  const map = L.map("map").setView([__CENTER_LAT__, __CENTER_LON__], 16);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors"
  }).addTo(map);

  const houseIcon = L.icon({
    iconUrl: "https://cdn-icons-png.flaticon.com/512/25/25694.png",
    iconSize: [28, 28],
    iconAnchor: [14, 28]
  });

  L.marker(BASE, {icon: houseIcon})
    .addTo(map)
    .bindPopup("<b>Basestasjon</b><br/>(" + BASE[0].toFixed(6) + ", " + BASE[1].toFixed(6) + ")");

  const nodeColors = {};
  function colorFor(nodeId) {
    if (!nodeColors[nodeId]) {
      nodeColors[nodeId] = "#" + Math.floor(Math.random()*16777215).toString(16).padStart(6,"0");
    }
    return nodeColors[nodeId];
  }

  let activeLayers = [];
  function clearLayers() {
    for (const l of activeLayers) map.removeLayer(l);
    activeLayers = [];
  }

  function popupHtml(r) {
    const when = (r.date + " " + r.time).trim();
    const snr = (r.rx_snr ?? "");
    const dist = (r.distance_m ?? "");
    return `
      <div style="font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial;">
        <div><b>${r.sender_name || r.from}</b> <span style="color:#666;">(${r.from})</span></div>
        <div style="color:#666;">${when}</div>
        <hr/>
        <div><b>seq</b>: ${r.seq}</div>
        <div>SNR: <b>${snr}</b></div>
        <div>distance(m): <b>${dist}</b></div>
        <div>hop limit: <b>${r.hop_limit}</b></div>
        <div style="margin-top:6px; color:#666;">
          sender: ${r.sender_lat.toFixed(6)}, ${r.sender_lon.toFixed(6)}<br/>
          rx: ${r.rx_lat.toFixed(6)}, ${r.rx_lon.toFixed(6)}
        </div>
      </div>
    `;
  }

  function drawOne(r) {
    clearLayers();
    const c = colorFor(r.from);

    const sender = [r.sender_lat, r.sender_lon];
    const rx = [r.rx_lat, r.rx_lon];

    const senderMarker = L.circleMarker(sender, {
      radius: 7, color: c, fillColor: c, fillOpacity: 0.25, weight: 2
    }).addTo(map).bindPopup(popupHtml(r) + "<div style='margin-top:6px;'><b>Type:</b> sender</div>");

    const rxMarker = L.circleMarker(rx, {
      radius: 9, color: c, fillColor: c, fillOpacity: 0.75, weight: 2
    }).addTo(map).bindPopup(popupHtml(r) + "<div style='margin-top:6px;'><b>Type:</b> rx</div>");

    const line = L.polyline([sender, rx], { color: c, weight: 3, opacity: 0.6 }).addTo(map);

    activeLayers.push(senderMarker, rxMarker, line);

    const b = L.latLngBounds([sender, rx, BASE]);
    map.fitBounds(b, { padding: [40, 40] });

    document.getElementById("info").innerHTML =
      `Viser <b>seq ${r.seq}</b> · ${r.date} ${r.time} · node: <code>${r.from}</code>`;
  }

  function drawAll() {
    clearLayers();
    const b = L.latLngBounds([BASE]);

    for (const r of rows) {
      const c = colorFor(r.from);
      const sender = [r.sender_lat, r.sender_lon];
      const rx = [r.rx_lat, r.rx_lon];

      const senderMarker = L.circleMarker(sender, {
        radius: 4, color: c, fillColor: c, fillOpacity: 0.2, weight: 2
      }).addTo(map).bindPopup(popupHtml(r) + "<div style='margin-top:6px;'><b>Type:</b> sender</div>");

      const rxMarker = L.circleMarker(rx, {
        radius: 6, color: c, fillColor: c, fillOpacity: 0.7, weight: 2
      }).addTo(map).bindPopup(popupHtml(r) + "<div style='margin-top:6px;'><b>Type:</b> rx</div>");

      const line = L.polyline([sender, rx], { color: c, weight: 2, opacity: 0.25 }).addTo(map);

      activeLayers.push(senderMarker, rxMarker, line);
      b.extend(sender); b.extend(rx);
    }

    map.fitBounds(b, { padding: [40, 40] });
    document.getElementById("info").innerHTML = `Viser <b>alle</b> seq (${rows.length})`;
  }

  // Dropdown
  const sel = document.getElementById("seqSel");
  for (let i = 0; i < rows.length; i++) {
    const r = rows[i];
    const opt = document.createElement("option");
    opt.value = i;
    opt.textContent = "seq " + r.seq + " (" + r.time + ")";
    sel.appendChild(opt);
  }

  function currentIndex() { return parseInt(sel.value || "0", 10); }
  function setIndex(i) {
    i = Math.max(0, Math.min(rows.length - 1, i));
    sel.value = String(i);
    drawOne(rows[i]);
  }

  sel.addEventListener("change", () => setIndex(currentIndex()));
  document.getElementById("prevBtn").addEventListener("click", () => setIndex(currentIndex() - 1));
  document.getElementById("nextBtn").addEventListener("click", () => setIndex(currentIndex() + 1));
  document.getElementById("allBtn").addEventListener("click", () => drawAll());

  setIndex(0);
</script>
</body>
</html>
"""

HTML = (
    HTML.replace("__ROWS_JSON__", rows_json)
        .replace("__BASE_LAT__", f"{BASE_LAT:.6f}")
        .replace("__BASE_LON__", f"{BASE_LON:.6f}")
        .replace("__BASE_LAT_NUM__", str(BASE_LAT))
        .replace("__BASE_LON_NUM__", str(BASE_LON))
        .replace("__CENTER_LAT__", str(center_lat))
        .replace("__CENTER_LON__", str(center_lon))
)

OUT_HTML.write_text(HTML, encoding="utf-8")
print(f"Skrev: {OUT_HTML.resolve()}")
print(f"Seq-rader funnet: {len(seq_rows)}")