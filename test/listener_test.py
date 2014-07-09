import UDPServer
from interfaces import TFLogInterface, PSQLDatabaseInterface
from entities import Server
from serverlib import ServerManager
from tornado import ioloop
import settings
import logging
import psycopg2
import threading
import socket

logging.basicConfig(level=logging.DEBUG)

server = None
listener = None

def basicListener():
    server_address = (settings.listen_ip, 0)
    iface = TFLogInterface.TFLogInterface(None)

    listener = UDPServer.UDPServer(server_address, iface.parse)
    print listener.server_address

    listener.start()

def serverListener():
    dsn = "dbname=%s user=%s password=%s host=%s port=%s" % (
                settings.db_name, settings.db_user, settings.db_pass, 
                settings.db_host, settings.db_port
            )

    db = psycopg2.pool.SimpleConnectionPool(minconn = 1, maxconn = 1, 
        dsn = dsn)

    dbinterface = PSQLDatabaseInterface.PSQLDatabaseInterface(db)

    smanager = ServerManager.ServerManager(1, dbinterface)
    server = smanager.get_server_by_id(1)

    server._setup_listener(50000)
    logging.info("server addr: %s", server._listener.server_address)

def start():
    basicListener()
    serverListener()

    ioloop.IOLoop.instance().start()

def message_basicTest():
    newsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    newsocket.connect(('127.0.0.1', listener.server_address[1]))

    newsocket.send("BASIC TEST")
    newsocket.close()

def message_serverTest():
    newsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    newsocket.connect(('127.0.0.1', 50000))
    newsocket.send("SERVER TEST!")

    newsocket.close()

def main():
    thread = threading.thread(target = start)
    thread.start()

    message_basicTest()
    message_serverTest()
