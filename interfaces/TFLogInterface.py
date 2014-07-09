from BaseLogInterface import BaseLogInterface

import logging

class TFLogInterface(BaseLogInterface):
    def parse(self, data):
        logging.debug("Received data: %s", data)
