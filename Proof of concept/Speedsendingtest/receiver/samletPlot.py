import pandas as pd
import matplotlib.pyplot as plt
import os
import numpy as np

# --- Konfigurasjon ---
TOTAL_SENT = 100
ALL_DELAYS = [1, 2, 3]
BYTE_SIZES = [20, 150, 231]

data_config = {
    20: {
        'Short Fast': {1: 'shortfast_meshtastic_test_results_1seconds_20bytes.csv',
                       2: 'shortfast_meshtastic_test_results_2seconds_20bytes.csv',
                       3: 'shortfast_meshtastic_test_results_3seconds_20bytes.csv'},
        'Long Fast':  {1: 'longfast_meshtastic_test_results_1seconds_20bytes.csv',
                       2: 'longfast_meshtastic_test_results_2seconds_20bytes.csv',
                       3: 'longfast_meshtastic_test_results_3seconds_20bytes.csv'}
    },
    150: {
        'Short Fast': {1: 'shortfast_meshtastic_test_results_1seconds_150bytes.csv',
                       2: 'shortfast_meshtastic_test_results_2seconds_150bytes.csv',
                       3: 'shortfast_meshtastic_test_results_3seconds_150bytes.csv'},
        'Long Fast':  {1: 'longfast_meshtastic_test_results_1second_150bytes.csv',
                       2: 'longfast_meshtastic_test_results_2seconds_150bytes.csv',
                       3: 'longfast_meshtastic_test_results_3seconds_150bytes.csv'}
    },
    231: {
        'Short Fast': {1: 'shortfast_meshtastic_test_results_1seconds_231bytes.csv',
                       2: 'shortfast_meshtastic_test_results_2seconds_231bytes.csv',
                       3: 'shortfast_meshtastic_test_results_3seconds_231bytes.csv'},
        'Long Fast':  {1: 'longfast_meshtastic_test_results_1seconds_231bytes.csv',
                       2: 'longfast_meshtastic_test_results_2seconds_231bytes.csv',
                       3: 'longfast_meshtastic_test_results_3seconds_231bytes.csv'}
    }
}

colors = {'Short Fast': '#2980b9', 'Long Fast': '#e74c3c'}

# --- Opprett Figuren ---
fig, axes = plt.subplots(1, 3, figsize=(18, 7), sharey=True)
bar_width = 0.35
x = np.arange(len(ALL_DELAYS))

for idx, bytes_val in enumerate(BYTE_SIZES):
    ax = axes[idx]
    current_files = data_config[bytes_val]
    
    for i, (preset, delay_files) in enumerate(current_files.items()):
        received_values = []
        for delay in ALL_DELAYS:
            filename = delay_files.get(delay)
            if filename and os.path.exists(filename):
                df = pd.read_csv(filename)
                count = len(df[(df['Message'] != 'NA') & (df['RSSI'] != 'LOST')])
                received_values.append(count)
            else:
                received_values.append(0)

        offsets = x + (i - 0.5) * bar_width
        bars = ax.bar(offsets, received_values, width=bar_width, 
                      label=preset, color=colors[preset], alpha=0.85, edgecolor='white')

        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{int(height)}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 5), textcoords="offset points",
                        ha='center', va='bottom', fontsize=10, fontweight='bold')

    # Undertitler (20 Bytes, 150 Bytes, 231 Bytes)
    ax.set_title(f'{bytes_val} Bytes', fontsize=14, fontweight='bold', pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{d}s" for d in ALL_DELAYS])
    ax.set_xlabel('Forsinkelse (sekunder)', fontsize=11)
    ax.grid(True, axis='y', linestyle='--', alpha=0.3)
    
    if idx == 0:
        ax.set_ylabel('Mottatte pakker', fontsize=12)
    
    # FLYTTET LEGEND: Her plasserer vi den manuelt utenfor selve grafen
    if idx == 2:
        ax.legend(
            loc='lower right', 
            bbox_to_anchor=(1.0, 1.02), # Plasserer den rett over 231 Bytes-grafen
            frameon=True, 
            facecolor='white', 
            ncol=1, # Setter denne til 2 hvis du vil ha dem ved siden av hverandre
            fontsize=10
        )

plt.ylim(0, 115)
#plt.suptitle('Forsinkelsestest', fontsize=18, fontweight='bold')

# Justerer margene slik at tittelen og legend får plass
plt.tight_layout(rect=[0, 0.03, 1, 0.92]) 

plt.savefig('samlet_plot.png', dpi=150, bbox_inches='tight')
plt.show()