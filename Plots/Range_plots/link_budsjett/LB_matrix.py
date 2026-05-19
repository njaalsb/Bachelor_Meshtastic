import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

P_tx = 22  # dBm, same for all devices

# (label, G_tx [dBi], P_sens [dBm], cable_loss [dB])
devices = [
    ("Sensecap",      0.39,   -138, 0.0),
    ("T3S3 Mono_short",     2.5,   -136, 0.0),
    ("T3S3 Dipol",  -0.584, -136, 0.584),  # dipole cable loss each end
    ("Heltec",        3.0,   -136, 0.0),
    ("T-Deck",        2.5,   -136, 0.0),
    ("Repeater Mini",         2.5,   -136, 0.0),
]

labels    = [d[0] for d in devices]
g_tx      = np.array([d[1] for d in devices])
p_sens    = np.array([d[2] for d in devices])
cable     = np.array([d[3] for d in devices])

n = len(devices)

# Link budget: P_tx + G_tx(i) + G_rx(j) - cable(i) - cable(j) - P_sens(j)
lb = np.zeros((n, n))
for i in range(n):
    for j in range(n):
        lb[i, j] = P_tx + g_tx[i] + g_tx[j] - cable[i] - cable[j] - p_sens[j]

# --- Plot ---
cmap = mcolors.LinearSegmentedColormap.from_list(
    "lb_map",
    ["#c00000", "#c06000", "#c0c000", "#80c000", "#00c000"],
    N=256,
)
vmin, vmax = lb.min(), lb.max()
norm = mcolors.Normalize(vmin=vmin, vmax=vmax)

fig, ax = plt.subplots(figsize=(max(6, n * 1.8), max(5, n * 1.6)))
fig.patch.set_facecolor("#f7f9fc")

for i in range(n):
    for j in range(n):
        val = lb[i, j]
        ax.add_patch(plt.Rectangle([j - 0.5, i - 0.5], 1, 1, color=cmap(norm(val))))
        ax.text(j, i, f"{val:.1f} dB",
                ha="center", va="center",
                color="black", weight="bold", fontsize=10)

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

plt.title("Linkbudsjettmatrise [dB]", pad=20, fontweight="bold", fontsize=14)
sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
plt.colorbar(sm, ax=ax, label="Link Budget (dB)")
plt.tight_layout()
plt.savefig("lb_matrix.png", dpi=150)
print("Saved lb_matrix.png")
plt.show()
