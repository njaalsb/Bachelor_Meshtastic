import time
import meshtastic.serial_interface


iface = meshtastic.serial_interface.SerialInterface()

def sending():
    max_payload = 230
    bytes_to_send = max_payload 
    payload = b'X' * bytes_to_send  
    for i in range(1, 101):
        print(f"Sender pakke {i} med payload størrelse {len(payload)}")
        iface.sendText(payload.decode('utf-8'), wantAck=False)
        time.sleep(0.2)  

if __name__ == "__main__":
    sending()