import socket
import threading
import struct
import binascii
from hashlib import md5
import time

# =============================================================================
# Script for creating a node for the P2P network. Connects to 130.233.195.30
# =============================================================================

# List of known neighbours
neighbours = []
# Distionary with key-value pairs
keys = {'ourtestkey': '12345678'}
# List of connections
connections = []
# Sequence number for header
sequence_nr = 0
# List of query searches
q_searches = []

# Different message types in binary
MSG_PING = 0x00
MSG_PONG = 0x01
MSG_BYE = 0x02
MSG_JOIN = 0x03
MSG_QUERY = 0x80
MSG_QHIT = 0x81


# Determine what kind of message has been received and process it accordingly
def process_message(header, payload, socket):
    # Discard messages with invalid version or ttl
    global q_searches
    global connections
    global neighbours
    if (header[0] == 1 or header[1] < 1 or header[1] > 5):
        if header[2] == MSG_PING:
            # Type a
            if header[1] == 1:
                print("Respond with PONG A")
                socket.send(createMessage(msg_type=MSG_PONG,
                                          org_port=header[4]))
            # Type b
            else:
                tmp = list(neighbours)
                if (header[6], header[4]) in tmp:
                    tmp.remove((header[6], header[4]))
                response = tmp[:5]
                data = bytearray()
                if(len(response) > 0):
                    data.extend(struct.pack('>HH', len(response), 0))
                    for item in response:
                        data.extend(struct.pack('>IHH', ipToNum(item[0]),
                                                item[1], 0))
                print("Respond with PONG B")
                socket.send(createMessage(msg_type=MSG_PONG,
                                          org_port=header[4], payload=data))
        elif header[2] == MSG_PONG:
            # Pong type b
            if len(payload) > 0:
                # Iterate through payload
                for i in range(1, len(payload)):
                    # Add to neighbours if not already there
                    if not (payload[i][0], payload[i][1]) in neighbours:
                        neighbours.append((payload[i][0], payload[i][1]))
        elif header[2] == MSG_BYE:
            if (header[6], header[4]) in neighbours:
                neighbours.remove((header[6], header[4]))
                connections.remove(socket)
                print("Neighbours:")
                print(neighbours)
        elif header[2] == MSG_JOIN:
            if not (header[6], header[4]) in neighbours:
                neighbours.append((header[6], header[4]))
                print("Neighbours:")
                print(neighbours)
            data = bytearray()
            data.append(0x02)
            data.append(0x00)
            print("Respond with JOIN OK")
            socket.send(createMessage(msg_type=MSG_JOIN, org_port=header[4],
                                      payload=data))
        elif header[2] == MSG_QUERY:
            # Check if key is known
            if payload[0] in keys:
                data = struct.pack('>HHHH4s', 1, 0, 1, 0,
                                   binascii.unhexlify(keys[payload[0]]))
                print("Respond with QUERY HIT")
                socket.send(createMessage(msg_type=MSG_QHIT,
                                          org_port=header[4], payload=data,
                                          msg_id=header[7]))
            # Save search
            q_searches.append((header[6], header[7]))
            # Forward to other nodes
            forward(header, payload, socket)
        elif header[2] == MSG_QHIT:
            # Check if known message id
            for (x, y) in q_searches:
                if y == header[7]:
                    # Check if connection exists with given ip address
                    for (a, b) in connections:
                        if a == x:
                            data = bytearray()
                            data.extend(struct.pack('>HH', payload[0], 0))
                            for i in range(payload[0]):
                                data.extend(
                                    struct.pack('>HH4s', i+1, 0,
                                                binascii.unhexlify(
                                                    payload[1][i+1])))
                            b.send(createMessage(msg_type=MSG_QHIT,
                                                 org_port=header[4],
                                                 org_ip=header[6],
                                                 payload=data, msg_id=y))


# Forward messages to existing connections
def forward(header, payload, sock):

    global connections
    data = struct.pack('>'+str(len(payload[0]))+'s', payload[0])
    message = createMessage(msg_type=MSG_QUERY, ttl=header[1]-1,
                            org_port=header[4], org_ip=header[6],
                            msg_id=header[7], payload=data)

    for connection in connections:
        # Don't send it back to searching node
        if sock is not connection[1]:
            print("Forwarded Message parsed:")
            print(parseReceivedMessage(message))
            connection[1].send(message)


# Create binary data to be sent
def createMessage(msg_type=MSG_PING, ttl=1,
                  org_port=6346, payload="", msg_id="", org_ip=""):
    if msg_type == MSG_PING:
        print ("Creating message: PING")
        return construct_header(ttl=ttl, org_port=org_port, length=0)
    elif msg_type == MSG_PONG:
        print ("Creating message: PONG")
        header = construct_header(msg_type=msg_type, ttl=ttl,
                                  org_port=org_port,
                                  length=len(payload))
        return header+payload
    elif msg_type == MSG_BYE:
        print ("Creating message: BYE")
        return construct_header(msg_type=msg_type, org_port=org_port)
    elif msg_type == MSG_JOIN:
        print ("Creating message: JOIN")
        header = construct_header(msg_type=msg_type, org_port=org_port,
                                  length=len(payload))
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


def handshake(socket):
    socket.send(createMessage(msg_type=MSG_JOIN, payload=""))
    response = socket.recv(1024)
    header, payload = parseReceivedMessage(response)
    # Join was successful
    if payload == ('0200'):
        global neighbours
        neighbours.append((header[6], header[4]))
        # Send PING type b to expand neighbourhood
        socket.send(createMessage(ttl=5))
        response = socket.recv(1024)
        header, payload = parseReceivedMessage(response)
        if len(payload) > 0:
            # Iterate through payload
            for i in range(1, len(payload)):
                # Add to neighbours if not already there
                if not (payload[i][0], payload[i][1]) in neighbours:
                    neighbours.append((payload[i][0], payload[i][1]))
            print("Neighbours:")
            print(neighbours)


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


def p2p_replying(socket):

    connected = True
    while connected:
        message = socket.recv(1024)
        print("Message received:")
        print(binascii.hexlify(message))
        header, payload = parseReceivedMessage(message)
        print(header)
        print(payload)
        # Disconnect after BYE
        if(header[2] == MSG_BYE):
            connected = False
        process_message(header, payload, socket)

    socket.close()


def p2p_initiation(socket):

    # Initialize connection before starting to reply
    handshake(socket)
    p2p_replying(socket)


def make_server_socket(port):

    # Server sock listening on the given port.
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((socket.gethostname(), port))
    print("Can be reached at "+socket.gethostbyname(socket.gethostname()) +
          " port "+str(port))
    s.listen(5)
    return s


s = make_server_socket(6346)
# Connect to existing network
bootstrap = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
bootstrap.connect(('130.233.195.30', 6346))
connections.append(('130.233.195.30', bootstrap))
source = threading.Thread(target=p2p_initiation, args=[bootstrap])
source.start()
while 1:
    (cl, address) = s.accept()
    connections.append((address[0], cl))
    print("accepted")
    ct = threading.Thread(target=p2p_replying, args=[cl])
    ct.start()
