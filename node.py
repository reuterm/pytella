import socket
import threading
import struct
import binascii
import sys
from p2p import parseReceivedMessage, createMessage, ipToNum

# =============================================================================
# Script for creating a node for the P2P network. Connects to 130.233.195.30
# by default.
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
                                          org_port=socket.getsockname()[1],
                                          org_ip=socket.getsockname()[0]))
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
                                          org_port=socket.getsockname()[1],
                                          org_ip=socket.getsockname()[0],
                                          payload=data))
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
                print("Neighbours:")
                print(neighbours)
            if (header[6], socket) in connections:
                connections.remove((header[6], socket))

        elif header[2] == MSG_JOIN:
            if not (header[6], header[4]) in neighbours:
                neighbours.append((header[6], header[4]))
                print("Neighbours:")
                print(neighbours)
            data = bytearray()
            data.append(0x02)
            data.append(0x00)
            print("Respond with JOIN OK")
            socket.send(createMessage(msg_type=MSG_JOIN,
                                      org_port=socket.getsockname()[1],
                                      org_ip=socket.getsockname()[0],
                                      payload=data))
        elif header[2] == MSG_QUERY:
            # Check if key is known
            if payload[0] in keys:
                data = struct.pack('>HHHH4s', 1, 0, 1, 0,
                                   binascii.unhexlify(keys[payload[0]]))
                print("Respond with QUERY HIT")
                socket.send(createMessage(msg_type=MSG_QHIT,
                                          org_port=socket.getsockname()[1],
                                          org_ip=socket.getsockname()[0],
                                          payload=data, msg_id=header[7]))
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


def handshake(socket):
    socket.send(createMessage(msg_type=MSG_JOIN,
                              org_ip=socket.getsockname()[0]))
    response = socket.recv(1024)
    header, payload = parseReceivedMessage(response)
    # Join was successful
    if payload == ('0200'):
        global neighbours
        neighbours.append((header[6], header[4]))
        # Send PING type b to expand neighbourhood
        socket.send(createMessage(ttl=5, org_port=socket.getsockname()[1],
                                  org_ip=socket.getsockname()[0]))
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


# Initialize connection before starting to reply
def p2p_initiation(socket):
    handshake(socket)
    p2p_replying(socket)


# Server sock listening on the given port.
def make_server_socket(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((socket.gethostname(), port))
    print("Can be reached at "+socket.gethostbyname(socket.gethostname()) +
          " port "+str(port))
    s.listen(5)
    return s


# Connect to existing network
def bootstrap(ip, port):
    global connections
    bootstrap = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    bootstrap.connect((ip, port))
    connections.append((ip, bootstrap))
    source = threading.Thread(target=p2p_initiation, args=[bootstrap])
    source.start()

s = make_server_socket(6346)
try:
    bootstrap(str(sys.argv[1]), int(sys.argv[2]))
except:
    print("####################################################")
    print("Node not connected to existing network. Use")
    print("\'node.py <host-ip> <host-port>\' in order to do so.")
    print("####################################################")
while 1:
    (cl, address) = s.accept()
    connections.append((address[0], cl))
    print("accepted")
    ct = threading.Thread(target=p2p_replying, args=[cl])
    ct.start()
