import meshtastic
import meshtastic.serial_interface
import time

interface = meshtastic.serial_interface.SerialInterface(devPath='/dev/ttyACM0')
interface2 = meshtastic.serial_interface.SerialInterface(devPath='/dev/ttyACM1')


def send_test_packets(count=50, delay=2):
    target_bytes = 231
    print(f"Sending {count} packets at {target_bytes} bytes each...")
    
    for i in range(1, count + 1):
        # Create the header
        header = f"Packet {i}/100 "
        
        
  
        length_needed = target_bytes - len(header)
        length = "X" * length_needed
        
        message = header + length
        
        try:
  
            print(f"Sending Packet {i} (Length: {len(message.encode('utf-8'))} bytes)")
            interface.sendText(message, wantAck=False)
            time.sleep(delay)
            interface2.sendText(message, wantAck=False)
            time.sleep(delay)
            
        except Exception as e:
            print(f"Error sending packet {i}: {e}")
            break

    print("Test complete.")
    interface.close()
    interface2.close()

if __name__ == "__main__":
    send_test_packets(count=100, delay=3)