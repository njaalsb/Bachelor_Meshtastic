import numpy as np
import matplotlib.pyplot as plt

# Parameter fra sheets

# felles
lambda_868 = 0.345 #m

distance = np.linspace(1, 20000, 20000)

# LilyGO T3 S3

G_tx_lily = 2.73 # Antenne-Gain dBi
P_tx_lily = 22 # dBm

# LilyGO T-deck

G_tx_tdeck = 2.73
P_tx_tdeck = 22

# Heltec Mesh node

G_tx_heltec = 3  # dBi 
P_tx_heltec = 22 # dBm

P_sens_low = -135  # dBm
P_sens_high = -124 # dBm 

# Sensecap T1000-E

G_tx_sens = 1 # dbi
P_tx_sens = 22 #dBm 

# Friis transmissjonsligning
def f(d, pt, gt, gr):
    return pt + gt + gr + 20*np.log10(lambda_868/(4*np.pi*d))

def g(d):
    return P_sens_low

def h(d):
    return P_sens_high

plt.plot(f(distance, P_tx_heltec, G_tx_heltec, G_tx_heltec), label="Heltec")
plt.plot(f(distance, P_tx_lily, G_tx_lily, G_tx_lily), label="LilyGO T3 S3")
plt.plot(f(distance, P_tx_tdeck, G_tx_tdeck, G_tx_tdeck), label="T-deck")
plt.plot(f(distance, P_tx_sens, G_tx_sens, G_tx_sens), label="Sensecap")
#plt.axhline(y=P_sens_low, color='r', linestyle='--', label="Min sensitivitet (-135 dBm)")
#plt.axhline(y=P_sens_high, color='g', linestyle='--', label="Max sensitivitet (-124 dBm)")

plt.title("P_rx(d)")
plt.xlabel("Distanse [m]")
plt.ylabel("P_rx [dBm]")
plt.legend()
plt.show()