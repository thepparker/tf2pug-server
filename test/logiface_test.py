import socket

newsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
newsocket.connect(('192.168.35.130', 38657))

newsocket.send("TEST")
