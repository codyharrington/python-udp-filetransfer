"""
@title server.py
@author Cody Harrington
@description Server program for COSC364. 
"""
from time import clock
from socket import *
import os
import sys
import struct # packs and unpacks values to/from literal bytes
import random

class Server(object):
    
    def __init__(self):
        """Start up the server"""
        # This must be the address that the server is running on
        self.ip = gethostbyname(gethostname()) # Change this as needed
        self.port, self.p_err = self.get_args()
        self.address = (self.ip, self.port)
        
        # Allocate the buffer
        self.buffer_ = 2048 # Change as needed
        self.udp_socket = self.init_socket()
        
        self.epoch_number = self.get_epoch_number();
        self.handle_number = 0
        
        self.context_record = {}
        
        self.listen()
        
    
    def get_args(self):
        """
        Gets the port number and packet error threshold value. from the command line.
        
        Usage:
        
        server.py port p_err
        
        Where port is a number between 1024 and 60000, and p_err is a float
        between 0 and 1.
        """
        try:
            port = int(sys.argv[1])
            p_err = float(sys.argv[2])
            
        except ValueError:
            print "Port must be a number only, and p_err must only be a float."
            sys.exit("Usage:\n\nserver.py port p_err\n\nWhere port is a number between 1024 and 60000,\n and p_err is a float between 0 and 1")
            
        except IndexError:
            print "A port number and an error probability value p_err must be provided."
            sys.exit("Usage:\n\nserver.py port p_err\n\nWhere port is a number between 1024 and 60000,\n and p_err is a float between 0 and 1")
            
        if any([port < 1024, port > 60000, p_err < 0, p_err > 1]):
            print "Port must be between 1024 and 60000, and p_err must be between 0 and 1"
            sys.exit("Usage:\n\nserver.py port p_err\n\nWhere port is a number between 1024 and 60000,\n and p_err is a float between 0 and 1")
            
        else:
            return port, p_err
            
    
    def init_socket(self):
        """Creates socket for use. Returns an active UDP socket."""
        udp_socket = socket(AF_INET, SOCK_DGRAM)
        
        udp_socket.bind(self.address)
        udp_socket.setblocking(True)
    
        return udp_socket
            
    
    def get_epoch_number(self):
        """
        Checks to see if file "epoch.number" exists. If it doesn't, then 
        epoch-number is set to 1, and stored in a file named "epoch.number"
        Otherwise, the first line is read for a single integer, which is stored 
        as the epoch number. This number is then incremented by 1, and is 
        written into the file over the old number.
        """
        if not os.path.isfile('epoch.number'):
            epoch_number = 1
            f = open('epoch.number', 'w')
            
        else:
            f = open('epoch.number', 'r+')
            f_string = f.readline()
            if f_string.isdigit():
                epoch_number = int(f_string)
                epoch_number += 1
                
            else:
                epoch_number = 1
                
            # Go back to the start of the file so it can be overwritten
            f.seek(0)
            
        f.write(str(epoch_number))
        f.close()
        print "Retrieved epoch number: %d" % epoch_number
        
        return epoch_number
    
            
    def send_open_response(self, packet, recv_addr):
        """
        Parses an open-request, then replies with an appropriate open-response.
        
        Receives: 
        file_name
        
        100 bytes
        100 chars
        
        struct.pack("!100s", field)
        
        Sends:
        Bit_signature packet_type status file_length epoch_number handle_number
        
        4bits + 4bits + 1 bit + 8 bits + 8 bits + 8 bits
        int + int + bool + longlong + long + long
        
        struct.pack('!2I?Q2L', sequence of fields)
        
        Note: ! denotes network byte order (big-endian).
        """
        print "Received open request from %s on port %d." % recv_addr
        
        # After the header data is stripped, only the file name f_name is left
        (f_name,) = struct.unpack('!100s', packet)
        f_name = f_name.replace('\x00', "").strip()
        
        try: 
            f_handle = open(f_name, "rb")
            print "Opened file:", f_name
            self.handle_number += 1
            # Store the handle number so it isn't affected when the original
            # is incremented.
            f_handle_no = self.handle_number
            f_size = os.path.getsize(f_name)
            ttl = 60
            init_time = clock()
            # Store the file handle in the context record
            self.context_record[f_handle_no] = (f_handle, init_time, ttl)
            self.update_context_record(f_handle_no)
            status = True
            
        # If there is ANY error, set the status bit to 0.
        except Exception as exception_:
            print "Open response error:", exception_
            status = False
            f_size = 0
            f_handle_no = 0
            
        print "Client %s given handle %d" % recv_addr, f_handle_no
        
        # Attach bit-signature and packet response type
        response_packet = struct.pack("!2I?Q2I", 0b1101, 0b1000, status, f_size, self.epoch_number, f_handle_no)
        self.udp_socket.sendto(response_packet, recv_addr)
        print "Sent open response."
        
    
    def send_read_response(self, packet, recv_addr):
        """
        Parses a read-request, then replies with an appropriate read-response.
        
        Receives:
        recv_epoch_number, recv_handle_number, read_start_pos, read_size
        
        ("!4I", sequence of fields)
        
        4bits + 4bits + 4 bits + 4bits
        int + int + int + int
        
        Sends:
        Bit_signature packet_type status epoch_number handle_number start_pos num_bytes_read bytes_read
        
        4bits + 4bits + 2 bits + 4 bits + 4 bits + 4 bits + 8 bits + variable
        int + int + short + int + int + int + longlong + variable
        
        struct.pack('!2IH3IQ', sequence of fields) + bytes_read
        
        Note: ! denotes network byte order (big-endian).
        
        """
        buff_size = 0
        read_buffer = 0
        
        print "Received read request from %s on port %d." % recv_addr
        (recv_epoch_number, recv_handle_number, read_start_pos, read_size) = struct.unpack("!4I", packet)
        
        # Returns False if f_handle doesn't exist in the context record
        f_handle = self.get_file_handle(recv_handle_number)
        
        if recv_epoch_number != self.epoch_number:
            print "Epoch numbers do not match: Server = %d, Client = %d" % (self.epoch_number, recv_epoch_number)
            status = 0b01
            
        elif not f_handle:
            print "Handle %d does not exist in context record." % recv_handle_number
            status = 0b10
            
        else:
            status = 0b00
            try:
                print "Read from file at byte %d" % read_start_pos
                f_handle.seek(read_start_pos)
                read_buffer = f_handle.read(read_size)
                buff_size = len(read_buffer)
                
            except Exception as exception_:
                print "Read response error:", exception_
                status = 0b11
                f_handle.close()
                
        response_header = struct.pack('!2IH3IQ', 0b1101, 0b0010, status, 
                                      self.epoch_number, recv_handle_number, 
                                      read_start_pos, buff_size)
        
        response_packet = response_header + read_buffer
        
        self.udp_socket.sendto(response_packet, recv_addr)
        print "Sent read response."
    
    
    def recv_close_request(self, packet, recv_addr):
        """
        Parses a close-request, then closes the file that was associated with
        that client.
      
        Receives:
        recv_epoch_number, recv_handle_number
      
        ("!2I", sequence of fields)
      
        4bits + 4bits
        int + int
      
        Note: ! denotes network byte order (big-endian).
        """
        print "Received close request from %s on port %d." % recv_addr
        (recv_epoch_number, recv_handle_number) = struct.unpack("!2I", packet)
        
        f_handle = self.get_file_handle(recv_handle_number)
        
        if recv_epoch_number != self.epoch_number:
            print "Close error:\nEpoch numbers do not match: Server = %d, Client = %d"
            return
        
        elif not f_handle:
            print "Close error: Handle %d does not exist in context record" % recv_handle_number
            return
        
        else:
            try:
                print "Closing file:", f_handle
                f_handle.close()
                
            except Exception as exception_:
                print "Close error:", exception_
            
        
    def recv_invalid_request(self, packet, recv_addr):
        """
        Prints a message informing of an invalid packet, and then drops the
        packet.
        """ 
        print "Received invalid request from %s on port %d" % recv_addr
        print "Packet data (%d bytes)\n---START---" % len(packet)
        print packet
        print "---END---"
        
        # Clear the packet
        packet = None
        
        print "Dropped packet."
        
    
    def update_context_record(self, handle_number):
        """
        The corresponding timeout value of the handle 'handle_number' is reset.
        
        The entire record is iterated through, and any records that are older 
        than their time_to_live value are deleted.
        """
        # Create an iterable list of items for the context record
        records = self.context_record.iteritems()
        expiry_list = []
        
        for key, (f_han, i_time, time_tl) in records:
            if (clock() - i_time) > time_tl:
                # If record has expired, add to list of records to be deleted
                print "Handle %d has timed out." % key
                expiry_list.append(key)
        
        # Update the TTL on the handle so it doesn't expire during transfer.       
        (f_han, i_time, time_tl) = self.context_record.get(handle_number)
        i_time = clock()
        self.context_record[handle_number] = (f_han, i_time, time_tl)
        
        # Delete expired items
        for key in expiry_list:
            print "Deleting handle %d." % key
            del self.context_record[key]

            
    def get_file_handle(self, handle_number):
        """
        Receives a handle number and fetches the corresponding handle from the 
        context record. If the handle doesn't exist, return False.
        """
        if self.context_record.has_key(handle_number):
            self.update_context_record(handle_number)
            (f_handle, init_time, ttl) = self.context_record[handle_number]
            return f_handle
        
        else:
            return False
        
        
    def parse_recv_data(self, packet_bytes, recv_addr):
        """
        Receives: 
        ("!2I", 0b1101, 0b1000) +  payload
        
        Header 
        4bits + 4bits
        int + int
        
        Where ! indicates network byte order
        
        When a packet is received, it is stripped of the header, and then the 
        payload is sent to the corresponding function to be processed, based on 
        the request_type field.
        
        The bit signature is 1101 = 13 = \x00\x00\x00\r
        
        Packet type values:
        1 = 0b0001 = read request = \x00\x00\x00\x01
        2 = 0b0010 = read response = \x00\x00\x00\x02
        4 = 0b0100 = open request = \x00\x00\x00\x04
        8 = 0b1000 = open response = \x00\x00\x00\x08
        9 = 0b1001 = close request = \x00\x00\x00\x09
        """
        bit_signature = packet_bytes[:4]
        request_type = packet_bytes[4:8]
        payload = packet_bytes[8:]
        
        # Bit signature of 13 to identify our packets
        if bit_signature != "\x00\x00\x00\r":
            self.recv_invalid_request(packet_bytes, recv_addr)
        else:
            if request_type == "\x00\x00\x00\x09": # Type 1001
                self.recv_close_request(payload, recv_addr)
            elif request_type == "\x00\x00\x00\x01": # Type 0001
                self.send_read_response(payload, recv_addr)
            elif request_type == "\x00\x00\x00\x04": # Type 0100
                self.send_open_response(payload, recv_addr)
            else:
                self.recv_invalid_request(packet_bytes, recv_addr)
                
        
    def listen(self):
        """
        Enters into an infinite loop and listens on the specified UDP socket.
        
        If there is a packet, it is passed to a receiver function.
        
        Drops a packet if the random error value > p_err.
        """
        print ("Listening at address %s on port %d." % (self.ip, self.port))
        while (1):
            
            (packet_bytes, recv_addr) = self.udp_socket.recvfrom(self.buffer_)
                
            if packet_bytes and (random.uniform(0,1) >= self.p_err):
                self.parse_recv_data(packet_bytes, recv_addr)
            else:
                packet_bytes = None
                print "Packet errors too high. Dropped packet."
                continue
                
            
            
server_process = Server()
