import argparse
import os
import sys
from Queue import Empty
from multiprocessing import Process, Queue, Event, active_children

from paste import httpserver

from khufu.script._base import __version__, Command

class ReloadableServerCommand(Command):
    '''Run a reloadable development web server.
    '''

    _logger_name = __package__ + '.server'

    __name__ = 'runserver'

    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--host', help='Host/IP to listen on, specify 0.0.0.0 for all available interfaces',
                        default='0.0.0.0', metavar='host')
    parser.add_argument('-p', '--port', type=int,
                        help='Port to listen on, defaults to 8080',
                        default=8080, metavar='port')
    parser.add_argument('--with-reloader', action='store_true',
                        help='Watch for code changes and restart as necessary',
                        default=False)

    def __init__(self, app_factory, logger=None):
        super(ReloadableServerCommand, self).__init__(logger)
        self.app_factory = app_factory

    def do_work(self, argv):
        ns = self.parser.parse_args(argv)
        app = self.app_factory()
        WSGIAppRunner(self.logger).wsgi_serve(application=app, host=ns.host, port=ns.port,
                                              with_reloader=ns.with_reloader)

class WSGIHandler(httpserver.WSGIHandler, object): 

    def __init__(self, logger, *args, **kwargs):
        self.logger = logger
        super(WSGIHandler, self).__init__(*args, **kwargs)

    def wsgi_execute(self, environ=None):
        super(WSGIHandler, self).wsgi_execute(environ=environ)
        environ = self.wsgi_environ
        self.logger.info('%s %s%s' % (environ['REQUEST_METHOD'],
                                      environ['SCRIPT_NAME'],
                                      environ['PATH_INFO']))

class WSGIServer(httpserver.WSGIServer, object):
    server_version = 'PasteWSGIServer+Khufu/' + __version__

    def __init__(self, application, host, port, logger):
        super(WSGIServer, self).__init__(application, (host, port), self.wsgi_handler)
        self.logger = logger

    def handle_error(self, request, client_address):
        exc_class, exc, tb = sys.exc_info()
        if exc_class is httpserver.ServerExit:
            # This is actually a request to stop the server
            raise
        self.logger.exception('Unhandled exception')

    def wsgi_handler(self, *args, **kwargs):
        return WSGIHandler(self.logger, *args, **kwargs)

class WSGIAppRunner(object):

    def __init__(self, logger = None):
        self.logger = logger or logging.getLogger('unused')

    def wsgi_serve(self, application, host, port, with_reloader):
        logger = self.logger
        server = WSGIServer(application, host, port, logger)
        self.logger.info('Listening on: %s:%s' % (host, port))

        if not with_reloader:
            server.serve_forever()
            return

        tx = Queue()

        def spinup():
            rx = Event()
            worker = Process(target=self._process_handler,
                             args=(server, tx, rx))
            worker.rx = rx
            worker.start()
            return worker

        spinup()

        while True:
            try:
                msg = tx.get(True, 1)
                if msg['status'] == 'changed':
                    logger.info('code reloaded')
                    spinup()
                elif msg['status'] == 'loaded':
                    for worker in active_children():
                        if worker.ident != msg['pid']:
                            worker.rx.set()
            except Empty:
                if not active_children():
                    return

    def _process_handler(self, server, tx, rx):
        from threading import Thread
        from reloadwsgi import Monitor
        try:
            tx.put({'pid':os.getpid(), 'status':'loaded'})
            t = Thread(target=server.serve_forever)
            t.setDaemon(True)
            t.start()
            monitor = Monitor(tx=tx, rx=rx)
            monitor.periodic_reload()
        except KeyboardInterrupt:
            pass

