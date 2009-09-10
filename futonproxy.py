#!/usr/bin/env python
# Copyright 2009 Paul J Davis
#
# This file is part of the futonproxy package and is released under the
# Tumbolia Public License. See LICENSE for more details.

"""
A simple proxy server to assist in hacking on the CouchDB administrator
interface Futon.
"""

import httplib
import inspect
import logging
import mimetypes
import optparse as op
import os
import uuid
import urlparse
from wsgiref.handlers import SimpleHandler
from wsgiref.simple_server import make_server, WSGIRequestHandler
from wsgiref.util import is_hop_by_hop, FileWrapper

__usage__ = "%prog [OPTIONS] [futon_directory]"

log = logging.getLogger()
logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s %(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

class FutonProxy(object):
    def __init__(self, couch, dname):
        self.couch = httplib.HTTPConnection(couch)
        self.couch.connect()
        self.dname = dname
    
    def __call__(self, environ, start_response):
        if environ['PATH_INFO'] == '/_utils':
            url = ''.join([
                environ['wsgi.url_scheme'],
                '://',
                environ.get('HTTP_HOST', environ['SERVER_NAME']),
                '/_utils/'
            ])
            start_response('301 MOVED PERMANENTLY', [
                ('Location', url)
            ])
            return ['Its not here!\n']
        if environ['PATH_INFO'].startswith("/_utils"):
            return self.send_file(environ, start_response)
        return self.proxy_request(environ, start_response)
    
    def send_file(self, environ, start_response):
        path = self.hack(environ['PATH_INFO'])
        path = path[len("/_utils"):].lstrip('/')
        path = os.path.join(self.dname, path)
        if path[-1:] == '/':
            path += 'index.html'
        path = os.path.abspath(path)

        if not os.path.isfile(path):
            start_response('404 NOT FOUND', [])
            return ["File not found"]

        ctype = mimetypes.guess_type(path)[0] or "text/plain"
        
        headers = [
            ('Content-Type', ctype),
            ('Content-Size', str(os.stat(path).st_size)),
            # Crush caching.
            ('Cache-Control', 'no-cahe'),
            ('Expires', 'Fri, 01 Jan 1990 00:00:00 GMT'),
            ('Pragma', 'no-cache'),
            ('ETag', uuid.uuid4().hex.upper())
        ]
        start_response('200 OK', headers)

        return FileWrapper(open(path))

    def proxy_request(self, environ, start_response):
        method = environ['REQUEST_METHOD']
        path = self.hack(environ['PATH_INFO'], remove_qs=False)
        if method.upper() in ["POST", "PUT"]:
            body = environ['wsgi.input'].read(int(environ['CONTENT_LENGTH']))
        else:
            body = None
        headers = dict([
            (h[5:], environ[h])
            for h in environ
            if h.startswith("HTTP_")
        ])
        
        self.couch.request(method, path, body, headers)
        resp = self.couch.getresponse()

        status = "%s %s" % (resp.status, resp.reason)
        headers = filter(lambda x: not is_hop_by_hop(x[0]), resp.getheaders())
        body = resp.read()
        
        start_response(status, headers)
        return [body]

    def hack(self, default, remove_qs=True):
        r"""
        A pristine example of Python web development.
        
        I need the raw unescaped URL in because CouchDB relies on
        having %2F available.
        
        Technically this could be rewritten as this:
        
            inspect.stack()[4][0].f_locals["self"].path
        
        But I wanted to test each assumption in that chain.
        
        Basic idea:
            1. Reach back up the stack four frames
            2. Grab the object that parsed the raw URL.
            3. Grab its stored copy of the raw version
            4. Profit

        I knew it was four frames because I counted back in my
        head. None of that write a temp version that iterated
        and checked stuff here. I swear!
        """
        frames = inspect.stack()
        if len(frames) < 5:
            return default
        if "self" not in frames[4][0].f_locals:
            return default
        handler = frames[4][0].f_locals["self"]
        if not isinstance(handler, WSGIRequestHandler):
            return default
        if not hasattr(handler, "path"):
            return default
        if not isinstance(handler.path, basestring):
            return default
        path = handler.path
        pos = path.find("?")
        if remove_qs and pos >= 0:
            return path[:pos]
        return path

def options():
    return [
        op.make_option('-a', '--address', dest='address',
            default='127.0.0.1',
            help="IP to use for client connections."),
        op.make_option('-p', '--port', dest='port', type='int',
            default=8080,
            help="Port to use for client connections."),
        op.make_option('-c', '--couch', dest='couch',
            default='127.0.0.1:5984',
            help="The base URL of a running CouchDB node.")
    ]

def main():
    parser = op.OptionParser(usage=__usage__, option_list=options())
    opts, args = parser.parse_args()
    
    if len(args) > 1:
        parser.error("Unrecognized arguments: %r" % ' '.join(args[1:]))
    if len(args) < 1:
        dname = os.path.abspath(".")
    else:
        dname = args[0]
        
    if not os.path.isdir(dname):
        parser.error("%r does not exist." % dname)

    couch = opts.couch
    if couch.startswith("http://"):
        couch = couch[7:]
    elif couch.startswith("https://"):
        couch = couch[8:]
    couch = couch.rstrip('/')

    app = FutonProxy(couch, dname)
    server = make_server(opts.address, opts.port, app)
    log.info("Starting server at http://%s:%d" % (opts.address, opts.port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    
if __name__ == '__main__':
    main()
