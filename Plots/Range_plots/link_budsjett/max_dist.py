# Kode for å beregne teoretisk max distanse for kommunikasjon med ulike antenner:

import numpy as np
import matplotlib.pyplot as plt 

wl = (3*10**8)/(869.525*10**6)

lb = [156.78, 154-0.584*2, 159, 160, 158.3-2.204*2, 159, 159, 160]

lb_boost = [160.78, 158-0.584*2, 163, 164, 162.3-2.204*2,163,163,164]

def lin(linkbud):
    return 10**(linkbud/10)

def distanse(linkbud_lin):
    return np.sqrt(linkbud_lin)*wl/(4*np.pi)
    

    
def h(da_list):
    for i in range(len(da_list)):
        link_lin = lin(da_list[i])
        print(distanse(link_lin))

print(f'uten boost')
h(lb)
print(f'med boost')
h(lb_boost)
