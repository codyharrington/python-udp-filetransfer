"""
@title client.py
@author Josephine Lim
@description Client for file transfer program (COSC 364)

Summary of packet types:
1 = 0b0001 = read request = \x00\x00\x00\x01
2 = 0b0010 = read response = \x00\x00\x00\x02
4 = 0b0100 = open request = \x00\x00\x00\x04
8 = 0b1000 = open response = \x00\x00\x00\x08
9 = 0b1001 = close request = \x00\x00\x00\x09
"""

from socket import *
import sys
import select
import struct
import random

class Client(object):

    NUM_BYTES_TO_READ = 1400 #Total bytes sent inc header will be <1500 to prevent fragmentation over Ethernet links
    epoch_no = 0
    handle_no = 0
    
    def __init__(self):
        """Sets up UDP socket, obtains 5 values at command line:
        Filename to be read from server
        Filename under which received file is to be stored locally
        IP address or hostname of server (localhost if client is run on same machine)
        Port number of server
	Probability of packet loss, p
	"""
        self.client_socket = socket(AF_INET, SOCK_DGRAM)
	# Value for number of bytes socket can receive. ( For best match with hardware and network realities, 
	# the value should be a relatively small power of 2, for example, 4096)
	self.buffer_ = 2048 
	
	self.file_read = self.get_file_read_arg()
	self.local_filename = self.get_local_filename_arg()
	self.ip = self.get_ip_arg()
	self.port = self.get_port_arg()
	self.p = self.get_p_arg()
	self.address = (self.ip, self.port)
	
	# Create file on local system with name provided, to write our received file to
	self.file_write = open(self.local_filename, 'wb')
	self.eof = False

    def get_file_read_arg(self):
	"""Gets the name of the file to receive from the command line.
	Throws an error if it is empty or more than 100 characters."""
	try:
	    arg = sys.argv[1]
	    file_read = str(arg)
	except IndexError:
	    print "Please provide the name of the file that you wish to receive."
	    sys.exit("Example usage:\n\nclient.py myfile.txt receivedfile.txt 127.0.0.1 6060 0.0")    
	if (len(file_read) > 100):
	    print "Name of file must be equal to or less than 100 characters."
	    sys.exit("Example usage:\n\nclient.py myfile.txt receivedfile.txt 127.0.0.1 6060 0.0")
	else:
	    return file_read
	
    def get_local_filename_arg(self):
	"""Gets the name under which received file is to be stored locally, from the command line.
	Throws an error if it is empty."""
	try:
	    arg = sys.argv[2]
	    local_filename = str(arg)    
	except IndexError:
	    print "Please provide the name under which the received file is to be stored locally."
	    sys.exit("Example usage:\n\nclient.py myfile.txt receivedfile.txt 127.0.0.1 6060 0.0")
	else:
	    return local_filename
	
    def get_ip_arg(self):
	"""Gets the ip number or hostname of the server from the command line.
	Throws an error if it is empty."""   
	try:
	    arg = sys.argv[3]
	    ip = str(arg)	    
	except IndexError:
	    print "The IP address or hostname of the server must be provided."
	    sys.exit("Example usage:\n\nclient.py myfile.txt receivedfile.txt 127.0.0.1 6060 0.0")
	else:
	    return ip
    
    def get_port_arg(self):
	"""Gets the port number of the server from the command line.
	Throws an error if it is empty, not an integer, or not in the range of 1024 - 60000."""
	try:
	    arg = sys.argv[4]
	    port = int(arg)    
	except ValueError:
	    print "Port must be a number only."
	    sys.exit("Example usage:\n\nclient.py myfile.txt receivedfile.txt 127.0.0.1 6060 0.0")	    
	except IndexError:
	    print "Port number must be provided."
	    sys.exit("Example usage:\n\nclient.py myfile.txt receivedfile.txt 127.0.0.1 6060 0.0")	    
	if any([port < 1024, port > 60000]):
	    print "Port must be between 1024 and 60000"
	    sys.exit("Example usage:\n\nclient.py myfile.txt receivedfile.txt 127.0.0.1 6060 0.0")	    
	else:
	    return port
    
    def get_p_arg(self):
	"""Gets the probability of packet loss, p, from the command line.
	Throws an error if it is empty, or not a float in the range of 0.0 - 1.0."""
	try:
	    arg = sys.argv[5]
	    p = float(arg)    
	except IndexError:
	    print "The probability of packet loss, p, must be provided."
	    sys.exit("Example usage:\n\nclient.py myfile.txt receivedfile.txt 127.0.0.1 6060 0.0")   
	if (p < 0.0 or p > 1.0):
	    print "p value must be between 0.0 and 1.0 inclusive."
	    sys.exit("Example usage:\n\nclient.py myfile.txt receivedfile.txt 127.0.0.1 6060 0.0")	
	else:
	    return p
	
    def recv_invalid_response(self, recv_data, invalid_type = ""):
	"""When bit signature is invalid or wrong packet type is received, 
	discard packet and print error message."""	
	if (invalid_type == "bit_signature"):
	    print("Error: Packet received from outside our network (wrong bit signature)")	    
	    recv_data = ""	    
	elif (invalid_type == "response_type"):
	    print("Error: Wrong response type in packet received.")	    
	    recv_data = ""	   	
	return
    
  
    def send_open_request(self):
        """Sends an open-request packet to the server in binary.
	Format of packet is:
	4 bytes - bit signature - 0b1101
	4 bytes - open request type - 0b0100
	100 bytes - filename to be read as ASCII string
	"""
	print "Sending open request for file named ", self.file_read
	send_data = struct.pack("!2I100s", 0b1101, 0b0100, self.file_read)
	self.client_socket.sendto(send_data, self.address)
	return
    
    def recv_open_response(self, recv_payload):
        """When client receives an (already-validated) open-response packet from the server, 
	it unpacks the payload and saves the received fields as instance variables if file found."""

	unpacked_payload = struct.unpack("!?Q2I", recv_payload)
        # Read status field. If set to False, ignore remaining fields and 
	# generate error msg (file not found) before exiting. 
	# Each unpacked value is a tuple, so [0] accesses the value that we want
	status = unpacked_payload[0:1][0]
	if status == False:
	    print "Error: File not found."
	    sys.exit()
	
	#If set to True, read remaining fields.
	elif status == True:
	    print("File found.")
	    self.file_length = unpacked_payload[1:2][0]
	    self.epoch_no = unpacked_payload[2:3][0]
	    self.handle_no = unpacked_payload[3:][0]	    	    
	return
    
    def send_read_request(self, start_position):
        """Sends a read request packet to the server in binary.
	Format of packet is:
	4 bytes - bit signature - 0b1101
	4 bytes - read request type - 0b0001
	4 bytes - epoch number - provided by server in open response
	4 bytes - handle number - provided by server in open response
	4 bytes - start position of the block to be read from the file - incremented sequentially
	4 bytes - number of bytes to read - 1400
	"""
	send_data = struct.pack("!6I", 0b1101, 0b0001, self.epoch_no, self.handle_no, start_position, self.NUM_BYTES_TO_READ)
	self.client_socket.sendto(send_data, self.address)	
	return
    
    def recv_read_response(self, recv_payload):
        """When client receives an (already-validated) read-response packet from the server, it unpacks payload,
	checks that epoch number and handle number are correct and status field is 'OK',
	and appends file data received to the local file at the given start position."""       
	#Only unpack the headers because we want to store the file data as binary
	unpacked_payload = struct.unpack('!H3IQ', recv_payload[:22])
	status = unpacked_payload[0:1][0]
	epoch_no = unpacked_payload[1:2][0]
	handle_no = unpacked_payload[2:3][0]	
	
	#Check that file handle is the same, to make sure it is the same file request.
	if (self.epoch_no == epoch_no and self.handle_no == handle_no):
	    start_position = unpacked_payload[3:4][0]
	    num_bytes_been_read = unpacked_payload[4:5][0]    
	    # If we receive less bytes than the number we requested to read, this means that
	    # end of file has been reached
	    if (num_bytes_been_read < self.NUM_BYTES_TO_READ):
		self.eof = True
	    data_to_write = recv_payload[22:]	    
	    #If status field says that response contains real data: Append to file. Otherwise react 
	    #depending on error code received.
	    #Status 00 = OK
	    #Status 01 = Epoch no. of file handle doesnt match epoch no. of current invocation
	    #Status 10 = No context found for file-handle and no data has been read
	    #Status 11 = Context could be found but start position out of range
	    if (status == 0b00):
		self.file_append.seek(start_position)
		self.file_append.write(data_to_write)
	    elif (status == 0b01):
		print("Error: Epoch no. of file handle doesnt match epoch no. of current invocation")
		sys.exit()
	    elif (status == 0b10):
		print("Error: No context found for file-handle and no data has been read")
		sys.exit()
	    elif(status == 0b11):
		print("Error: Context could be found but start position out of range")
		sys.exit()
	else:
	    print("Error: File handle does not match file handle stored in client. Wrong file received.")
	    sys.exit() 	    
	#Then return control to read_service_loop() method so that next iteration of send_read_request 
	#from new start position is called.
        return
    
       
    def send_close_request(self):
        """Sends a close request packet to the server to close the file object.
	Format of packet is:
	4 bytes - bit signature - 0b1101
	4 bytes - close request type - 0b1001
	4 bytes - epoch number
	4 bytes - handle number
	"""
	data = struct.pack("!4I", 0b1101, 0b1001, self.epoch_no, self.handle_no)
	self.client_socket.sendto(data, self.address)
	self.client_socket.close()	
        return
    
    def open_service_loop(self):
	"""Loop that governs the timing and retransmission of open request packets,
	then checks packets received for the bit signature and response type fields to ensure that they are correct."""
	
	print "Attempting to receive file", self.file_read, "from", self.ip, "at port", self.port, "." 
	recv_data = None
	num_retransmits = 0
	#Start timer, retransmit after each timeout of one second. If receive response within the timer, move on to next step. 
	#Limit number of retransmits to 60 so as not to enter infinite loop.
	while(num_retransmits < 60):
	    num_retransmits += 1
	    self.send_open_request()

	    input_socket = [self.client_socket]
	    inputready,outputready,exceptready = select.select(input_socket,[],[], 1)
	    #if timer expires without input becoming ready, empty list is returned. So go to next iteration of loop (retransmit)
	    if (inputready == []):
		continue
	    else:
		try:
		    recv_data = self.client_socket.recv(self.buffer_)
		except Exception as exception_:
		    print("Wrong port number or IP address provided, or server is not available at the moment.")
		    sys.exit()
		print("Received a packet.")
		
		#Generate a random number between 0 and 1 with uniform distribution to simulate packet loss.
		if (random.uniform(0,1) < self.p):
		    recv_data = None
		    print("Packet dropped randomly to simulate packet losses")
		    continue
		
		bit_signature = recv_data[0:4]
		response_type = recv_data[4:8]
		recv_payload = recv_data[8:]

		#Check that bit signature is valid (packet is from our network)
		if bit_signature != "\x00\x00\x00\r": 
		    recv_invalid_response(recv_data, "bit_signature")
		    continue
		else:
		    #We have only ever sent a open_request, so the only viable response at this point is an open_response. 
		    #If this field contains anything else, it is an invalid packet. Retransmit request.
		    if response_type != "\x00\x00\x00\x08": 
			self.recv_invalid_response(recv_data, "response_type")
			continue		
		    else:
			#Bit signature and response type fields are both valid.
			print("Received open response from server...")
			self.recv_open_response(recv_payload)
			break
	
	if (num_retransmits >= 60):
	    print ("Exceeded number of retransmissions allowed. Exiting program.")
	    sys.exit()	
	return
    
    def read_service_loop(self):
	"""Loop that governs the timing and retransmission of read request packets,
	then checks packets received for the bit signature and response type fields to ensure that they are correct."""
	
	#Increment start_position each time packet sent, send a read request packet for each new position.
	#Expect to receive a read_response packet for each time read request sent.
	recv_data = None
	print("Sending request to server to read and receive file...")
	start_position = 0
	while(self.eof == False):
	    print("Reading from byte " + str(start_position))	    
	    num_retransmits = 0    
	    #Loop for retransmissions of the same start position
	    while(num_retransmits < 60):
		num_retransmits = num_retransmits + 1
		self.send_read_request(start_position)
		input_socket = [self.client_socket]
		inputready,outputready,exceptready = select.select(input_socket,[],[], 1)		
		if (inputready == []):
		    continue		
		else:
		    recv_data = self.client_socket.recv(self.buffer_)		    
		    if (random.uniform(0,1) < self.p):
			recv_data = None
			print("Packet dropped randomly to simulate packet losses")
			continue		    
		    bit_signature = recv_data[0:4]
		    response_type = recv_data[4:8]
		    recv_payload = recv_data[8:]	    
		    if bit_signature != "\x00\x00\x00\r":
			self.recv_invalid_response(recv_data, "bit_signature")
			continue
		    else:
			if response_type == "\x00\x00\x00\x02":
			    #Packet is valid, proceed to recv_read_response to append this bit of file received into local_filename
			    self.file_append = open(self.local_filename, 'r+b')
			    self.recv_read_response(recv_payload)
			    break
			else:
			    self.recv_invalid_response(recv_data, "response_type")
			    continue
		
	    start_position = start_position + self.NUM_BYTES_TO_READ		
	    if (num_retransmits >= 60):
		print ("Exceeded number of retransmissions allowed. Exiting program.")
		sys.exit()	    		
	return

client = Client()
client.open_service_loop()
client.read_service_loop()
client.send_close_request()
print ("File received successfully. Program will now exit.")
sys.exit()
