
import logging
import string
import random

from serverlib import Rcon
from interfaces import TFLogInterface
import UDPServer
import settings

def random_string(len=24, chars=string.ascii_lowercase + string.ascii_uppercase + string.digits):
    #generates a random string of length len
    return ''.join(random.choice(chars) for x in range(len))

class Server(object):
    def __init__(self):
        self.id = -1
        # server details
        self.ip = ""
        self.port = 0
        self.rcon_password = ""
        self.password = ""

        # the pug on this server
        self.pug_id = -1
        self.pug = None

        # the log port being used by this server (for log_address)
        self.log_port = 0

        self.group = 0

        self.rcon_connection = None

    def rcon(self, command):
        if not self.rcon_connection or self.rcon_connection.closed:
            self.rcon_connection = Rcon.RconConnection(self.ip, self.port, self.rcon_password)

        res = self.rcon_connection.send_cmd(command)
        logging.debug("RCON RESULT: %s", res)

        return res

    def reset(self):
        self.pug = None
        self.pug_id = -1

        self.rcon("say This server is being reset because the pug is over; kickall; sv_password getOuTPLZ")

        self._end_listener()

    # reserves a server for a pug
    def reserve(self, pug):
        self.pug = pug
        self.pug_id = pug.id

        pug.server = self
        pug.server_id = self.id

        self.password = random_string(10)

        self.rcon("sv_password %s; say This server has been reserved for pug %d; kickall" % (self.password, pug.id,))

        self._setup_listener()

    def setup(self):
        if not self.pug:
            return

        rcon_command = "kickall; changelevel %s; sv_password %s" % (self.pug.map, self.password)
        self.rcon(rcon_command)

    def _setup_listener(self, log_port = 0):
        if log_port is None:
            log_port = 0
            
        # make an instance of udp server, log interface, and start the listener
        server_address = (settings.listen_ip, log_port) # bind to any available IP

        self._log_interface = TFLogInterface.TFLogInterface(self)

        self._listener = UDPServer.UDPServer(server_address, self._log_interface.parse)
        self._listener.start()

        listener_ip, self.log_port = self._listener.server_address

        self.rcon("logaddress_add %s:%s" % self._listener.server_address)

    def late_loaded(self):
        # if there was last a pug in progress on this server, re-establish
        # the listener... it doesn't really need to be the same port, it could
        # be any port
        if self.pug_id > 0:
            self._setup_listener(self.log_port)

    def _end_listener(self):
        self.rcon("logaddress_del %s:%s" % self._listener.server_address)
        self._listener.close()

        self._log_interface = None
        self.log_port = 0

    @property
    def in_use(self):
        return self.pug is not None or self.pug_id > 0
