python-ftp
==========

This was an assignment for COSC364 back in 2012. I wrote the server, Josephine Lim wrote the client.

# To use the server

`
python server.py port p_err
`

Where 
* `port` is the port number to listen on
* `p_err` is the probability of a packet being deliberately dropped by the server, where 0 <= p_err <= 1

# To use the client

`
python client.py srcfile destfile addr port p_err
`

Where 
* `srcfile` is the file to download from the server
* `destfile` is the file to save the downloaded file as locally
* `addr` is the address of the server
* `port` is the port to connect to the server on
* `p_err` is the probability of a packet being deliberately dropped by the client, where 0 <= p_err <= 1
