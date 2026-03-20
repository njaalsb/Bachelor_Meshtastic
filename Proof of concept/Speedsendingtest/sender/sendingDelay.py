import meshtastic
import meshtastic.serial_interface
import time


interface = meshtastic.serial_interface.SerialInterface(devPath='/dev/ttyACM0')

def send_test_packets(count=100, delay=5):
    print(f"Sending {count} packets...")
    
    for i in range(1, count + 1):
        message = f"Test Packet {i}/100"
        
        try:
            print(f"Sending: {message}")
            interface.sendText(message)
            
            time.sleep(delay)
            
        except Exception as e:
            print(f"Error sending packet {i}: {e}")
            break

    print("Test complete.")
    interface.close()

if __name__ == "__main__":
    send_test_packets(count=100, delay=5)