import UDPServer
from interfaces import TFLogInterface
#from entities import Server
from tornado import ioloop

server_address = (settings.listen_ip, 0)
iface = TFLogInterface.TFLogInterface(None)

listener = UDPServer(server_address, iface.parse)

listener.start()

ioloop.IOLoop.instance.start()
