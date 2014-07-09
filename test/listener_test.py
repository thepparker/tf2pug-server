import logging
logging.basicConfig()

import UDPServer
from interfaces import TFLogInterface, PSQLDatabaseInterface
from entities import Server
from serverlib import ServerManager
from tornado import ioloop
import settings
import psycopg2
import psycopg2.pool
import threading
import socket
import time

def basicListener():
    server_address = (settings.listen_ip, 0)
    iface = TFLogInterface.TFLogInterface(None)

    listener = UDPServer.UDPServer(server_address, iface.parse)
    listener_address = listener.server_address

    listener.start()
    print "listener test is up"
    return listener_address

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
    server_address = server._listener.server_address
    print "server test is up"
    return server_address

def start(d):
    d.listener_address = basicListener()
    d.server_address = serverListener()
    try:
        ioloop.IOLoop.instance().start()
    except:
        quit()

def message_basicTest(d):
    newsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    newsocket.connect(('127.0.0.1', d.listener_address[1]))

    newsocket.send("BASIC TEST")
    newsocket.close()

def message_serverTest(d):
    newsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    newsocket.connect(('127.0.0.1', d.server_address[1]))
    newsocket.send("SERVER TEST!")

    newsocket.close()

class data(object):
    listener_address = None
    server_address = None

def main():
    d = data()
    thread = threading.Thread(target = start, args=(d,))
    thread.daemon = True
    thread.start()

    while d.listener_address is None or d.server_address is None:
        #print "dont have addresses yetttttt"
        pass

    message_basicTest(d)
    message_serverTest(d)
    

main()
