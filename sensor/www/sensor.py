#!/usr/bin/env python

import web, serial
import os, re, socket, datetime, hashlib, httplib

import yaml
import xml.dom.minidom

import decree          # http://bitbucket.org/dantakk/decree

from decorators import restricted, throttled

TIMEOUT = 30

DOC = """\
sensor.hackspace.ca - a <a href="http://vancouver.hackspace.ca">VHS</a> project

    <a href="/door/state">/door/state</a>
       text/plain response: open|closed (entrance door)
    
    <a href="/door/photo">/door/photo</a>
       image/jpeg response: a photo of the entrance taken in the last %ds
    
    <a href="/bathroom/door/state">/bathroom/door/state</a>
       text/plain response: open|closed (bathroom door)
    
    <a href="/temperature/celsius">/temperature/celsius</a>
       text/plain response: (\d+(\.\d*)?) (space temperature in celsius)
    
    <a href="/temperature/fahrenheit">/temperature/fahrenheit</a>
       text/plain response: (\d+\.(\d*)?) (space temperature in fahrenheit)
    
    <a href="/feed/eeml">/feed/eeml</a>
       text/xml response: an <a href="http://www.eeml.org">EEML</a> XML feed for use with <a href="http://www.pachube.com">pachube</a>
    
Restricted urls require VHS membership

    <a href="/buzz">/buzz</a>
       text/plain response: (raw buzzer response)

    <a href="/door/photo/url">/door/photo/url</a>
       image/jpeg response: redirects to URL of a new photo of the entrance
""" % TIMEOUT

SERIAL_HOST_PORT = ('localhost', 9994)

# route urls to handler classes
urls = (
    r'/door/(state|photo(?:\/url)?)/?', 'Door',
    r'/bathroom/door/(state)/?', 'BathroomDoor',
    r'/temperature/(celsius|fahrenheit)/?', 'Temperature',
    r'/buzz/?', 'Buzz',
    r'/feed/(eeml)/?', 'Feed',
    r'/feed/(pusheeml)/?', 'Feed',
    r'.*', 'Static',
)

app = web.application(urls, globals())

def serial_query(query):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(SERIAL_HOST_PORT)
    s.send(query + '\n')
    response = s.recv(1024)
    s.close()
    return response

def get_celsius():
    response = serial_query('temperature')
    match = re.search(r'((\d+)(\.\d+)?)C?', response)
    if match:
        return match.groups()[0]
    else:
        return None

def take_door_photo():
    """Take a photo of the front door and return a URL and file path"""

    # based on lukec's code in VHS.pm
    config = yaml.load(file('/etc/vhs.yaml'))
    short_hash = hashlib.sha256(str(datetime.datetime.now())).hexdigest()[0:6]
    pic_base = config.get('picture_base')
    if pic_base:
        filename = os.path.join(pic_base, '%s.jpeg' % short_hash)
        os.system('streamer -c /dev/video0 -b 16 -o %s >/dev/null 2>&1' % filename)
        short_file = os.path.splitext(filename)[0] + '.jpg'
        os.rename(filename, short_file)
        pic_uri_base = config.get('picture_uri_base') 
        if pic_uri_base and os.path.exists(short_file):
            pic_uri = '%s/%s' % (pic_uri_base, os.path.basename(short_file))
            return (pic_uri, short_file)

    return None

class Door(object):
    def __init__(self, *args, **kw):
        super(Door, self).__init__(*args, **kw)
        self.doorname = self.response_cmd = 'door'
        
    def door_state(self):
        response = serial_query('%s state' % self.doorname).strip()
        if response == '%s closed' % self.response_cmd:
            return 'closed'
        elif response == '%s open' % self.response_cmd:
            return 'opened'
        else:
            return '!unknown response <%s>' % response

    @throttled(timeout=TIMEOUT)
    def door_photo(self):
        door_photo_uri, door_photo_path = take_door_photo()
        if door_photo_path:
            web.header('Content-Type', 'image/jpeg')
            web.header('X-Vhs-URL', str(door_photo_uri))
            return(file(door_photo_path).read())

        return '!door photo not taken - check config'

    @restricted
    def door_photo_url(self):
        door_photo_uri, door_photo_path = take_door_photo()
        if door_photo_uri:
            raise web.seeother(door_photo_uri)

        return '!door photo not taken - check config'

    def GET(self, query):
        if query == 'state':
            return self.door_state()
        elif query == 'photo':
            return self.door_photo()
        elif query == 'photo/url':
            return self.door_photo_url()

class BathroomDoor(Door):
    def __init__(self, *args, **kw):
        super(BathroomDoor, self).__init__(*args, **kw)
        self.doorname = 'bathroom door'
        self.response_cmd = 'bathroom'

class Temperature:
    @property
    def celsius(self):
        return get_celsius() or '#no match in response "%s"' % response

    @property
    def fahrenheit(self):
        celsius = self.celsius

        if celsius.startswith('#'):
            return celsius

        fahr = 1.8 * float(celsius) + 32
        return '%.2f' % fahr

    def GET(self, scale):
        if scale == 'celsius':
            return self.celsius
        elif scale == 'fahrenheit':
            return self.fahrenheit

class Static:
    def GET(self):
        web.header('Content-Type', 'text/html')
        return """\
<html>
  <head>
  <title>sensor.hackspace.ca</title>
  </head>
  <body>
  <pre>%s</pre>
  </body>
</html>
""" % DOC
    
class Buzz:
    @restricted
    def GET(self):
        return serial_query('buzz');

class Feed:
    @property
    def eeml(self):
        tag = decree.DecreeTagger()
        xmlns = { 'xmlns': 'http://www.eeml.org/xsd/005',
                  'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
                  'xsi:schemaLocation': 'http://www.eeml.org/xad/005 http://www.eeml.org/xsd/005/005.xsd',
                }

        try:
            celsius = float(get_celsius())
        except ValueError:
            celsius = None  

        # TODO include properly formatted date
        feed = tag.eeml[xmlns] (
                   tag.environment (
                       tag.title('Vancouver Hackerspace (VHS)'),
                       # tag.feed('http://www..com/feeds/1.xml'),
                       tag.description('VHS @ 45 West Hastings St'),
                       tag.website('http://vancouver.hackspace.ca'),
                       tag.email('info@hackspace.ca'),
                       tag.location[{ 'exposure': 'indoor',
                                      'domain': 'physical',
                                      'disposition': 'fixed'}] (
                           tag.name('VHS first floor'),
                           tag.lat('49.282319'),
                           tag.lon('-123.106152'),
                       ),
                       tag.data[{'id':'0'}] (
                           tag.tag('temperature'),
                           tag.value(celsius),
                           tag.unit[{'symbol': 'C', 'type': 'derivedSI'}]('Celsius')
                       ) if celsius else None,
                   )
               )
        builder = decree.XmlDomBuilder(xml.dom.minidom.getDOMImplementation())
        doc = builder.create_xml_dom(feed)
        # for debugging return doc.toprettyxml()
        return doc.toxml()

    def pachube_update(self):
        config = yaml.load(file('/etc/vhs.yaml'))
        pachube_apikey = config.get('pachube_apikey')
        if pachube_apikey:
            conn = httplib.HTTPConnection('www.pachube.com:80')
            conn.request('PUT', 'http://www.pachube.com/api/2417.xml', self.eeml, {'X-PachubeApiKey': pachube_apikey})
            rsp = conn.getresponse()
            if rsp.status != 200:
                raise Exception(rsp.reason)
            response = rsp.read()
            conn.close()

            return response

        return 'pachube_apikey not defined in /etc/vhs.yaml'

    def GET(self, kind):
        if kind == 'eeml':
            web.header('Content-Type', 'text/xml')
            return self.eeml
        elif kind == 'pusheeml':
            web.header('Content-Type', 'text/plain')
            try:
                return self.pachube_update()
            except Exception, e:
                return 'Error: %s' % e

    
if __name__ == '__main__':
    app.run()

