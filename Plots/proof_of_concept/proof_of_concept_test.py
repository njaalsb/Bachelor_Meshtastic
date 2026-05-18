"""
plot_meshtastic_n50.py
======================
Plotter sender-/mottakerpunkter og linjer mellom dem på N50 kartgrunnlag.

Avhengigheter:
    pip install geopandas matplotlib pyproj fiona shapely

Bruk:
    python plot_meshtastic_n50.py
"""

import warnings
warnings.filterwarnings('ignore')
import os

import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from pyproj import Transformer
from shapely.geometry import box as shapely_box

# ─────────────────────────────────────────────────────────────────────────────
# KONFIGURASJON
# ─────────────────────────────────────────────────────────────────────────────

GML_AREALDEKKE  = r"C:\Users\bruhe\OneDrive - NTNU\Documents\ESI\ESI.sem6\bachelor_oppgave\github repo\Meshtastic-GOATS\Plots\Basisdata_5001_Trondheim_25832_N50Kartdata_GML\Basisdata_5001_Trondheim_25832_N50Arealdekke_GML.gml"
GML_SAMFERDSEL  = r"C:\Users\bruhe\OneDrive - NTNU\Documents\ESI\ESI.sem6\bachelor_oppgave\github repo\Meshtastic-GOATS\Plots\Basisdata_5001_Trondheim_25832_N50Kartdata_GML\Basisdata_5001_Trondheim_25832_N50Samferdsel_GML.gml"
GML_BYGNINGER   = r"C:\Users\bruhe\OneDrive - NTNU\Documents\ESI\ESI.sem6\bachelor_oppgave\github repo\Meshtastic-GOATS\Plots\Basisdata_5001_Trondheim_25832_N50Kartdata_GML\Basisdata_5001_Trondheim_25832_N50BygningerOgAnlegg_GML.gml"
GML_HOYDE       = r"C:\Users\bruhe\OneDrive - NTNU\Documents\ESI\ESI.sem6\bachelor_oppgave\github repo\Meshtastic-GOATS\Plots\Basisdata_5001_Trondheim_25832_N50Kartdata_GML\Basisdata_5001_Trondheim_25832_N50Hoyde_GML.gml"

UTFIL      = "rekkeviddetest_kart.png"
OPPLOSNING = 200        # DPI
FIGSTR     = (14, 16)   # Figurstørrelse i tommer

# ── SENDERE (legg til så mange du vil) ───────────────────────────────────────
#
# Hvert punkt trenger: name (str), lat (float), lon (float)
# Koordinater i WGS84 (desimalgrader) – finn dem på norgeskart.no eller GPS.
#
SENDERE = [
    {"name": "Estenstadshytta", "lat": 63.3948938, "lon": 10.4876772},
    {"name": "Gråkallen", "lat": 63.4212331,"lon": 10.2529852},
    {"name": "St. Olavs Pir","lat": 63.4371437, "lon": 10.3914343},
    {"name": "Kuhaugen", "lat": 63.4307656, "lon": 10.4274003},
    {"name": "Gløshaugen", "lat": 63.4192163, "lon": 10.3998152 }
    #{"name": "Ukjent node", "lat": 63.4126330, "lon": 10.3546880},
    #{"name": "bcdf", "lat": 63.4322940, "lon": 10.3612410},
    #{"name": "Ukjent", "lat": 63.3823230, "lon": 10.4062970},
    #{"name": "b058", "lat": 63.3839610, "lon" : 10.4062970},
    #{"name": "0ddc", "lat": 63.4126330, "lon" : 10.4071160}
]

# ── LINJER MELLOM SENDERE ─────────────────────────────────────────────────────
#
# Liste med par av sender-navn. Tegner en linje mellom hvert par.
# Bruk [] hvis du ikke vil ha noen linjer.
#
LINJER = [
    #("Gråkallen", "b058"),
    #("b058", "bcdf"),
    ("Gråkallen", "St. Olavs Pir"),
    ("Gråkallen", "Gløshaugen")
    #("Gråkallen", "St. Olavs Pir"),
    #("Estenstadshytta", "Kuhaugen"),
    #("Kuhaugen", "St. Olavs Pir"),
    #("Gløshaugen", "Gråkallen"),
    #("Gråkallen", "Kuhaugen"),
    #("Gløshaugen", "Kuhaugen")
    #("Gløshaugen", "bcdf"),
    #("bcdf", "St. Olavs Pir")
    #("b058", "bcdf")
]

# ── LINJEUTSEENDE ─────────────────────────────────────────────────────────────
LINJE_FARGE    = '#333333'
LINJE_BREDDE   = 1.5
LINJE_STIL     = '--'   # '-' | '--' | ':' | '-.'

# ── ZOOM / KARTUTSNITT ───────────────────────────────────────────────────────
#
# Tre modi – velg ett ved å sette ZOOM_MODUS:
#
#   "auto"    → Passer automatisk alle senderpunkter + MARGIN_METER buffer
#   "margin"  → Som "auto", men du styrer bufferstørrelsen selv
#   "manuell" → Du oppgir nøyaktige grenser selv
#
ZOOM_MODUS   = "manuell"   # "auto" | "margin" | "manuell"
MARGIN_METER = 800      # Buffer rundt punktene (brukes i "auto" og "margin")

# Aktive kun i ZOOM_MODUS = "manuell".
# Du kan oppgi enten UTM32N-koordinater ELLER WGS84 lat/lon.
#
# UTM32N (EPSG:25832) – finn koordinater på norgeskart.no:
ZOOM_XMIN = 569000      # Vestgrense  (meter øst)
ZOOM_XMAX = 571500      # Østgrense   (meter øst)
ZOOM_YMIN = 7031500     # Sørgrense   (meter nord)
ZOOM_YMAX = 7036000     # Nordgrense  (meter nord)

# WGS84 lat/lon – sett ZOOM_FRA_LATLON = True for å bruke disse i stedet:
ZOOM_FRA_LATLON = True
ZOOM_LAT_MIN    = 63.3750748     # Sørgrense  (grader nord)   
ZOOM_LAT_MAX    = 63.4512696     # Nordgrense (grader nord)
ZOOM_LON_MIN    = 10.2484850     # Vestgrense (grader øst)
ZOOM_LON_MAX    = 10.501     # Østgrense  (grader øst)

# ── UTSEENDE ─────────────────────────────────────────────────────────────────
TX_FARGER = ['#e63946', '#457b9d', '#2a9d8f', '#e9c46a', '#f4a261']

# ─────────────────────────────────────────────────────────────────────────────
# KONVERTER KOORDINATER
# ─────────────────────────────────────────────────────────────────────────────

to_utm = Transformer.from_crs("EPSG:4326", "EPSG:25832", always_xy=True)

def wgs84_til_utm(lat, lon):
    return to_utm.transform(lon, lat)   # always_xy: (lon, lat) → (x, y)

for tx in SENDERE:
    tx['x'], tx['y'] = wgs84_til_utm(tx['lat'], tx['lon'])

# Oppslag: navn → punkt (for linje-tegning)
sender_oppslag = {tx['name']: tx for tx in SENDERE}

print(f"  Sendere: {len(SENDERE)}")
print(f"  Linjer:  {len(LINJER)}")

# ─────────────────────────────────────────────────────────────────────────────
# BEREGN KARTUTSNITT
# ─────────────────────────────────────────────────────────────────────────────

if ZOOM_MODUS == "manuell":
    if ZOOM_FRA_LATLON:
        xmin, ymin = wgs84_til_utm(ZOOM_LAT_MIN, ZOOM_LON_MIN)
        xmax, ymax = wgs84_til_utm(ZOOM_LAT_MAX, ZOOM_LON_MAX)
        print(f"Zoom (fra lat/lon → UTM): x=[{xmin:.0f}, {xmax:.0f}], y=[{ymin:.0f}, {ymax:.0f}]")
    else:
        xmin, xmax = ZOOM_XMIN, ZOOM_XMAX
        ymin, ymax = ZOOM_YMIN, ZOOM_YMAX
        print(f"Zoom (manuell UTM): x=[{xmin:.0f}, {xmax:.0f}], y=[{ymin:.0f}, {ymax:.0f}]")
else:
    alle_x = [tx['x'] for tx in SENDERE]
    alle_y = [tx['y'] for tx in SENDERE]
    xmin = min(alle_x) - MARGIN_METER
    xmax = max(alle_x) + MARGIN_METER
    ymin = min(alle_y) - MARGIN_METER
    ymax = max(alle_y) + MARGIN_METER
    print(f"Zoom ({ZOOM_MODUS}, margin={MARGIN_METER} m): "
          f"x=[{xmin:.0f}, {xmax:.0f}], y=[{ymin:.0f}, {ymax:.0f}]")

# Shapely-boks og tuple-bbox brukes til lasting og klipping
kart_boks = shapely_box(xmin, ymin, xmax, ymax)
bbox      = (xmin, ymin, xmax, ymax)

# ─────────────────────────────────────────────────────────────────────────────
# LAST INN OG KLIPP GML-LAG
# ─────────────────────────────────────────────────────────────────────────────
#
# bbox-parameteren i gpd.read_file() begrenser hvilke features som leses
# (raskere), men store polygoner kan stikke utenfor utsnittet.
# Vi klipper dem derfor mot kart_boks etterpå.

print("Leser GML-lag...")

def les_lag(fil, lag, bbox, kart_boks, klipp=True):
    try:
        # På Windows lager GDAL en .gfs-sidecar-fil ved første lesing av en
        # GML-fil. Ved neste kjøring prøver GDAL å bruke denne i stedet for
        # selve .gml-filen, noe som feiler. Vi sletter den derfor alltid
        # før lesing for å sikre at .gml-filen leses direkte.
        gfs_fil = os.path.splitext(fil)[0] + ".gfs"
        if os.path.exists(gfs_fil):
            os.remove(gfs_fil)
        gdf = gpd.read_file(fil, layer=lag, bbox=bbox)
        if len(gdf) == 0:
            print(f"  {lag}: 0 objekter")
            return gdf
        # Behold kun de som faktisk overlapper kartutsnittet
        gdf = gdf[gdf.geometry.intersects(kart_boks)].copy()
        # Klipp polygoner mot kartutsnittet
        if klipp and gdf.geom_type.isin(['Polygon', 'MultiPolygon']).any():
            gdf['geometry'] = gdf.geometry.intersection(kart_boks)
            gdf = gdf[~gdf.geometry.is_empty].copy()
        print(f"  {lag}: {len(gdf)} objekter")
        return gdf
    except Exception as e:
        print(f"  {lag}: FEIL – {e}")
        return gpd.GeoDataFrame()

# Arealdekke
skog     = les_lag(GML_AREALDEKKE, 'Skog',               bbox, kart_boks)
elv      = les_lag(GML_AREALDEKKE, 'Elv',                bbox, kart_boks)
innsjø   = les_lag(GML_AREALDEKKE, 'Innsjø',             bbox, kart_boks)
myr      = les_lag(GML_AREALDEKKE, 'Myr',                bbox, kart_boks)
tettbeb  = les_lag(GML_AREALDEKKE, 'Tettbebyggelse',     bbox, kart_boks)
bymessig = les_lag(GML_AREALDEKKE, 'BymessigBebyggelse', bbox, kart_boks)

# Samferdsel – linjer, ikke klipp polygonvis
veglenke = les_lag(GML_SAMFERDSEL, 'Veglenke', bbox, kart_boks, klipp=False)
bane     = les_lag(GML_SAMFERDSEL, 'Bane',     bbox, kart_boks, klipp=False)

# Bygninger – skill punkter fra polygoner (begge er gyldige i N50)
bygning_all = les_lag(GML_BYGNINGER, 'Bygning', bbox, kart_boks)
if len(bygning_all):
    bygning_poly  = bygning_all[bygning_all.geom_type == 'Polygon']
    bygning_punkt = bygning_all[bygning_all.geom_type == 'Point']
else:
    bygning_poly  = gpd.GeoDataFrame()
    bygning_punkt = gpd.GeoDataFrame()

# Høydekurver
hkurve  = les_lag(GML_HOYDE, 'Høydekurve',  bbox, kart_boks, klipp=False)
hjkurve = les_lag(GML_HOYDE, 'Hjelpekurve', bbox, kart_boks, klipp=False)

# ─────────────────────────────────────────────────────────────────────────────
# PLOTT
# ─────────────────────────────────────────────────────────────────────────────

print("Tegner kart...")
fig, ax = plt.subplots(1, 1, figsize=FIGSTR, facecolor='#f5f0e8')
ax.set_facecolor('#f5f0e8')

# Sett aksegrenser FØR andre plot-kall – viktig for korrekt rendering
ax.set_xlim(xmin, xmax)
ax.set_ylim(ymin, ymax)

# --- Bakgrunnslag (rekkefølge betyr noe: laveste lag først) ---
if len(tettbeb):  tettbeb.plot(ax=ax,  color='#e8e0d0', linewidth=0, alpha=0.7)
if len(bymessig): bymessig.plot(ax=ax, color='#ddd5c5', linewidth=0, alpha=0.7)
if len(myr):      myr.plot(ax=ax,      color='#d4e8c8', linewidth=0, alpha=0.6)
if len(skog):     skog.plot(ax=ax,     color='#b8d4a0', linewidth=0, alpha=0.85)
if len(innsjø):   innsjø.plot(ax=ax,   color='#9ac4dc', linewidth=0, alpha=0.9)
if len(elv):      elv.plot(ax=ax,      color='#9ac4dc', linewidth=0, alpha=0.9)

# --- Høydekurver ---
if len(hjkurve): hjkurve.plot(ax=ax, color='#c4a882', linewidth=0.3, alpha=0.5)
if len(hkurve):  hkurve.plot(ax=ax,  color='#b8956e', linewidth=0.7, alpha=0.7)

# --- Bygninger ---
if len(bygning_poly):
    bygning_poly.plot(ax=ax, color='#c0a898', linewidth=0.3,
                      edgecolor='#8a7868', alpha=0.85)
if len(bygning_punkt):
    # Punktbygninger vises som små firkanter
    bygning_punkt.plot(ax=ax, color='#c0a898', markersize=4,
                       marker='s', edgecolor='#8a7868',
                       linewidths=0.5, alpha=0.7)

# --- Veier ---
if len(veglenke):
    veglenke.plot(ax=ax, color='white',   linewidth=1.5, alpha=0.95)
    veglenke.plot(ax=ax, color='#888880', linewidth=0.5, alpha=0.5)

# --- Jernbane (deaktivert) ---
# if len(bane):
#     bane.plot(ax=ax, color='#444440', linewidth=1.5, alpha=0.85, linestyle='--')

# --- Linjer mellom sendere ---
for navn1, navn2 in LINJER:
    p1 = sender_oppslag.get(navn1)
    p2 = sender_oppslag.get(navn2)
    if p1 and p2:
        ax.plot(
            [p1['x'], p2['x']], [p1['y'], p2['y']],
            color=LINJE_FARGE, linewidth=LINJE_BREDDE,
            linestyle=LINJE_STIL, zorder=15, alpha=0.85
        )
    else:
        print(f"  ADVARSEL: Fant ikke begge senderne i linjeparet ({navn1}, {navn2})")

# --- Senderpunkter (trekanter, én farge per sender) ---
for i, tx in enumerate(SENDERE):
    farge = TX_FARGER[i % len(TX_FARGER)]
    ax.scatter(tx['x'], tx['y'], c=farge, s=220, zorder=20,
               marker='^', edgecolors='white', linewidths=1.5)
    ax.annotate(
        tx['name'], (tx['x'], tx['y']),
        textcoords='offset points', xytext=(8, 6),
        fontsize=7.5, fontweight='bold', color='#111111',
        bbox=dict(boxstyle='round,pad=0.25', facecolor='white',
                  alpha=0.8, edgecolor='none')
    )

# --- Tegnforklaring ---
legend_el = [
    mpatches.Patch(color='#e8e0d0', label='Tettbebyggelse'),
    mpatches.Patch(color='#c0a898', label='Bygninger'),
    Line2D([0],[0], color='#b8956e', linewidth=1.2, label='Høydekurver'),
]
if LINJER:
    legend_el.append(
        Line2D([0],[0], color=LINJE_FARGE, linewidth=LINJE_BREDDE,
               linestyle=LINJE_STIL, label='Forbindelseslinje')
    )
for i, tx in enumerate(SENDERE):
    legend_el.append(
        Line2D([0],[0], marker='^', color='w',
               markerfacecolor=TX_FARGER[i % len(TX_FARGER)],
               markersize=10, markeredgecolor='white',
               label=f"TX: {tx['name']}")
    )

ax.legend(handles=legend_el, loc='upper left', fontsize=8,
          framealpha=0.92, fancybox=True, shadow=True)

# --- Rutenett og tittel ---
ax.set_title('Meshtastic proof of concept test LOS \nN50 kartgrunnlag (Kartverket)',
             fontsize=14, fontweight='bold', pad=14)
ax.set_xlabel('UTM Øst (m)',  fontsize=9)
ax.set_ylabel('UTM Nord (m)', fontsize=9)
ax.tick_params(labelsize=8)
ax.grid(True, linewidth=0.3, alpha=0.4, color='#888888')

# --- Målestokk ---
skala_m = 500
scale_x = xmin + (xmax - xmin) * 0.05
scale_y = ymin + (ymax - ymin) * 0.03
ax.plot([scale_x, scale_x + skala_m], [scale_y, scale_y],
        'k-', linewidth=3, zorder=25)
ax.text(scale_x + skala_m / 2, scale_y + (ymax - ymin) * 0.009,
        f'{skala_m} m', ha='center', fontsize=8, fontweight='bold')

# ─────────────────────────────────────────────────────────────────────────────
# LAGRE
# ─────────────────────────────────────────────────────────────────────────────

plt.tight_layout()
plt.savefig(UTFIL, dpi=OPPLOSNING, bbox_inches='tight')
print(f"\nKartet er lagret som '{UTFIL}'")
plt.show()
