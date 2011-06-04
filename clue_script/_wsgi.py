import argparse
import os
import subprocess
import sys
import logging

from paste import httpserver, reloader

from clue_script import Command, __version__


prog_prefix = os.path.basename(sys.argv[0])


class ReloadableServerCommand(Command):
    '''Launch web server to serve this application.
    '''

    _logger_name = __package__ + '.server'

    __name__ = 'runserver'

    defaults = {
        'host': '0.0.0.0',
        'port': '8080',
        'with_reloader': 1,
        }

    use_rfoo = False
    rfoo_namespace = None

    def __init__(self, app_factory=None, application=None, logger=None):
        super(ReloadableServerCommand, self).__init__(logger)
        if application is not None:
            self.application = application
        elif app_factory is not None:
            self.application = app_factory()
        else:
            raise ValueError('Must specify one of "app_factory" or "app"')

        self.rfoo_namespace = {}

        self.parser = parser = \
            argparse.ArgumentParser(prog=prog_prefix + ' ' + self.__name__,
                                    description=self.__doc__)
        parser.add_argument('-i', '--host',
                            help=('Host/IP/Interface to listen on, '
                                  'specify 0.0.0.0 '
                                  'for all available interfaces '
                                  '(default: %(default)s)'),
                            default=self.defaults['host'], metavar='host')
        parser.add_argument('-p', '--port', type=int,
                            help='Port to listen on (default: %(default)s)',
                            default=self.defaults['port'], metavar='port')
        parser.add_argument('--with-reloader', nargs='?',
                            help=('1 to watch for code changes and restart '
                                  'as necessary (default: %(default)s)'),
                            default=self.defaults['with_reloader'])

    def run(self, argv):
        ns = self.parser.parse_args(argv)
        ns.with_reloader = bool(int(ns.with_reloader))

        runner = WSGIAppRunner(application=self.application,
                               host=ns.host,
                               port=ns.port, logger=self.logger,
                               use_rfoo=self.use_rfoo,
                               rfoo_namespace=self.rfoo_namespace)
        runner.wsgi_serve(with_reloader=ns.with_reloader)


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
    server_version = 'PasteWSGIServer+clue_script/' + __version__

    def __init__(self, application, host, port, logger):
        super(WSGIServer, self).__init__(application, (host, port),
                                         self.wsgi_handler)
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

    _reloader_key = 'CLUE_SCRIPT_RELOADER'
    rfoo_port = 54321

    def __init__(self, application, host, port, logger=None,
                 use_rfoo=False, rfoo_namespace={}):
        self.application = application
        self.host = host
        self.port = port
        self.logger = logger or logging.getLogger('clue_script.unused')
        self.use_rfoo = use_rfoo
        self.rfoo_namespace = rfoo_namespace

    def wsgi_serve(self, with_reloader):
        if not with_reloader or self._reloader_key not in os.environ:
            self.logger.info('Listening on: %s:%s' % (self.host, self.port))

        if self._reloader_key in os.environ:
            self.logger.info('Monitoring code files')
            reloader.install()

        if self._reloader_key in os.environ or not with_reloader:
            if self.use_rfoo:
                from rfoo.utils import rconsole
                rconsole.spawn_server(self.rfoo_namespace, self.rfoo_port)
                self.logger.info('Rfoo listening on port %i' % self.rfoo_port)
            server = WSGIServer(self.application, self.host,
                                self.port, self.logger)
            server.serve_forever()
            return

        self.restart_with_reloader()

    def restart_with_reloader(self):
        self.logger.info('Starting subprocess with reloader')

        while True:
            args = [self.quote_first_command_arg(sys.executable)] + sys.argv
            new_environ = os.environ.copy()
            new_environ[self._reloader_key] = 'true'

            proc = None
            try:
                try:
                    _turn_sigterm_into_systemexit()
                    proc = subprocess.Popen(args, env=new_environ)
                    exit_code = proc.wait()
                    proc = None
                except KeyboardInterrupt:
                    return 1
            finally:
                if (proc is not None
                    and hasattr(os, 'kill')):
                    import signal
                    try:
                        os.kill(proc.pid, signal.SIGTERM)
                    except (OSError, IOError):
                        pass

            if exit_code != 3:
                return exit_code

            self.logger.info('reloading code, restarting server process')

    def quote_first_command_arg(self, arg):
        """
        There's a bug in Windows when running an executable that's
        located inside a path with a space in it.  This method handles
        that case, or on non-Windows systems or an executable with no
        spaces, it just leaves well enough alone.
        """
        if (sys.platform != 'win32'
            or ' ' not in arg):
            # Problem does not apply:
            return arg
        try:
            import win32api
        except ImportError:
            raise ValueError(
                "The executable %r contains a space, and in order to "
                "handle this issue you must have the win32api module "
                "installed" % arg)
        arg = win32api.GetShortPathName(arg)
        return arg


def _turn_sigterm_into_systemexit():
    """
    Attempts to turn a SIGTERM exception into a SystemExit exception.
    """
    try:
        import signal
    except ImportError:
        return

    def handle_term(signo, frame):
        raise SystemExit
    signal.signal(signal.SIGTERM, handle_term)
