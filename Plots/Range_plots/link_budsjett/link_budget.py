import numpy as np
import matplotlib.pyplot as plt

# Parameter fra sheets

# felles
lambda_868 = 0.345 #m

distance = np.linspace(1, 200000, 200)

# T3 S3

P_tx_t3s3 = 2.15 # Antenne-Gain dBi
G_tx_t3s3 = 22 # dBm

# Monopol

P_tx_mono_long = 3 
G_tx_mono_long = 22 

P_tx_mono_short = 2.5 
G_tx_mono_short = 22 

# Dipol

P_tx_dipol = 0
G_tx_dipol = 22 

# Heltec Mesh node

P_tx_spiral = 3 # dBi
G_tx_spiral = 22  

P_sens_low = -135  # dBm
P_sens_high = -124 # dBm 

# Sensecap T1000-E

G_tx_sens = 1 # dbi
P_tx_sens = 22 #dBm 

G_tx_pv = 2.5
P_tx_pv = 22

# Friis transmissjonsligning
def f(d, pt, gt, gr, ml=0):
    return pt + gt + gr -ml + 20*np.log10(lambda_868/(4*np.pi*d))

def g(d):
    return P_sens_low

def h(d):
    return P_sens_high

plt.plot(distance,f(distance, P_tx_dipol, G_tx_dipol, G_tx_dipol,ml=-2*0.57), label="dipol")
plt.plot(distance, f(distance, P_tx_t3s3, G_tx_t3s3, G_tx_t3s3, ml=-2*1.76), label="T3S3")
plt.plot(distance, f(distance, P_tx_mono_long, G_tx_mono_long, G_tx_mono_long), label="Monopol_long")
plt.plot(distance,f(distance, P_tx_mono_short, G_tx_mono_short, G_tx_mono_short), label="Monopol_short")
plt.plot(distance,f(distance, P_tx_pv, G_tx_pv, G_tx_pv), label="PV")
plt.plot(distance,f(distance, P_tx_spiral, G_tx_spiral, G_tx_spiral), label="spiral")
plt.plot(distance,f(distance, P_tx_sens, G_tx_sens, G_tx_sens), label="Sensecap")
#plt.axhline(y=P_sens_low, color='r', linestyle='--', label="Min sensitivitet (-135 dBm)")
#plt.axhline(y=P_sens_high, color='g', linestyle='--', label="Max sensitivitet (-124 dBm)")
#plt.xscale('log')
plt.title("RSSI vs distanse")
plt.xlabel("Distanse [m]")
plt.ylabel("P_rx [dBm]")
plt.legend()
plt.show()