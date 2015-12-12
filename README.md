# pytella
P2P node in Python (simplified Gnutella)

## Requirments
Make sure you to use Python version 2.7 for all the scripts.

## Usage
Run node.py with “python node.py <host-ip> <host-port>” to connect node to existing network. If run without specifying host ip and port the node is still able to run and accept other connections as well as responding to messages.
Start a console with “python console.py”.
Inside the console you can use different commands:
- c - connects to own node’s ip and with default port 6346.
- c [host] [port] - connects to given host and port. 
- join - send join message to connected node.
- ping - send ping message to the connected node.
- query [key] - send query with given key value.
- bye -  send bye message and close the socket connection.
- man - display commands.
- q - shutdown program.
