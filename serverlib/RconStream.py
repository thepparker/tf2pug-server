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
from collections import deque

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

        self.error = None

        self._queue = deque()

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
        logging.debug("Sending packet %s", repr(packet))
        self._stream.write(packet, callback)

    def _read_single_packet(self, callback = None):
        # reads a single packet from the stream and pushes the processed
        # response through the given callback if provided
        logging.debug("Reading single packet from stream")

        def process_packet(packed_packet):
            logging.debug("Processing packet: %s", repr(packed_packet))
            #packet is in the form <id (packed int)><response code (packed int)><body>\x00\x00
            curr_packet_id = struct.unpack('<l', packed_packet[0:4])[0]
            response_code = struct.unpack('<l', packed_packet[4:8])[0]
            message = packed_packet[8:].strip('\x00') #strip the terminators

            """logging.debug("ID: %d CODE: %d MESSAGE: %s", curr_packet_id,
                            response_code, message)"""

            # we now have the packet message, response code, and response id, 
            # so push it through the given callback
            if callback is not None:
                callback((curr_packet_id, response_code, message))

        def process_packet_len(packed_packet_len):
            packet_len = struct.unpack('<l', packed_packet_len)[0]
            logging.debug("Processing packet length: %s, length: %s", 
                            repr(packed_packet_len), packet_len)

            # read the entire packet
            logging.debug("Reading the rest of the packet")
            self._stream.read_bytes(packet_len, process_packet)

        self._stream.read_bytes(4, process_packet_len)

    def _auth(self, data = None, auth_sent = False, junked = False):
        """
        Called when connect is successful. First thing we always do after
        connecting is attempt to authenticate. Authentication is asynchronous.
        We'll utilise partials to do this
        """
        if self.error:
            raise self.error

        if not auth_sent:
            auth_packet = self._construct_packet(SERVERDATA_AUTH, self.rcon_password)

            # _auth will be called again once the auth packet has been sent

            f = partial(self._auth, auth_sent = True)
            self._send_packet(auth_packet, f)
        elif not junked:
            # read the junk packet out. don't supply a callback, so it is simply
            # discarded
            f = partial(self._auth, auth_sent = True, junked = True)
            self._read_single_packet(f)
        
        else:
            # now read the real response. call _auth_response once it has been
            # processed
            self._read_single_packet(self._auth_response)

    def _auth_response(self, response):
        logging.debug("Auth response: %s", repr(response))
        if response[1] == SERVERDATA_AUTH_RESPONSE:
            if response[0] == -1:
                self.error = RconAuthError("Invalid RCON password specified")

            elif response[0] == self.request_id:
                self.authed = True

                logging.debug("Successfully authed")

                self._process_queue()

            else:
                self.error = RconAuthError("Unknown packet id (%d) received when auth packet was expected with id %d" % (response[0], self.request_id))

        else:
            self.error = RconAuthError("Received unexpected response code when auth response was expected")

    def _exec(self, command, callback = None):
        """
        Send a command packet to the server if we are authenticated. When doing
        this, we send a packet with SERVERDATA_EXEC_COMMAND and the command we
        want to execute, along with an empty SERVERDATA_COMMAND_RESPONSE, which
        the server will mirror back at us once it has sent the response to our
        command (in order, because TCP is ordered). Doing this lets us know
        exactly when we've received the full response to our command.
        """
        if self.authed:
            # send command packet with no callback, it'll just execute and
            # and do nothing
            packet = self._construct_packet(SERVERDATA_EXEC_COMMAND, command)
            self._send_packet(packet)

            # add empty packet, with callback. this packet is just appended
            # to the stream's internal write queue
            packet = self._construct_packet(SERVERDATA_COMMAND_RESPONSE, r'')

            f = partial(self._command_sent_callback, handle_callback = callback)
            self._send_packet(packet, f)

    def _command_sent_callback(self, handle_callback = None):
        """
        Called when a complete command has been sent (command + mirror packets)
        This will let us know when we should start reading.

        @param handle_callback The callback to be used once we've read all data
                               from a response
        """
        
        # begin reading
        f = partial(self._handle_multi_packet_read, complete_callback = handle_callback)
        self._read_single_packet(f)

    def _handle_multi_packet_read(self, data, previous = None, complete_callback = None):
        # data is a tuple in the form (id, code, message)

        if previous is None:
            previous = [ data ]
        else:
            previous.append(data)

        length = len(previous)
        if length > 0:
            """
            To signify the end of a multi-line response, we'll receive an
            empty packet (which is the mirror of our empty packet), along
            with an additional empty packet whose body consists of solely
            \x01. So we need to check the last two packets. This means
            we'll receive a MINIMUM of THREE packets for ANY command response
            """

            response_complete = False
            got_mirror_packet = False
            empty = previous[length-2:] # last 2 packets in previous list
            for packet in empty:
                packet_id = packet[0]
                response_code = packet[1]
                message = packet[2]
                if (response_code == SERVERDATA_COMMAND_RESPONSE and
                    packet_id == self.request_id):

                    if got_mirror_packet and message == '\x01':
                        # have already gotten mirror packet, so this packet is the
                        # expected packet after the mirror, with body of \x01. 
                        # therefore, our response is complete!

                        response_complete = True
                    else:
                        got_mirror_packet = True

            if response_complete and complete_callback is not None:
                complete = self._compile_multi_packet(previous)
                complete_callback(complete)

                self._process_queue()
            elif not response_complete:
                # response not complete, get the next packet
                f = partial(self._handle_multi_packet_read, previous = previous, complete_callback = complete_callback)
                self._read_single_packet(f)

    def _compile_multi_packet(self, packets):
        """
        Compiles a list of packets into a single packet, chopping off the empty
        packets. Then calls the given callback method (if any) with the
        complete packet.

        @param packets A list of packet tuples

        @return Complete packet
        """

        first = packets[0]
        response_id = first[0]
        response_code = first[1]

        message = "".join([ x[2] for x in packets[:-2] ])

        return (response_id, response_code, message)

    def send_cmd(self, command, callback = None):
        if self.error:
            raise self.error

        if self._stream.reading() or self._stream.writing() or not self.authed:
            # we're already reading/writing from the socket. this command
            # should be queued
            logging.debug("Stream is busy or we are not authed. Adding command to queue")
            self._add_to_queue((command, callback))

        else:
            # execute the command!
            self._exec(command, callback)

    def _add_to_queue(self, qtuple):
        self._queue.append(qtuple)

    def _process_queue(self):
        logging.debug("Processing RCON command queue")
        try:
            command, callback = self._queue.popleft()
            logging.debug("QUEUE - command: %s, callback: %s", command, callback)

            self.send_cmd(command, callback)
        except IndexError:
            pass
        except:
            logging.exception("Unknown exception occurred whilst attempting to process queue")

    @property
    def closed(self):
        return self._stream.closed()


