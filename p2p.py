import socket
import struct
import binascii
import time
from hashlib import md5
import select

# ===========================================================================
# The Header definition of our Protocol
# uint8_t     version; #version always one. Any message with other version
# values MUST be discarded.
# uint8_t     ttl; #MUST be greater than zero and be less than or equal to
# five.
# uint8_t     msg_type;
# uint8_t     reserved; #Set to zero. Unused in this version.
# /* the listening port of the original sender */
# uint16_t    org_port;
# /* the length of message body */
# uint16_t    length;
# /* the ip address of the original sender */
# uint32_t    org_ip;
# uint32_t    msg_id;
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
# MsgTypes class makes it easier to handle different constant message types
# =============================================================================
class MsgTypes:
    def __init__(self):
        self.MSG_PING = 0x00
        self.MSG_PONG = 0x01
        self.MSG_BYE = 0x02
        self.MSG_JOIN = 0x03
        self.MSG_QUERY = 0x80
        self.MSG_QHIT = 0x81

    def get_MSG_PING(self):
        return self.MSG_PING

    def get_MSG_PONG(self):
        return self.MSG_PONG

    def get_MSG_BYE(self):
        return self.MSG_BYE

    def get_MSG_JOIN(self):
        return self.MSG_JOIN

    def get_MSG_QUERY(self):
        return self.MSG_QUERY

    def get_MSG_QHIT(self):
        return self.MSG_QHIT

    def get_name(self, n):
        if n == 0:
            return "MSG_PING"
        if n == 1:
            return "MSG_PONG"
        if n == 2:
            return "MSG_BYE"
        if n == 3:
            return "MSG_JOIN"
        if n == 80:
            return "MSG_QUERY"
        if n == 81:
            return "MSG_QHIT"


# =============================================================================
# P2PConnection class implements helpful functionality to send and receive
# messages between nodes in peer to peer network.
# =============================================================================
class P2PConnection:
    def __init__(self, port, connection_to_host):
        self.org_port = port
        self.host = connection_to_host
        self.p2p_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.msg_types = MsgTypes()
        self.sequence_nr = 0
        # List of known neighbours
        self.neighbours = []
        # Distionary with key-value pairs
        self.keys = {'ourtestkey': '12345678'}

    def start_connection(self):
        try:
            self.p2p_socket.connect((str(self.host), self.org_port))
            print ("Connected to " + str(self.host) + " with port : " +
                   str(self.org_port))
        except:
            print("Connection failed or it is already connected!")

    def send_message(self, message):
        self.p2p_socket.send(message)

    def createMessage(self, msg_type=MsgTypes().get_MSG_PING(), ttl=1,
                      org_port=6346, payload=""):
        if msg_type == self.msg_types.get_MSG_PING():
            print ("Creating message: PING")
            return self.construct_header(ttl=ttl, org_port=org_port, length=0)
        elif msg_type == self.msg_types.get_MSG_PONG():
            print ("Creating message: PONG")
            header = self.construct_header(msg_type=msg_type, ttl=ttl,
                                           org_port=org_port,
                                           length=len(payload))
            return header+payload
        elif msg_type == self.msg_types.get_MSG_BYE():
            print ("Creating message: BYE")
            return self.construct_header(msg_type=msg_type, org_port=org_port)
        elif msg_type == self.msg_types.get_MSG_JOIN():
            print ("Creating message: JOIN")
            header = self.construct_header(msg_type=msg_type,
                                           org_port=org_port,
                                           length=len(payload))
            return header+payload
        elif msg_type == self.msg_types.get_MSG_QUERY():
            print ("Creating message: QUERY")
            header = self.construct_header(msg_type=msg_type, ttl=ttl,
                                           org_port=org_port,
                                           length=len(payload))
            return header+payload
        elif msg_type == self.msg_types.get_MSG_QHIT():
            print ("Creating message: QHIT")
            header = self.construct_header(msg_type=msg_type, ttl=ttl,
                                           org_port=org_port,
                                           length=len(payload))
            return header+payload
        else:
            return -1

    def construct_header(self, ttl=1, msg_type=MsgTypes().get_MSG_PING(),
                         org_port=6346, length=0):
        # Gnutella protocol header fields
        version = 1
        reserved = 0
        # Convert IP address of sender as single number
        # org_ip = self.ipToNum('192.168.56.1')
        org_ip = self.ipToNum(socket.gethostbyname(socket.gethostname()))
        # Create msg_id
        self.sequence_nr += 1
        digest_builder = md5()
        digest_builder.update(str(org_ip) + str(org_port) + str(time.time())
                              + str(self.sequence_nr))  # test.encode('utf-8'))
        msg_id = digest_builder.digest()

        # For struct format see: https://docs.python.org/2/library/struct.html
        return struct.pack('!BBBBHHI4s', version, ttl, msg_type, reserved,
                           org_port, length, org_ip, msg_id)

    def receive_message(self):
        ready = select.select([self.p2p_socket], [], [], 10.0)
        if ready[0]:
            print('Starting to receive')
            reply = self.p2p_socket.recv(4096)  # 4096
            print('Reply raw:')
            print(binascii.hexlify(reply))
            print('Reply parsed:')
            print(self.parseReceivedMessage(reply))
        else:
            print('Timeout!')

    def parseReceivedMessage(self, message):
        try:
            header_raw = struct.unpack('!BBBBHHI4s', message[:16])
        except:
            print("Unnable to unpack struct!")
            return ()

        # Convert single number into IP address of sender
        ip_addr = self.numToIP(header_raw[6])
        header = (header_raw[0], header_raw[1], header_raw[2], header_raw[3],
                  header_raw[4], header_raw[5], ip_addr,
                  binascii.hexlify(header_raw[7]))
        payload = ()

        # Return tuple (header, payload)
        # PING and PONG are handled the same way
        if header[2] == self.msg_types.get_MSG_PING():
            # No payload to look at
            pass
        elif header[2] == self.msg_types.get_MSG_PONG():
            if len(message) > 16:
                # Obtain number of entries in payload
                payload = struct.unpack('>H', message[16:18])
                # tmp for iterating
                tmp = 20
                for i in range(0, payload[0]):
                    payload_raw = struct.unpack('>IHH', message[tmp:tmp+8])
                    # Convert single number into IP address
                    ip_addr = self.numToIP(payload_raw[0])
                    payload += ((ip_addr, payload_raw[1]),)
                    tmp += 8
        elif header[2] == self.msg_types.get_MSG_JOIN():
            if len(message) > 16:
                payload = binascii.hexlify(message[16:])
                # payload = struct.unpack('>H', message[16:18])
        elif header[2] == self.msg_types.get_MSG_QUERY():
                # Find out how long payload is
                length = len(message)-16
                payload = struct.unpack('>'+str(length)+'s', message[16:])
        elif header[2] == self.msg_types.get_MSG_QHIT():
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
        elif header[2] == self.msg_types.get_MSG_BYE():
            # No payload to look at
            pass
        else:
            print('Message does not match protocol specification.')
            return -1
        return (header, payload)

    # Convert IP address of sender as single number
    def ipToNum(self, ip_addr):
        return struct.unpack('>L', socket.inet_aton(ip_addr))[0]

    # Convert number back to IP address
    def numToIP(self, num):
        return socket.inet_ntoa(struct.pack('>L', num))

    def close_connection(self):
        self.p2p_socket.close()
        print("Connection closed")
