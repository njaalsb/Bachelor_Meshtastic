import pandas as pd
import matplotlib.pyplot as plt
import os

# Configuration
files = {
    1: 'meshtastic_test_results_1second_150bytes.csv',
    2: 'meshtastic_test_results_2seconds_150bytes.csv',
    3: 'meshtastic_test_results_3seconds_150bytes.csv',
    4: 'meshtastic_test_results_4seconds_150bytes.csv',
    5: 'meshtastic_test_results_5seconds_150bytes.csv'
}
TOTAL_SENT = 100

delays = []
received_counts = []

# Process each file
for delay, filename in sorted(files.items()):
    if os.path.exists(filename):
        df = pd.read_csv(filename)
        
        # Count rows where a message was actually received 
        # (Filtering out any row where Message is 'NA' or RSSI is 'LOST')
        success_df = df[(df['Message'] != 'NA') & (df['RSSI'] != 'LOST')]
        count = len(success_df)
        
        delays.append(delay)
        received_counts.append(count)
        print(f"Delay {delay}s: {count} packets received.")
    else:
        print(f"File {filename} not found.")

# Plotting
plt.figure(figsize=(10, 6))

# Line plot with markers to connect the points
plt.plot(delays, received_counts, marker='o', linestyle='-', 
         color='#2980b9', linewidth=2.5, markersize=10, label='Packets Received')

# Title and Labels
plt.title('150 Bytes', fontsize=14)
plt.xlabel('Delay Between Packets (Seconds)', fontsize=12)
plt.ylabel('Number of Packets Received (Out of 100)', fontsize=12)

# Grid and Formatting
plt.xticks(delays)
plt.ylim(0, 110)
plt.grid(True, linestyle='--', alpha=0.6)

# Add data labels above each point
for i, val in enumerate(received_counts):
    plt.annotate(f"{val}", (delays[i], val), textcoords="offset points", 
                 xytext=(0,12), ha='center', fontweight='bold', fontsize=10)

plt.tight_layout()
plt.show()