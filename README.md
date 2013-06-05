#python-udp-ftp
==========

This was an assignment for COSC364 back in 2012 which implements a simple UDP file transfer protocol
with retransmission. 

I wrote the server, Josephine Lim wrote the client.

#### server.py

Usage:
`
python server.py port p_err
`

Where 
* `port` is the port number to listen on
* `p_err` is the probability of a packet being deliberately dropped by the server, where 0 <= `p_err` <= 1

The server is blocking, so it will run, display the its IP address, and await a packet from the client.
Output is printed for each packet sent and received.

#### client.py

Usage:
`
python client.py srcfile destfile addr port p_err
`

Where 
* `srcfile` is the file to download from the server
* `destfile` is the file to save the downloaded file as locally
* `addr` is the address of the server
* `port` is the port to send data to the server on
* `p_err` is the probability of a packet being deliberately dropped by the client, where 0 <= `p_err` <= 1

The client will send a request to the server, which will initiate communication between the two.
As with the server, the client prints output for each packet sent and received.
