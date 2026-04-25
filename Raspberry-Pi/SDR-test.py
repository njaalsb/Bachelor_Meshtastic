from rtlsdr import RtlSdr

# Initialize the device
sdr = RtlSdr()

# Configure device settings
sdr.sample_rate = 2.048e6    # 2.048 MHz
sdr.center_freq = 100.1e6    # 100.1 MHz (FM Station)
sdr.gain = 'auto'

# Read samples
samples = sdr.read_samples(1024)

print(f"Captured {len(samples)} samples.")
print(samples[:5]) # Display first 5 IQ samples

# Always close the device
sdr.close()
