Futon Proxy
===========

A simple HTTP proxy to aid in hacking on Futon. Just start this up and
point it at a checkout of couchdb/share/www to give yourself a dev environment.

By default it requires a CouchDB node running at 127.0.0.1:5985 but you
can set that at the command line.

If you don't specify a Futon directory, the current directory is used.

If you have problems, feel free to email me.

Help Output
===========

    $ ./futonproxy.py -h
    Usage: futonproxy.py [OPTIONS] [futon_directory]

    Options:
      -a ADDRESS, --address=ADDRESS
                            IP to use for client connections.
      -p PORT, --port=PORT  Port to use for client connections.
      -c COUCH, --couch=COUCH
                            The base URL of a running CouchDB node.
      -h, --help            show this help message and exit


License
=======

Tumbolia Public License

See the LICENSE file for more info.