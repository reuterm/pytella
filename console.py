import sys
from p2p import MsgTypes
from p2p import P2PConnection
import socket


# =============================================================================
# Simple console program that makes it easy to use our p2p network.
# =============================================================================
def main():
    # initialize p2p connection with default values
    port = 6346
    msg_types = MsgTypes()
    # my ip connect 192.168.56.1 6346
    p2p = P2PConnection(port, socket.gethostbyname(socket.gethostname()))
#    p2p.start_connection()
    while(True):
        console_input = str(raw_input('node$ ')).split()
        print(console_input)
        if str(console_input[0]) == 'c':
            if len(console_input) == 3:
                p2p.host = str(console_input[1])
                p2p.org_port = int(console_input[2])
                p2p.start_connection()
            else:
                print("Staring connection with default values. Use following" +
                      " syntax for custom values: connect [host] [port] ")
                p2p.start_connection()
        elif str(console_input[0]) == 'join':
            p2p.send_message(p2p.createMessage(
                msg_type=msg_types.get_MSG_JOIN(), payload=""))
            p2p.receive_message()
        elif str(console_input[0]) == 'query':  # example: vm3testkey
            if len(console_input) == 2:
                message = p2p.createMessage(
                    msg_type=msg_types.get_MSG_QUERY(),
                    payload=str(console_input[1]), ttl=3)
                print(p2p.parseReceivedMessage(message))
                p2p.send_message(message)
                p2p.receive_message()
            else:
                print("Use following syntax: query [payload]")
        elif str(console_input[0]) == 'ping':
            p2p.send_message(p2p.createMessage(ttl=3))
            p2p.receive_message()
        elif str(console_input[0]) == 'bye':
            print("Closing connection")
            p2p.send_message(p2p.createMessage(
                msg_type=msg_types.get_MSG_BYE()))
            p2p.close_connection()
            print("Closed")
        elif str(console_input[0]) == 'q':
            p2p.close_connection()
            sys.exit(0)
        else:
            print('Wrong input!')

main()
