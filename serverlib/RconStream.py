"""
A source RCON implementation utilising the tornado IOStream class for async
operations. Utilises futures to return data where applicable
"""

import socket
import struct
import logging

from tornado.iostream import IOStream

SERVERDATA_AUTH = 3
SERVERDATA_EXEC_COMMAND = 2

SERVERDATA_AUTH_RESPONSE = 2
SERVERDATA_COMMAND_RESPONSE = 0

to_hex = lambda x : ":".join(hex(ord(c))[2:].zfill(2) for c in x)

class RconError(Exception):
    """ 
    raised for general errors 
    """
    pass

class RconAuthError(Exception):
    """
    raised for auth errors (i.e wrong password)
    """
    pass

class RconConnectionError(Exception):
    """
    raised for errors reading/sending from/to disconnected sockets
    """
    pass

class RconConnectionInterruptedError(Exception):
    """
    raised when the connection is interrupted whilst reading (ie the server 
    closed the connection after rcon_password is changed)
    """
    pass

class RconConnection(object):
    def __init__(self, ip, port, rcon_password, command):
        self.ip = ip
        self.port = port
        self.rcon_password = rcon_password

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self._stream = IOStream(self._socket)

        self.authed = False
        self.request_id = 0

        # connect and immediately call _auth
        self._stream.connect((ip, port), self._auth)

    def _connect(self):
        if self._socket:
            try:
                self._socket.connect((self.ip, self.port))
            except:
                self.close()
                raise RconConnectionError("Unable to connect to server")
        else:
            raise RconConnectionError("Cannot connect to dead socket")

    def _construct_packet(self, code, body):
        #if len(body) > 510:
        #    raise RconError("Command length too long. Length specified: %s, max length: %s" % (len(body), 510))

        #packets are in the form dictated at https://developer.valvesoftware.com/wiki/Source_RCON_Protocol
        #<packet size><request id><request code><body string><empty string>
        #strings must be null terminated, even the empty one

        if body is None:
            body = r''

        self.request_id += 1

        #use little endian packing of ints, terminate body with a null, and add a null at the end for the empty string
        packet = struct.pack('<l', self.request_id) + struct.pack('<l', code) + body.encode('ascii') + '\x00\x00'

        #add the packed length of the message body to the beginning of the packet
        logging.debug("Packet length: %s, packet: %s", len(packet), repr(packet))

        packet = struct.pack('<l', len(packet)) + packet

        return packet

    def _receive_data(self):
        if not self._socket:
            raise RconError("Cannot receive data on dead socket")

        first_packet_id = None #this will be the ID return in multi-line responses
        curr_packet_id = 0 #this will be the ID checked against for the end of multi-line responses
        response_code = 0
        entire_message = ''

        got_empty_packet = False

        while 1:
            packet_len_packed = self.__get_packet_len()
            # now we have the entire packet length. 
            # all data is not necessarily sent in a single packet, and may be 
            # split into multiple packets
            packet_len = struct.unpack('<l', packet_len_packed)[0] 

            packet_packed = self.__read_socket(packet_len)

            logging.debug("Entire packet: %s", repr(packet_len_packed + packet_packed))

            #packet is in the form <id (packed int)><response code (packed int)><body>\x00\x00
            curr_packet_id = struct.unpack('<l', packet_packed[0:4])[0]
            response_code = struct.unpack('<l', packet_packed[4:8])[0]
            message = packet_packed[8:].strip('\x00') #strip the terminators

            if first_packet_id is None:
                first_packet_id = curr_packet_id

            if not self.authed:
                #we're waiting for an auth packet, so we should just return from here for now
                return (curr_packet_id, response_code, message)

            else:
                if response_code == SERVERDATA_COMMAND_RESPONSE and curr_packet_id == self.request_id:
                    #this is the mirror packet after sending a RESPONSE_VALUE command, so we know our potentially multi-line response has ended
                    if got_empty_packet:
                        logging.debug("Got empty packet after mirror. This signals end of multi-line response")
                        return (first_packet_id, response_code, entire_message)
                    
                    else:
                        logging.debug("Got empty mirror response")
                        got_empty_packet = True
                

                entire_message += message #concatenate the read message onto the full message



    def _run_callback(self):
        # we need to process the data received, then push it through the 
        # callback (if set?)

    def _read_stream(self, numbytes, callback):
        self._stream.read_bytes(numbytes, callback)

    def _read_stream_blocking(self, numbytes):
        data = self._stream.read_bytes(numbytes)
        yield data.result()

    def __get_packet_len(self):
        """
        Reads the packet length from the stream and yields it. This is the only
        read operation which will ALWAYS block.

        The first 4 bytes in a packet are the packet length
        """
        return self._read_stream_blocking(4)

    def __read_socket(self, num_bytes):
        #loops over the socket, reading until num_bytes is read
        if self.closed:
            raise RconConnectionError("Cannot read from closed socket")

        data = r''
        num_read = 0



        while num_read < num_bytes:
            try:
                rcvd = self._socket.recv(num_bytes - num_read)
            except:
                raise RconConnectionError("Connection timed out while waiting for data")

            if len(rcvd) == 0:
                raise RconConnectionInterruptedError("RCon connection unexpectedly closed")

            data += rcvd

            num_read = len(data)

        logging.debug("Data read: %s", to_hex(data))
        return data

    def _send_packet(self, packet):
        if self._stream and not self._stream.closed():
            logging.debug("Packet to send: %s", repr(packet))
            self._stream.write(packet)

        else:
            raise RconConnectionError("Cannot send to dead socket")


    def _auth(self):
        if not self.authed:
            auth_packet = self._construct_packet(SERVERDATA_AUTH, self.rcon_password)
            self._send_packet(auth_packet)

            junk = self._receive_data() # get junk packet pre-auth
            response = self._receive_data()

            logging.debug("Auth response: (junk): %s, (auth): %s", repr(junk), repr(response))

            if response[1] == SERVERDATA_AUTH_RESPONSE:
                if response[0] == -1:
                    raise RconAuthError("Invalid RCON password specified")

                elif response[0] == self.request_id:
                    self.authed = True

                    logging.debug("Successfully authed")

                else:
                    raise RconAuthError("Unknown packet id (%d) received when auth packet was expected with id %d" % (response[0], self.request_id))

            else:
                raise RconAuthError("Received unexpected response code when auth response was expected")

    def _exec(self, cmd):
        if self.authed:
            cmd_packet = self._construct_packet(SERVERDATA_EXEC_COMMAND, cmd)

            self._send_packet(cmd_packet)
            # send a "response" packet, which srcds will mirror back after 
            # responding to the EXEC, letting us know the exec command has 
            # finished. this makes it easier to read multi-line responses
            self._send_packet(self._construct_packet(SERVERDATA_COMMAND_RESPONSE, r''))

            return self._receive_data()

        else:
            raise RconError("RCon connected is not authed. Cannot send command")

    def send_cmd(self, cmd, callback = None):
        """
        Support a callback, which the rcon response will be parsed through. If no
        callback is given, we yield the data from _receive_data via a future
        """
        if not self.authed:
            self._auth()

        result = self._exec(cmd)

        if self.run_once:
            logging.debug("Single command executed. Closing socket")
            self.close()

        return result

    def close(self):
        if self._socket and not self.closed:
            self._socket.close()

            self.closed = True

    def fileno(self):
        return self._socket.fileno()

    @property
    def closed(self):
        return self._stream.closed()


