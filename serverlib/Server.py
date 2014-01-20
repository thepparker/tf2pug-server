
import logging
import string
import random

import Rcon

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

        self.rcon("sv_password %s; say This server has been reserved for pug %d; kickall" % self.password, pug.id)

        self._setup_listener()

    def setup(self):
        if not self.pug:
            return

        rcon_command = "changelevel %s; sv_password %s" % (self.pug.map, self.password)
        self.rcon(rcon_command)

    def _setup_listener(self):
        pass

    def _end_listener(self):
        #self.rcon("logaddress_del blah")

        self.log_port = 0

    @property
    def in_use(self):
        return self.pug is not None or self.pug_id > 0
