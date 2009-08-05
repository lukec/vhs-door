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
    - subclass SocketServer.TCPServer constructor to eliminate global SERIAL_DAEMON
    - switch from Lock protected lists to python's synchronized Queue class 
    - better granularity of existing locks
""" 

from __future__ import with_statement

import serial, yaml
import SocketServer, threading, socket, re, os, logging, time
import traceback

SERVER_HOST_PORT = 'localhost', 9994

SERIAL_PORT, LOG_FILENAME, YAML_CONFIG = {
    'nt': ('COM12', 'serialserver.log', 'vhs.yaml'),
}.get(os.name, ('/dev/ttyUSB0', '/var/log/vhs-serialserver.log', '/etc/vhs.yaml'))

config = yaml.load(file(YAML_CONFIG))
SENSOR_HOOKS_DIR = config.get('sensor_hooks_dir')

# socket read timeout in seconds
TIMEOUT  = 0.01
# serial port timeout in seconds
SERIAL_TIMEOUT = 0.05

global SERIAL_DAEMON

logging.basicConfig(filename=LOG_FILENAME, level=logging.DEBUG)

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
        logging.info('Opened TCP client connection %s' % str(self.client_address))

        while True:
            try:
                self.data = self.request.recv(1024)

                if self.data:
                    message = self.data.strip()
                    if not message: continue

                    logging.debug('received message "%s" length %d' % (message, len(message)))
                    # send to serial port
                    self.seriald.outgoing((self.client_id, message))
                else:
                    # stream closed
                    self.request.close()
                    logging.info('Closed TCP client connection #%d' % self.client_id)
                    break
            except socket.timeout:
                # check if there are any incoming messages for this client
                messages = self.seriald.incoming(self.client_id, pop=True)
                for (id, msg) in messages:
                    logging.debug('sending message %s to %d' % (msg.strip(), self.client_id))
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
        logging.debug('unregistering client %s' % client_id)
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
                logging.debug('writing "%s" to serial port' % msg)
                self.ser.write(msg + '\n')

                # wait till we get a response to our query
                if valid_message(msg):
                    attempts = 100
                    command = msg.split()[0]

                    while attempts:
                        response = self.ser.readline()
                        if valid_message(response):
                            logging.debug('response "%s"' % response.strip())
                            logging.debug(' command "%s"' % command)
                            if response and command == response.split()[0]:
                                logging.debug('matched response %s' % response.strip())
                                self.incoming_serial.append((id, response))
                                break
                            else:
                                broadcast(msg)

                        attempts -= 1
                    else:
                        # send out a timeout message
                        logging.warning('timeout on message "%s"' % msg)
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

class RelayScript(object):
    """
    RelayScript opens a server port and listens for commands from the arduino,
    then triggers matching scripts in SENSOR_HOOKS_DIR
    """

    def __init__(self):
        self.connect()
        logging.debug('Relay will trigger scripts from %s' % SENSOR_HOOKS_DIR)

    def loop(self):
        retry = False

        def _loop():
            while True:
                try:
                    data = self.socket.recv(1024)
                    if data:
                        self.run_command_from_arduino(data)
                        logging.debug('Received data "%s"' % data.strip())
                    else:
                        logging.info('Client connection terminated by server')
                        retry = True
                        break
                except socket.timeout:
                    pass

        while True:
            _loop()
            if retry:
                logging.info('Relay client waiting 10s before trying to reconnect')
                time.sleep(10)
                self.connect()
            else:
                break

    def connect(self):
        # connect to socket
        self.socket = s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(TIMEOUT)
        s.connect(SERVER_HOST_PORT)

    def run_command_from_arduino(self, data):
        def trigger(arg, dirname, names):
            for filename in names:
                script_path = os.path.join(dirname, filename)
                if not os.path.islink(script_path) and os.path.isfile(script_path):
                    full_path = '%s %s' % (script_path, arg)
                    logging.debug('launching "%s"' % full_path)
                    os.system(full_path)

        command, sep, arg = data.strip().partition(' ')
        hookpath = SENSOR_HOOKS_DIR
        script_dir = os.path.join(hookpath, '%s.d' % command)
        if os.path.exists(script_dir):
            os.path.walk(script_dir, trigger, arg)

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

        # start up relay client thread
        relay = RelayScript()
        relay_thread = threading.Thread(target=relay.loop)
        relay_thread.setDaemon(True)
        relay_thread.start()

        logging.info('Serial server initialized')
        logging.info('  -- listening on serial port %s and %s\n' % (
                SERIAL_PORT, '%s:%d' % (SERVER_HOST_PORT)))
        while True:
            # poll serial port
            SERIAL_DAEMON.update()

    except Exception, e:
        logging.critical('serialserver exception:', e)
        logging.critical(traceback.format_exc())
    finally:
        ser.close()

