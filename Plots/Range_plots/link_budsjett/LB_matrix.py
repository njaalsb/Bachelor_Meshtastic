# Beregning av verdier til en kompatibilitetsmatrise

# Felles transmitt effekt for alle:

P_tx = 22 # dBm 

# Sensecap specs 

cap_g_tx = 1         # dBi
cap_p_sens = -138

# T3S3 specs

t3s3_g_tx_mono = 2.5          # dBi
t3s3_g_tx_di   = 0 - 0.584    # dBi
t3s3_p_sens = -136

# Helctec specs 

heltec_g_tx = 3         # dBi
heltec_p_sens = -136 

# T-deck specs

t_deck_g_tx = 2.5
t_deck_p_sens = -136

# Solar specs

solar_g_tx = 3
solar_p_tx = -136

def link(gt, gr, psens):
    return P_tx + gt + gr - psens 

print(link(t3s3_g_tx_di,t3s3_g_tx_di, t3s3_p_sens))