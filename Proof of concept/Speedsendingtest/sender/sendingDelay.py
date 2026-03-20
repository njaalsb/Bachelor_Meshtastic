import meshtastic
import meshtastic.serial_interface
import time

interface = meshtastic.serial_interface.SerialInterface(devPath='/dev/ttyACM0')

def send_test_packets(count=100, delay=4):
    target_bytes = 150
    print(f"Sending {count} packets at {target_bytes} bytes each...")
    
    for i in range(1, count + 1):
        # Create the header
        header = f"Packet {i}/100 "
        
        # Calculate how much padding is needed to reach 200 bytes
        padding_needed = target_bytes - len(header)
        padding = "X" * padding_needed
        
        message = header + padding
        
        try:
            # Verify length before sending
            print(f"Sending Packet {i} (Length: {len(message.encode('utf-8'))} bytes)")
            interface.sendText(message)
            time.sleep(delay)
            
        except Exception as e:
            print(f"Error sending packet {i}: {e}")
            break

    print("Test complete.")
    interface.close()

if __name__ == "__main__":
    send_test_packets(count=100, delay=4)