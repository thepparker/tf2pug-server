"""
A source RCON implementation utilising the tornado IOStream class for async
operations. Utilises futures to return data where applicable
"""

import socket
import struct
import logging

from tornado.iostream import IOStream
from tornado import gen

from functools import partial

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
    def __init__(self, ip, port, rcon_password):
        self.ip = ip
        self.port = port
        self.rcon_password = rcon_password

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self._stream = IOStream(self._socket)

        self.authed = False
        self.request_id = 0

        # async connect & call _auth when connected
        self._stream.connect((ip, port), self._auth)

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

    def _send_packet(self, packet, callback = None):
        return self._steam.write(packet, callback)

    def _begin_read_packet(self):
        packet_len_packed = yield self._stream.read_bytes(4)
        packet_len = struct.unpack('<l', packet_len_packed)[0]

        return self._read_packet(packet_len)

    def _read_packet(self, numbytes):
        # we have the packet length. now we want to read LENGTH bytes from the
        # socket. If we read async, we'll need to have it pass the result
        # through our callback function, which will then process the packet and
        # pass it onto the given callback.
        # If we blocking read, we need to pass that data to our processing
        # method, which will return the data

        # let's implement blocking first, then figure out how to implement it
        # async
        packet_packed = yield self._stream.read_bytes(numbytes)

        #packet is in the form <id (packed int)><response code (packed int)><body>\x00\x00
        curr_packet_id = struct.unpack('<l', packet_packed[0:4])[0]
        response_code = struct.unpack('<l', packet_packed[4:8])[0]
        message = packet_packed[8:].strip('\x00') #strip the terminators

        # we now have the packet message, response code, and response id. 
        # if this packet is an auth packet, we can just return here. else, it
        # _COULD_ be a multi-line response, in which case we need to keep
        # reading until we've hit the end. The end is signified by an empty
        # packet after a mirror packet.

        if not self._authed:
            # just return here
            return (curr_packet_id, response_code, message)

        else:
            # possible multi line response.
            pass
        

    def _auth(self):
        """
        Called when connect is successful. First thing we always do after
        connecting is attempt to authenticate. Authentication is asynchronous.
        We'll utilise partials to do this properly
        """
        auth_packet = self._construct_packet(SERVERDATA_AUTH, self.rcon_password)

        # _auth will be called again once the auth packet has been sent
        self._send_packet(auth_packet, self._auth)

        junk = yield self._begin_read_packet()
        # now just get real response
        response = yield self._begin_read_packet()

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

    @property
    def closed(self):
        return self._stream.closed()


