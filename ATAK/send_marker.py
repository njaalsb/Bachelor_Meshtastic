import time
import meshtastic.serial_interface
from meshtastic import mesh_pb2, portnums_pb2

import TAKMessage_pb2


def build_cot(lat, lon, uid="py-marker-1", cot_type="b-m-p"):
    t = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    stale = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + 300))

    cot = (
        f'<event version="2.0" uid="{uid}" type="{cot_type}" how="m-g" '
        f'time="{t}" start="{t}" stale="{stale}">'
        f'<point lat="{lat}" lon="{lon}" hae="0" ce="10" le="10"/>'
        f'</event>'
    )
    return cot.encode("utf-8")


def send_marker(lat, lon, cot_type="b-m-p"):
    iface = meshtastic.serial_interface.SerialInterface()

    cot_bytes = build_cot(lat, lon, cot_type=cot_type)

    # Build TAK payload
    payload = TAKMessage_pb2.TakPayload()
    payload.message = cot_bytes
    payload.type = 1  # 1 = CoT

    # Wrap in TakMessage
    msg = TAKMessage_pb2.TakMessage()
    msg.payload.CopyFrom(payload)

    # Wrap in Meshtastic Data packet
    data = mesh_pb2.Data()
    data.portnum = 256  # ATAK plugin port
    data.payload = msg.SerializeToString()

    iface.sendData(data)
    print("ATAK marker sent!")


if __name__ == "__main__":
    send_marker(63.4264, 10.4109, cot_type="b-m-p")