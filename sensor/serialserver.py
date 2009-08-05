#!/usr/bin/env python

"""
serialserver multiplexes the Arduino serial port to concurrent incoming TCP 
socket connections.  this allows multiple clients to use the connected arduino
at once.

socket server listens on port 9994 and keeps open all incoming TCP connections

messages sent to the open socket are passed to the serial port and responses
  are written to the client socket

the serial port is also polled periodically and any other messages are broadcast
  to all open connections

future improvements:
    - convert print's to logging.*
    - subclass SocketServer.TCPServer constructor to eliminate global SERIAL_DAEMON
    - switch from Lock protected lists to python's synchronized Queue class 
    - better granularity of existing locks
""" 

from __future__ import with_statement

import serial
import SocketServer, threading, socket, re, os, logging
import traceback

SERVER_HOST_PORT = 'localhost', 9994

SERIAL_PORT = 'COM12' if os.name is 'nt' else '/dev/ttyUSB0'

# socket read timeout in seconds
TIMEOUT  = 0.01
# serial port timeout in seconds
SERIAL_TIMEOUT = 0.05

global SERIAL_DAEMON

class TCPHandler(SocketServer.BaseRequestHandler):
    def setup(self):
        global SERIAL_DAEMON
        assert(SERIAL_DAEMON)

        self.seriald = SERIAL_DAEMON

        (host, port) = self.client_address
        self.client_id = port
        self.seriald.register_client(self.client_id)

        self.request.settimeout(TIMEOUT)

    def handle(self):
        print 'Opened TCP client connection %s' % str(self.client_address)

        while True:
            try:
                self.data = self.request.recv(1024)

                if self.data:
                    message = self.data.strip()
                    if not message: continue

                    print 'received message', message, 'length %d' % len(message)
                    # send to serial port
                    self.seriald.outgoing((self.client_id, message))
                else:
                    # stream closed
                    self.request.close()
                    print 'Closed TCP client connection #%d' % self.client_id
                    break
            except socket.timeout:
                # check if there are any incoming messages for this client
                messages = self.seriald.incoming(self.client_id, pop=True)
                for (id, msg) in messages:
                    print 'sending message %s to %d' % (msg.strip(), self.client_id)
                    self.request.send(msg)
    
    def finish(self):
        self.seriald.unregister_client(self.client_id)

class TCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass

class SerialDaemon(object):
    def __init__(self, ser):
        assert(ser)

        self.ser = ser             # serial port
        self.incoming_serial = []  # message queue from the serial port
        self.outgoing_serial = []  # message queue writing to serial port
        self.clients = set()       # track a global list of clients for broadcast messages
        
        self.client_lock = threading.Lock()      # clients mutex
        self.message_lock = threading.Lock()     # message queues mutex

    def register_client(self, client_id):
        with self.client_lock:
            self.clients.add(client_id)

    def unregister_client(self, client_id):
        print 'unregistering client ', client_id
        with self.client_lock:
            self.clients.remove(client_id)

        # remove any messages related to this client
        self.incoming(client_id, pop=True)
        with self.message_lock:
            self.outgoing_serial = filter(lambda (id, msg): id != client_id, 
                                          self.outgoing_serial)

    def update(self):
        """Called from main loop"""

        valid_message = lambda msg: msg and not msg.startswith('#')

        def broadcast(message):
            for client in self.clients:
                self.incoming_serial.append((client, msg))

        # read and broadcast any new global messages
        msg = self.ser.readline()
        if valid_message(msg):
            with self.message_lock: broadcast(msg)

        # send client requests and accumulate responses
        with self.message_lock:
            while len(self.outgoing_serial):
                (id, msg) = self.outgoing_serial.pop(0)
                print 'writing "%s" to serial port' % msg
                self.ser.write(msg + '\n')

                # wait till we get a response to our query
                if valid_message(msg):
                    attempts = 100
                    command = msg.split()[0]

                    while attempts:
                        response = self.ser.readline()
                        if valid_message(response):
                            print 'response "%s"\ncommand "%s"' % (response.strip(), command)
                            if response and command == response.split()[0]:
                                print 'matched response %s' % response.strip()
                                self.incoming_serial.append((id, response))
                                break
                            else:
                                broadcast(msg)

                        attempts -= 1
                    else:
                        # send out a timeout message
                        self.incoming_serial.append((id, '!timeout\r\n'))

    def outgoing(self, (client_id, message)):
        """Send a message to the serial port"""

        with self.message_lock:
            self.outgoing_serial.append((client_id, message))

    def incoming(self, client_id, pop=True):
        """
        Get incoming messages from the serial port

        client_id -- matches only incoming messages associated with the given 
                     client id
        pop -- remove matching messages from the incoming queue
        """

        messages = list()
        popped_queue = list()

        with self.message_lock:
            for msg in self.incoming_serial:
                if msg[0] == client_id:
                    messages.append(msg)
                else:
                    popped_queue.append(msg)
            if pop:
                self.incoming_serial = popped_queue

        return messages

if __name__ == '__main__':
    ser = serial.Serial(SERIAL_PORT, 9600, timeout=SERIAL_TIMEOUT)

    try:
        global SERIAL_DAEMON
        SERIAL_DAEMON = SerialDaemon(ser)

        # start up server thread
        server = TCPServer(SERVER_HOST_PORT, TCPHandler)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.setDaemon(True)
        server_thread.start()

        print 'Serial server initialized'
        print '  -- listening on serial port %s and %s\n' % (
                SERIAL_PORT, '%s:%d' % (SERVER_HOST_PORT))
        while True:
            # poll serial port
            SERIAL_DAEMON.update()

    except Exception, e:
        print 'serialserver exception:', e 
        traceback.print_exc()
    finally:
        ser.close()

