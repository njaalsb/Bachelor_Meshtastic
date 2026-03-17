import skrf as rf
import matplotlib.pyplot as plt
import os

# Configuration
TARGET_FREQ = 869.525
X_MIN, X_MAX = 700, 1050  # Set your limits here
FOLDER_PATH = '.' 

files = sorted([f for f in os.listdir(FOLDER_PATH) if f.endswith('.s1p')])

plt.figure(figsize=(11, 6))

for file in files:
    ntwk = rf.Network(os.path.join(FOLDER_PATH, file))
    
    # Convert Hz to MHz for the plot
    freq_mhz = ntwk.f / 1e6
    s_db = ntwk.s_db[:, 0, 0] 
    
    plt.plot(freq_mhz, s_db, label=file)

# 1. Add the vertical marker line
plt.axvline(x=TARGET_FREQ, color='red', linestyle='--', linewidth=1.5, label=f'{TARGET_FREQ} MHz')

# 2. Fix the X-axis limits
plt.xlim(X_MIN, X_MAX)

# 3. Final Polish
plt.title('S-Parameter Antenna Test', fontsize=14)
plt.xlabel('Frequency (MHz)', fontsize=12)
plt.ylabel('Magnitude (dB)', fontsize=12)
plt.grid(True, which='both', linestyle=':', alpha=0.6)
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
plt.tight_layout()

plt.show()