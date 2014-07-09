import UDPServer
from interfaces import TFLogInterface
#from entities import Server
from tornado import ioloop
import settings
import logging

import tornado.options

server_address = (settings.listen_ip, 0)
print server_address
iface = TFLogInterface.TFLogInterface(None)

listener = UDPServer.UDPServer(server_address, iface.parse)

listener.start()

ioloop.IOLoop.instance().start()
