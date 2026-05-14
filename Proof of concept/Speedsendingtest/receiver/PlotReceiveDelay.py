import pandas as pd
import matplotlib.pyplot as plt
import os
import numpy as np

# Configuration
TOTAL_SENT = 100

files = {
    'Short Fast': {
        1: 'shortfast_meshtastic_test_results_1seconds_20bytes.csv',
        2: 'shortfast_meshtastic_test_results_2seconds_20bytes.csv',
        3: 'shortfast_meshtastic_test_results_3seconds_20bytes.csv',
        #4: 'shortfast_meshtastic_test_results_4seconds_20bytes.csv',
        #5: 'shortfast_meshtastic_test_results_5seconds_20bytes.csv',
    },
    'Long Fast': {
        1: 'longfast_meshtastic_test_results_1seconds_20bytes.csv',
        2: 'longfast_meshtastic_test_results_2seconds_20bytes.csv',
        3: 'longfast_meshtastic_test_results_3seconds_20bytes.csv',
        #4: 'longfast_meshtastic_test_results_4seconds_20bytes.csv',
        #5: 'longfast_meshtastic_test_results_5seconds_20bytes.csv',
    }
}



''' 
files = {
    'Short Fast': {
        1: 'shortfast_meshtastic_test_results_1seconds_150bytes.csv',
        2: 'shortfast_meshtastic_test_results_2seconds_150bytes.csv',
        3: 'shortfast_meshtastic_test_results_3seconds_150bytes.csv',
        #4: 'shortfast_meshtastic_test_results_4seconds_150bytes.csv',
        #5: 'shortfast_meshtastic_test_results_5seconds_150bytes.csv',
    },
    'Long Fast': {
        1: 'longfast_meshtastic_test_results_1second_150bytes.csv',
        2: 'longfast_meshtastic_test_results_2seconds_150bytes.csv',
        3: 'longfast_meshtastic_test_results_3seconds_150bytes.csv',
        #4: 'longfast_meshtastic_test_results_4seconds_150bytes.csv',
        #5: 'longfast_meshtastic_test_results_5seconds_150bytes.csv',
    }
}
'''

'''
files = {
    'Short Fast': {
        1: 'shortfast_meshtastic_test_results_1seconds_231bytes.csv',
        2: 'shortfast_meshtastic_test_results_2seconds_231bytes.csv',
        3: 'shortfast_meshtastic_test_results_3seconds_231bytes.csv',
        #4: 'shortfast_meshtastic_test_results_4seconds_231bytes.csv',
        #5: 'shortfast_meshtastic_test_results_5seconds_231bytes.csv',
    },
    'Long Fast': {
        1: 'longfast_meshtastic_test_results_1seconds_231bytes.csv',
        2: 'longfast_meshtastic_test_results_2seconds_231bytes.csv',
        3: 'longfast_meshtastic_test_results_3seconds_231bytes.csv',
        #4: 'longfast_meshtastic_test_results_4seconds_231bytes.csv',
        #5: 'longfast_meshtastic_test_results_5seconds_231bytes.csv',
    }
}
'''


# Colors for each preset
colors = {
    'Short Fast': '#2980b9',
    'Long Fast':  '#e74c3c'
}

# Collect results
results = {}
for preset, delay_files in files.items():
    results[preset] = {}
    for delay, filename in sorted(delay_files.items()):
        if os.path.exists(filename):
            df = pd.read_csv(filename)
            success_df = df[(df['Message'] != 'NA') & (df['RSSI'] != 'LOST')]
            received = len(success_df)
            # Endret her: Lagrer 'received' i stedet for 'packet_loss'
            results[preset][delay] = received
            print(f"{preset} | Delay {delay}s: {received}/{TOTAL_SENT} received")
        else:
            print(f"File not found: {filename} — skipping.")
            results[preset][delay] = None

# --- Plotting ---
#all_delays = [1, 2, 3, 4, 5]
all_delays = [1, 2, 3]  
n_presets = len(results)
bar_width = 0.35
x = np.arange(len(all_delays))

fig, ax = plt.subplots(figsize=(11, 6))

for i, (preset, delay_data) in enumerate(results.items()):
    offsets = x + (i - (n_presets - 1) / 2) * bar_width
    # Henter nå ut antall mottatte pakker
    received_values = [delay_data.get(d, None) for d in all_delays]

    bars = ax.bar(
        offsets,
        [v if v is not None else 0 for v in received_values],
        width=bar_width,
        label=preset,
        color=colors[preset],
        alpha=0.85,
        edgecolor='white'
    )

    # Add value labels on top of each bar
    for bar, val in zip(bars, received_values):
        # Endret her: Viser kun tallet (f.eks "95") i stedet for prosent
        label = f"{int(val)}" if val is not None else "N/A"
        ax.annotate(
            label,
            xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
            xytext=(0, 4),
            textcoords="offset points",
            ha='center',
            fontsize=10,
            fontweight='bold'
        )

# Oppdaterte titler og akser
ax.set_title('Antall mottatte pakker per intervall (20 bytes)', fontsize=14)
ax.set_xlabel('Forsinkelse mellom pakker (sekunder)', fontsize=12)
ax.set_ylabel('Mottatte pakker', fontsize=12)
ax.set_xticks(x)
ax.set_xticklabels([f"{d}s" for d in all_delays])
# Setter maksgrense på y-aksen til litt over TOTAL_SENT for å få plass til labels
ax.set_ylim(0, TOTAL_SENT + 15) 
ax.legend(fontsize=11)
ax.grid(True, axis='y', linestyle='--', alpha=0.5)

plt.tight_layout()
plt.savefig('packet_reception_comparison.png', dpi=150)
plt.show()