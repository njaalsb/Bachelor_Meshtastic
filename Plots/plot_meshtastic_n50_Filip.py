import warnings
warnings.filterwarnings('ignore')
import os

import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from pyproj import Transformer
from shapely.geometry import box as shapely_box

# ─────────────────────────────────────────────────────────────────────────────
# KONFIGURASJON
# ─────────────────────────────────────────────────────────────────────────────

CSV_FIL = r"Graakallen_estenstad_filip.csv" # Sti til CSV-filen
MAPPE = "Basisdata_5001_Trondheim_25832_N50Kartdata_GML"

GML_AREALDEKKE  = MAPPE + r"\Basisdata_5001_Trondheim_25832_N50Arealdekke_GML.gml"
GML_SAMFERDSEL  = MAPPE + r"\Basisdata_5001_Trondheim_25832_N50Samferdsel_GML.gml"
GML_BYGNINGER   = MAPPE + r"\Basisdata_5001_Trondheim_25832_N50BygningerOgAnlegg_GML.gml"
GML_HOYDE       = MAPPE + r"\Basisdata_5001_Trondheim_25832_N50Hoyde_GML.gml"

UTFIL      = "Graakallen_estenstad_filip.png"  
OPPLOSNING = 200        # DPI
FIGSTR     = (14, 16)   # Figurstørrelse i tommer

# ── OPPDATERTE KOORDINATER ───────────────────────────────────────────────────
NODE_1_LAT, NODE_1_LON = 63.418140, 10.404026  # Ny TX Node-posisjon
NODE_2_LAT, NODE_2_LON = 63.416946, 10.406386  # RX Node (forblir uendret)

# ── ZOOM / KARTUTSNITT ───────────────────────────────────────────────────────
ZOOM_MODUS   = "auto"      
MARGIN_METER = 500         # Buffer rundt nodene i meter

# ─────────────────────────────────────────────────────────────────────────────
# KOORDINATKONVERTERING
# ─────────────────────────────────────────────────────────────────────────────

to_utm = Transformer.from_crs("EPSG:4326", "EPSG:25832", always_xy=True)

def wgs84_til_utm(lat, lon):
    return to_utm.transform(lon, lat)

# Konverter de to spesifikke nodene til UTM
node1_x, node1_y = wgs84_til_utm(NODE_1_LAT, NODE_1_LON)
node2_x, node2_y = wgs84_til_utm(NODE_2_LAT, NODE_2_LON)

# Beregn boks basert på de nye posisjonene
xmin = min(node1_x, node2_x) - MARGIN_METER
xmax = max(node1_x, node2_x) + MARGIN_METER
ymin = min(node1_y, node2_y) - MARGIN_METER
ymax = max(node1_y, node2_y) + MARGIN_METER

kart_boks = shapely_box(xmin, ymin, xmax, ymax)
bbox      = (xmin, ymin, xmax, ymax)

# ─────────────────────────────────────────────────────────────────────────────
# LAST INN OG KLIPP GML-LAG
# ─────────────────────────────────────────────────────────────────────────────

print("Leser GML-lag...")
def les_lag(fil, lag, bbox, kart_boks, klipp=True):
    try:
        gfs_fil = os.path.splitext(fil)[0] + ".gfs"
        if os.path.exists(gfs_fil):
            os.remove(gfs_fil)
        gdf = gpd.read_file(fil, layer=lag, bbox=bbox)
        if len(gdf) == 0:
            return gdf
        gdf = gdf[gdf.geometry.intersects(kart_boks)].copy()
        if klipp and gdf.geom_type.isin(['Polygon', 'MultiPolygon']).any():
            gdf['geometry'] = gdf.geometry.intersection(kart_boks)
            gdf = gdf[~gdf.geometry.is_empty].copy()
        print(f"  {lag}: {len(gdf)} objekter")
        return gdf
    except Exception as e:
        print(f"  {lag}: FEIL – {e}")
        return gpd.GeoDataFrame()

skog     = les_lag(GML_AREALDEKKE, 'Skog',                bbox, kart_boks)
elv      = les_lag(GML_AREALDEKKE, 'Elv',                 bbox, kart_boks)
innsjø   = les_lag(GML_AREALDEKKE, 'Innsjø',              bbox, kart_boks)
myr      = les_lag(GML_AREALDEKKE, 'Myr',                 bbox, kart_boks)
tettbeb  = les_lag(GML_AREALDEKKE, 'Tettbebyggelse',      bbox, kart_boks)
bymessig = les_lag(GML_AREALDEKKE, 'BymessigBebyggelse',  bbox, kart_boks)
veglenke = les_lag(GML_SAMFERDSEL, 'Veglenke',            bbox, kart_boks, klipp=False)
bane     = les_lag(GML_SAMFERDSEL, 'Bane',                bbox, kart_boks, klipp=False)

bygning_all = les_lag(GML_BYGNINGER, 'Bygning', bbox, kart_boks)
if len(bygning_all):
    bygning_poly  = bygning_all[bygning_all.geom_type == 'Polygon']
    bygning_punkt = bygning_all[bygning_all.geom_type == 'Point']
else:
    bygning_poly  = gpd.GeoDataFrame()
    bygning_punkt = gpd.GeoDataFrame()

hkurve  = les_lag(GML_HOYDE, 'Høydekurve',  bbox, kart_boks, klipp=False)
hjkurve = les_lag(GML_HOYDE, 'Hjelpekurve', bbox, kart_boks, klipp=False)

# ─────────────────────────────────────────────────────────────────────────────
# PLOTT
# ─────────────────────────────────────────────────────────────────────────────

print("Tegner kart...")
fig, ax = plt.subplots(1, 1, figsize=FIGSTR, facecolor='#f5f0e8')
ax.set_facecolor('#f5f0e8')

ax.set_xlim(xmin, xmax)
ax.set_ylim(ymin, ymax)

# --- Bakgrunnslag ---
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
    bygning_poly.plot(ax=ax, color='#c0a898', linewidth=0.3, edgecolor='#8a7868', alpha=0.85)
if len(bygning_punkt):
    bygning_punkt.plot(ax=ax, color='#c0a898', markersize=4, marker='s', edgecolor='#8a7868', linewidths=0.5, alpha=0.7)

# --- Veier ---
if len(veglenke):
    veglenke.plot(ax=ax, color='white',   linewidth=1.5, alpha=0.95)
    veglenke.plot(ax=ax, color='#888880', linewidth=0.5, alpha=0.5)

# --- Jernbane ---
if len(bane):
    bane.plot(ax=ax, color='#444440', linewidth=1.5, alpha=0.85, linestyle='--')

# ── PLOT NODENE ──────────────────────────────────────────────────────────────

# 1. Plot TX Node (Rød trekant - Ny posisjon)
ax.scatter(node1_x, node1_y, c='#e63946', s=220, zorder=20, marker='^', edgecolors='white', linewidths=1.5)
ax.annotate('TX', (node1_x, node1_y), textcoords='offset points', xytext=(8, 6),
            fontsize=8, fontweight='bold', color='#111111',
            bbox=dict(boxstyle='round,pad=0.25', facecolor='white', alpha=0.8, edgecolor='none'))

# 2. Plot RX Node (Mørkegrå trekant)
ax.scatter(node2_x, node2_y, c='#343a40', s=220, zorder=20, marker='^', edgecolors='white', linewidths=1.5)
ax.annotate('RX', (node2_x, node2_y), textcoords='offset points', xytext=(8, 6),
            fontsize=8, fontweight='bold', color='#111111',
            bbox=dict(boxstyle='round,pad=0.25', facecolor='white', alpha=0.8, edgecolor='none'))


# --- Tegnforklaring ---
legend_el = [
    mpatches.Patch(color='#e8e0d0', label='Tettbebyggelse'),
    mpatches.Patch(color='#c0a898', label='Bygninger'),
    Line2D([0],[0], color='#b8956e', linewidth=1.2, label='Høydekurver'),
    Line2D([0],[0], marker='^', color='w', markerfacecolor='#e63946', markersize=10, markeredgecolor='white', label="TX Node"),
    Line2D([0],[0], marker='^', color='w', markerfacecolor='#343a40', markersize=10, markeredgecolor='white', label="RX Node")
]

ax.legend(handles=legend_el, loc='upper left', fontsize=8, framealpha=0.92, fancybox=True, shadow=True)

# --- Rutenett og tittel ---
ax.set_title('Meshtastic rekkeviddetest: kort distanse urbant område\nN50 kartgrunnlag (Kartverket)', fontsize=14, fontweight='bold', pad=14)
ax.set_xlabel('UTM Øst (m)',  fontsize=9)
ax.set_ylabel('UTM Nord (m)', fontsize=9)
ax.tick_params(labelsize=8)
ax.grid(True, linewidth=0.3, alpha=0.4, color='#888888')

# --- Målestokk ---
skala_m = 500
scale_x = xmin + (xmax - xmin) * 0.05
scale_y = ymin + (ymax - ymin) * 0.03
ax.plot([scale_x, scale_x + skala_m], [scale_y, scale_y], 'k-', linewidth=3, zorder=25)
ax.text(scale_x + skala_m / 2, scale_y + (ymax - ymin) * 0.009, f'{skala_m} m', ha='center', fontsize=8, fontweight='bold')

# ─────────────────────────────────────────────────────────────────────────────
# LAGRE
# ─────────────────────────────────────────────────────────────────────────────

plt.tight_layout()
plt.savefig(UTFIL, dpi=OPPLOSNING, bbox_inches='tight')
print(f"\nKartet er lagret som '{UTFIL}'")
plt.show()