import sys
import socket
import select
import binascii
from p2p import parseReceivedMessage, createMessage

MSG_PING = 0x00
MSG_PONG = 0x01
MSG_BYE = 0x02
MSG_JOIN = 0x03
MSG_QUERY = 0x80
MSG_QHIT = 0x81


# =============================================================================
# Simple console program that makes it easy to use our p2p network.
# =============================================================================
class p2pConsole:
    def __init__(self):
        # initialize p2p connection with default values
        self.port = 6346
        self.host = socket.gethostbyname(socket.gethostname())
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sequence_nr = 0
        self.org_port = 0
        self.org_ip = '0.0.0.0'

    def start_connection(self):
        try:
            self.sock.connect((str(self.host), self.port))
            self.org_ip = self.sock.getsockname()[0]
            self.org_port = self.sock.getsockname()[1]
            print ("Connected to " + str(self.host) + " with port : " +
                   str(self.org_port))
        except:
            print("Connection failed or it is already connected!")

    def close_connection(self):
        self.sock.close()
        print("Connection closed")

    def receive_message(self):
        ready = select.select([self.sock], [], [], 10.0)
        if ready[0]:
            print('Starting to receive')
            reply = self.sock.recv(4096)  # 4096
            print('Reply raw:')
            print(binascii.hexlify(reply))
            print('Reply parsed:')
            print(parseReceivedMessage(reply))
        else:
            print('Timeout!')


def main():
    app = p2pConsole()
    while(True):
        console_input = str(raw_input('node$ ')).split()
        if str(console_input[0]) == 'connect':
            if len(console_input) == 3:
                app.host = str(console_input[1])
                app.port = int(console_input[2])
                app.start_connection()
            else:
                print("Staring connection with default values. Use " +
                      "following syntax for custom values: connect " +
                      "[host] [port]")
                app.start_connection()
        elif str(console_input[0]) == 'join':
            app.sock.send(createMessage(
                msg_type=MSG_JOIN, payload="", org_port=app.org_port,
                org_ip=app.org_ip))
            app.receive_message()
        elif str(console_input[0]) == 'query':
            if len(console_input) == 2:
                message = createMessage(
                    msg_type=MSG_QUERY, ttl=3, org_port=app.org_port,
                    org_ip=app.org_ip, payload=str(console_input[1]))
                print(parseReceivedMessage(message))
                app.sock.send(message)
                app.receive_message()
            else:
                print("Use following syntax: query [payload]")
        elif str(console_input[0]) == 'ping':
            app.sock.send(createMessage(ttl=3, org_port=app.org_port,
                                        org_ip=app.org_ip))
            app.receive_message()
        elif str(console_input[0]) == 'bye':
            print("Closing connection")
            app.sock.send(createMessage(msg_type=MSG_BYE,
                                        org_port=app.org_port,
                                        org_ip=app.org_ip))
            app.close_connection()
            print("Closed")
        elif str(console_input[0]) == 'quit':
            app.close_connection()
            sys.exit(0)
        else:
            print('Wrong input!')


main()
