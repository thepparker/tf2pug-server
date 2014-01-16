
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

    def setup(self, pug):
        pass

    @property
    def in_use(self):
        return self.pug is not None
