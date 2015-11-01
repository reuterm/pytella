import socket
import struct
import binascii
from hashlib import md5
import time

MSG_PING = 0x00
MSG_PONG = 0x01
MSG_BYE = 0x02
MSG_JOIN = 0x03
MSG_QUERY = 0x80
MSG_QHIT = 0x81

sequence_nr = 0


# ===========================================================================
# Protocol header:
# 0                         16                        32
# +------------+------------+------------+------------+
# |   Version  |    TTL     |  Msg Type  |  Reserved  |
# +------------+------------+------------+------------+
# |        Sender Port      |      Payload length     |
# +------------+------------+------------+------------+
# |             Original Sender IP Address            |
# +------------+------------+------------+------------+
# |                     Message ID                    |
# +------------+------------+------------+------------+
# ===========================================================================

# =============================================================================
# Implements helpful functionality to send and receive
# messages between nodes in peer to peer network.
# =============================================================================
def createMessage(msg_type=MSG_PING, ttl=1,
                  org_port=6346, payload="", msg_id="", org_ip=""):
    if msg_type == MSG_PING:
        print ("Creating message: PING")
        return construct_header(ttl=ttl, org_port=org_port, org_ip=org_ip,
                                length=0)
    elif msg_type == MSG_PONG:
        print ("Creating message: PONG")
        header = construct_header(msg_type=msg_type, ttl=ttl,
                                  org_port=org_port, org_ip=org_ip,
                                  length=len(payload))
        return header+payload
    elif msg_type == MSG_BYE:
        print ("Creating message: BYE")
        return construct_header(msg_type=msg_type, org_port=org_port,
                                org_ip=org_ip)
    elif msg_type == MSG_JOIN:
        print ("Creating message: JOIN")
        header = construct_header(msg_type=msg_type, org_port=org_port,
                                  org_ip=org_ip, length=len(payload))
        return header+payload
    elif msg_type == MSG_QUERY:
        print ("Creating message: QUERY")
        header = construct_header(msg_type=msg_type, ttl=ttl,
                                  org_port=org_port, msg_id=msg_id,
                                  length=len(payload), org_ip=org_ip)
        return header+payload
    elif msg_type == MSG_QHIT:
        print ("Creating message: QHIT")
        header = construct_header(msg_type=msg_type, ttl=ttl,
                                  org_port=org_port, length=len(payload),
                                  msg_id=msg_id, org_ip=org_ip)
        return header+payload
    else:
        return -1


def construct_header(ttl=1, msg_type=MSG_PING,
                     org_port=6346, org_ip="", length=0, msg_id=""):
    # Gnutella protocol header fields
    version = 1
    reserved = 0
    # Convert IP address of sender as single number
    if org_ip == "":
        org_ip = ipToNum(socket.gethostbyname(socket.gethostname()))
    else:
        org_ip = ipToNum(org_ip)
    if msg_id == "":
        # Create msg_id
        global sequence_nr
        sequence_nr += 1
        digest_builder = md5()
        digest_builder.update(str(org_ip) + str(org_port) + str(time.time())
                              + str(sequence_nr))  # test.encode('utf-8'))
        msg_id = digest_builder.digest()
    else:
        msg_id = binascii.unhexlify(msg_id)
    # For struct format see: https://docs.python.org/2/library/struct.html
    return struct.pack('!BBBBHHI4s', version, ttl, msg_type, reserved,
                       org_port, length, org_ip, msg_id)


def parseReceivedMessage(message):
    try:
        header_raw = struct.unpack('!BBBBHHI4s', message[:16])
    except:
        print("Unnable to unpack struct!")
        return ()

    # Convert single number into IP address of sender
    ip_addr = numToIP(header_raw[6])
    header = (header_raw[0], header_raw[1], header_raw[2], header_raw[3],
              header_raw[4], header_raw[5], ip_addr,
              binascii.hexlify(header_raw[7]))
    payload = ()

    # Return tuple (header, payload)
    # PING and PONG are handled the same way
    if header[2] == MSG_PING:
        # No payload to look at
        pass
    elif header[2] == MSG_PONG:
        if len(message) > 16:
            # Obtain number of entries in payload
            payload = struct.unpack('>H', message[16:18])
            # tmp for iterating
            tmp = 20
            for i in range(0, payload[0]):
                payload_raw = struct.unpack('>IHH', message[tmp:tmp+8])
                # Convert single number into IP address
                ip_addr = numToIP(payload_raw[0])
                payload += ((ip_addr, payload_raw[1]),)
                tmp += 8
    elif header[2] == MSG_JOIN:
        if len(message) > 16:
            payload = binascii.hexlify(message[16:])
    elif header[2] == MSG_QUERY:
            # Find out how long payload is
            length = len(message)-16
            payload = struct.unpack('>'+str(length)+'s', message[16:])
    elif header[2] == MSG_QHIT:
        if len(message) > 16:
            # Obtain number of entries in payload
            payload = struct.unpack('>H', message[16:18])
            # tmp for iterating
            tmp = 20
            for i in range(0, payload[0]):
                payload_raw = struct.unpack('>HH4s', message[tmp:tmp+8])
                payload += ((payload_raw[0],
                             binascii.hexlify(payload_raw[2])),)
                tmp += 8
    elif header[2] == MSG_BYE:
        # No payload to look at
        pass
    else:
        print('Message does not match protocol specification.')
        return -1
    return (header, payload)


# Convert IP address of sender as single number
def ipToNum(ip_addr):
    return struct.unpack('>L', socket.inet_aton(ip_addr))[0]


# Convert number back to IP address
def numToIP(num):
    return socket.inet_ntoa(struct.pack('>L', num))
