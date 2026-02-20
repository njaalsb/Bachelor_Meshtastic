from meshtastic.protobuf import mesh_pb2, config_pb2
from meshtastic import portnums_pb2
from meshtastic import BROADCAST_NUM
import meshtastic.serial_interface

interface = meshtastic.serial_interface.SerialInterface()

data = bytes("hello world", "utf-8")

def send_message(data):
    interface.sendData(
        data=data,
        destinationId=BROADCAST_NUM,
        portNum=meshtastic.portnums_pb2.PRIVATE_APP,
        wantAck=False,
        wantResponse=False
    )
    
send_message(data)
print(f"Message sent: {data}")

interface.close()
