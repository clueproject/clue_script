import argparse
import os
import subprocess
import sys
import logging

from paste import httpserver, reloader

from clue_script import Command, __version__


class ReloadableServerCommand(Command):
    '''Run a reloadable development web server.
    '''

    _logger_name = __package__ + '.server'

    __name__ = 'runserver'

    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--host',
                        help=('Host/IP to listen on, specify 0.0.0.0 '
                              'for all available interfaces'),
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

    def run(self, argv):
        ns = self.parser.parse_args(argv)
        app = self.app_factory()
        runner = WSGIAppRunner(application=app, host=ns.host,
                               port=ns.port, logger=self.logger)
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

    def __init__(self, application, host, port, logger=None):
        self.application = application
        self.host = host
        self.port = port
        self.logger = logger or logging.getLogger('clue_script.unused')

    def wsgi_serve(self, with_reloader):
        if not with_reloader or self._reloader_key not in os.environ:
            self.logger.info('Listening on: %s:%s' % (self.host, self.port))

        if self._reloader_key in os.environ:
            self.logger.info('Monitoring code files')
            reloader.install()

        if self._reloader_key in os.environ or not with_reloader:
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
