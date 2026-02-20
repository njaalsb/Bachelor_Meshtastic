from meshtastic import mesh_pb2, portnums_pb2
import meshtastic

iface = meshtastic.SerialInterface()

msg = "<event version='2.0' uid='python-script' type='a-f-G-U-C' how='m-g'>" \
      "<point lat='53.4264' lon='10.4109' ce='9999999' le='9999999'/>" \
      "</event>"

iface.sendText(msg, portNum=portnums_pb2.PortNum.TAK_COT)