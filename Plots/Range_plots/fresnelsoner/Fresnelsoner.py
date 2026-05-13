import requests
import numpy as np
import matplotlib.pyplot as plt
import math

# --- Points ---
# Estenstadhytta <-> Gråkallen
#lat_1, lon_1 = 63.3945764, 10.4884753
#lat_2, lon_2 = 63.4212331, 10.2529852
#lat_1, lon_1 = 63.4192163, 10.3998152
#lat_2, lon_2 = 63.3949314, 10.4879423 
#lat_1, lon_1 = 63.4307656, 10.4274003 # Kuhaugen
#lat_2, lon_2 = 63.3948938, 10.4876772 # Estenstadshytta
lat_1,lon_1 = 63.4371437, 10.3914343 # Piren
lat_2,lon_2 = 63.4192163, 10.3998152 # gløs
#lat_1,lon_1 = 
#lat_2,lon_2 = 


freq = 869.525e6  # Hz
c = 3e8           # m/s
wavelength = c / freq

API_KEY = "ta_dej_en_bolle"  
N_SAMPLES = 100


def get_elevation_profile(lat1, lon1, lat2, lon2, samples, api_key):
    url = "https://maps.googleapis.com/maps/api/elevation/json"
    params = {
        "path": f"{lat1},{lon1}|{lat2},{lon2}",
        "samples": samples,
        "key": api_key,
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data["status"] != "OK":
        raise ValueError(f"Elevation API error: {data['status']}")
    results = data["results"]
    lats = np.array([r["location"]["lat"] for r in results])
    lons = np.array([r["location"]["lng"] for r in results])
    elevs = np.array([r["elevation"] for r in results])
    return lats, lons, elevs


def haversine(lat1, lon1, lat2, lon2):
    """Returns distance in metres between two lat/lon points."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# --- Fetch elevation profile ---
lats, lons, elevations = get_elevation_profile(lat_1, lon_1, lat_2, lon_2, N_SAMPLES, API_KEY)

# Cumulative horizontal distance along the profile
distances = np.zeros(N_SAMPLES)
for i in range(1, N_SAMPLES):
    distances[i] = distances[i - 1] + haversine(lats[i - 1], lons[i - 1], lats[i], lons[i])

D = distances[-1]  # total path length [m]

# --- Line of sight (straight line between endpoint elevations) ---
h1, h2 = elevations[0], elevations[-1]
los = h1 + (h2 - h1) * distances / D

# --- First Fresnel zone radius at each point ---
# r1 = sqrt(lambda * d1 * d2 / D), where d1 + d2 = D
fresnel_r = np.sqrt(wavelength * distances * (D - distances) / D)
fresnel_r[[0, -1]] = 0  # radius is zero at the antennas

# --- Plot ---
fig, ax = plt.subplots(figsize=(13, 6))

terrain_min = elevations.min() - 10
ax.fill_between(distances / 1000, terrain_min, elevations,
                color="saddlebrown", alpha=0.55, label="Terreng")
ax.plot(distances / 1000, elevations, color="saddlebrown", linewidth=1.2)

ax.plot(distances / 1000, los, "b-", linewidth=1.8, label="Siktlinje (LOS)")
ax.fill_between(distances / 1000, los - fresnel_r, los + fresnel_r,
                color="royalblue", alpha=0.25, label="1. Fresnelsone")
ax.plot(distances / 1000, los + fresnel_r, "b--", linewidth=0.9)
ax.plot(distances / 1000, los - fresnel_r, "b--", linewidth=0.9)

ax.set_xlim(0, D / 1000)
ax.set_ylim(terrain_min, max(elevations.max(), (los + fresnel_r).max()) + 20)
ax.set_xlabel("Avstand (km)")
ax.set_ylabel("Høyde (m o.h.)")
ax.set_title(
    f"Høydeprofil og 1. Fresnelsone\n"
    f"St. Olavs pir 2 → Gløshaugen  |  f = {freq / 1e6:.3f} MHz  |  D = {D / 1000:.2f} km"
)
ax.legend()
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig("fresnel_profile.png", dpi=150)
plt.show()
