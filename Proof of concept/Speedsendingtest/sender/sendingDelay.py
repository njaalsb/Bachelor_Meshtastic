import meshtastic
import meshtastic.serial_interface
import time

interface = meshtastic.serial_interface.SerialInterface(devPath='/dev/ttyACM0')

def send_test_packets(count=100000, delay=6):
    target_bytes = 200
    print(f"Sending {count} packets at {target_bytes} bytes each...")
    
    for i in range(1, count + 1):
        # Create the header
        header = f"Packet {i}/100000 "
        
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
    send_test_packets(count=100000, delay=6)
import meshtastic
import meshtastic.serial_interface
import time

interface = meshtastic.serial_interface.SerialInterface(devPath='/dev/ttyACM1')

def send_test_packets(count=100000, delay=6, destinations=None):
    """
    Send test packets over Meshtastic.
    
    destinations: list of node IDs (e.g. ['!a1b2c3d4', '!e5f6a7b8']).
                  If empty or None, broadcasts to all.
    """
    if not destinations:
        destinations = [None]  # None tells sendText to broadcast

    target_bytes = 200
    print(f"Sending {count} packets at {target_bytes} bytes each...")
    if destinations == [None]:
        print("Mode: Broadcast")
    else:
        print(f"Mode: Direct to {destinations}")

    for i in range(1, count + 1):
        header = f"Packet {i}/100000 "
        padding_needed = target_bytes - len(header)
        padding = "X" * padding_needed
        message = header + padding

        for dest in destinations:
            try:
                dest_label = dest if dest else "broadcast"
                print(f"Sending Packet {i} to {dest_label} (Length: {len(message.encode('utf-8'))} bytes)")
                interface.sendText(message, destinationId=dest)
                time.sleep(delay)
            except Exception as e:
                print(f"Error sending packet {i} to {dest_label}: {e}")
                break

    print("Test complete.")
    interface.close()

if __name__ == "__main__":
    # Put node IDs here to send direct, or leave empty to broadcast
    node_ids = ['!451709d6']  # e.g. ['!a1b2c3d4', '!e5f6a7b8']

    send_test_packets(count=100000, delay=6, destinations=node_ids)
