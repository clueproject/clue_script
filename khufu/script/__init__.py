import abc
import argparse
import logging
import StringIO
import sys
import textwrap
import pkg_resources

__version__ = pkg_resources.get_distribution('Khufu-Script').version


class Command(object):

    __metaclass__ = abc.ABCMeta

    _logger_name = __name__

    def __init__(self, logger=None):
        self.logger = logger
        if logger is None:
            self.logger = logging.getLogger(self._logger_name)
            self.logger.setLevel(logging.INFO)
        self._logger_name = self.logger.name

    def run(self, options):
        logging.basicConfig()
        self.do_work(options)

    @abc.abstractproperty
    def __name__(self): pass

    @abc.abstractmethod
    def do_work(self, options): pass

class SimpleObject(object):
    pass

class ReloadableServerCommand(Command):
    '''Run a reloadable development web server.
    '''

    _logger_name = __name__ + '.server'

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
        self.wsgi_serve(application=app, host=ns.host, port=ns.port)

    def wsgi_serve(self, application, host, port):
        # lazily loading paste stuff and defining the class to reduce dependencies
        from paste import httpserver
        logger = self.logger
        class WSGIHandler(httpserver.WSGIHandler, object): 
            def wsgi_execute(self, environ=None):
                super(WSGIHandler, self).wsgi_execute(environ=environ)
                environ = self.wsgi_environ
                logger.info('%s %s%s' % (environ['REQUEST_METHOD'],
                                         environ['SCRIPT_NAME'],
                                         environ['PATH_INFO']))

        class WSGIServer(httpserver.WSGIServer, object):
            server_version = 'PasteWSGIServer+Khufu/' + __version__

            def __init__(self, application, host, port):
                super(WSGIServer, self).__init__(application, (host, port), WSGIHandler)

            def handle_error(self, request, client_address):
                exc_class, exc, tb = sys.exc_info()
                if exc_class is httpserver.ServerExit:
                    # This is actually a request to stop the server
                    raise
                logger.exception('Unhandled exception')

        server = WSGIServer(application, host, port)
        self.logger.info('Listening on: %s:%s' % (host, port))
        server.serve_forever()

class SyncDBCommand(Command):
    '''Update the database.
    '''

    __name__ = 'syncdb'

    def __init__(self, session_factory, *update_callables):
        self.session_factory = session_factory
        self.update_callables = update_callables

    def do_work(self, argv):
        session = self.session_factory()
        try:
            for x in self.update_callables:
                x(session)
        except:
            session.rollback()
            raise
        else:
            session.commit()
        finally:
            session.close()

def display_usage(commands):
    s = StringIO.StringIO()
    print >> s, 'Commands:'
    for x in commands:
        print >> s, '   ', x.__name__, '   ', (x.__doc__ or '').strip()
    for x in s.getvalue().split('\n'):
        print textwrap.fill(x)

def find_command(s, commands):
    for x in commands:
        if x.__name__ == s:
            return x
    return None

def run(argv=sys.argv[1:], commands=[]):
    if len(argv) == 0:
        display_usage(commands)
        return

    cmd = find_command(argv[0], commands)
    if cmd is None:
        print 'Not a valid command: %s' % argv[0]
        print
        display_usage(commands)
        return

    cmd.run(argv[1:])
