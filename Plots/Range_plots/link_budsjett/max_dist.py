# Kode for å beregne teoretisk max distanse for kommunikasjon med ulike antenner:

import numpy as np
import matplotlib.pyplot as plt 

wl = (3*10**8)/(869.525*10**6)

lb = [154-0.57*2, 159, 160, 158.3-1.76*2, 159, 159, 160]

lb_boost = [158-0.57*2, 163, 164, 162.3-1.76*2,163,163,165]

def lin(linkbud):
    return 10**(linkbud/10)

def distanse(linkbud_lin):
    return np.sqrt(linkbud_lin)*wl/(4*np.pi)
    

for i in range(len(lb)):
    link_lin = lin(lb_boost[i])
    print(distanse(link_lin))
    
