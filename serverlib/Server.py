
import logging

import Rcon

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

    def setup(self, pug):
        rcon_command = "changelevel %s; password %s; logaddress_add %s" % (pug.map, self.password, "asdf")
        self.rcon(rcon_command)

        self.pug = pug
        self.pug_id = pug.id

        self.password = pug.password

        self._setup_listener()

    def _setup_listener(self):
        pass

    @property
    def in_use(self):
        return self.pug is not None
