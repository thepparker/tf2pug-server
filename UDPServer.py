"""
A UDP listen server using tornado's IO loop. Using tornado IOStream and
UDPStream (http://kyle.graehl.org/coding/2012/12/07/tornado-udpstream.html)
as examples
"""

import socket
import time
import logging

from tornado import ioloop

class UDPServer(object):
    def __init__(self, server_address, callback, io_loop = None):
        self.server_address = server_address
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setblocking(False)
        self._server_bind()

        self._callback = callback

        self._state = None
        self._stop = False

        self.io_loop = io_loop or ioloop.IOLoop.instance()

    def _server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)

        #update the address with what the socket bound to (in the case of 0 
        #port), which allows the OS to bind to any port
        self.server_address = self.socket.getsockname()

    """
    Start reading
    """
    def start(self):
        self._read_forever(None, first = True)

    def _read_forever(self, data, first = False):
        # if this is the first call, we're just starting, so we do nothing
        # with data. if not, we forward the data to the callback
        if not first:
            self._callback(data)

        # if we're finished, HALT!
        if self._stop:
            return

        # set state to READ
        self._add_io_state(self.io_loop.READ)

    """
    Sets the current state of our socket fd in the io loop
    """
    def _add_io_state(self, state):
        # if state is none (i.e first call), we either set it to the given
        # state, or it's an error, and add the socket to the io loop.
        # else, if self._state and state are not the same, we update the 
        # io loop with the new state
        if self._state is None:
            self._state = ioloop.IOLoop.ERROR | state

            # add our socket 
            self.io_loop.add_handler(self.socket.fileno(), self._handle_events,
                                        self._state)
        elif not self._state & state:
            # update the state, and update the io loop with new state
            self._state = self._state | state
            self.io_loop.update_handler(self.socket.fileno(), self._state)

    """
    Read size bytes from the buffer
    """
    def recv(self, size):
        return self.socket.recv(size)

    """
    Remove our socket from the io loop and close it
    """
    def close(self):
        self._stop = True
        self.io_loop.remove_handler(self.socket.fileno())
        self.socket.close()
        self.socket = None

    """
    Called by _handle_events if there is data to read
    """
    def _handle_read(self):
        # if this method is called, we've received data
        try:
            data = self.recv(4096)
        except:
            data = None

        self._read_forever(data)

    def _handle_events(self, fd, events):
        # the socket has data available to read!
        if events & self.io_loop.READ:
            self._handle_read()
        if events & self.io_loop.ERROR:
            logging.error("Socket event error")
