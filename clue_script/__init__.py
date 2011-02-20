from __future__ import print_function

import abc
import logging
import StringIO
import sys
import textwrap

import pkg_resources

try:
    __version__ = pkg_resources.get_distribution('clue_script').version
except:
    __version__ = 'dev'

def make_reloadable_server_command(*args, **kwargs):
    '''Create a new runserver command'''

    from clue_script._wsgi import ReloadableServerCommand
    return ReloadableServerCommand(*args, **kwargs)

def make_syncdb_command(*args, **kwargs):
    '''Create a new syncdb command'''

    from clue_script._syncdb import SyncDBCommand
    return SyncDBCommand(*args, **kwargs)   

class Command(object):
    '''Base class for commands, provides support for setting up default
    logger.
    '''

    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def __name__(self): pass

    def __init__(self, logger=None):
        self.logger = logger
        if logger is None:
            self.logger = logging.getLogger('%s.%s' % (__package__, self.__name__))
            self.logger.setLevel(logging.INFO)

    @abc.abstractmethod
    def run(self, argv): pass

class Commander(Command):
    '''A command that knows how to run sub-commands.

    :param initial_commands: an iterable of commands to start with
    '''

    __name__ = 'commander'

    def __init__(self, initial_commands=None):
        # copy the iterable as our base list
        self._commands = [x for x in initial_commands or []]

    def add(self, cmd):
        '''Add the given subcommand'''

        if not isinstance(cmd, Command):
            cmd = PseudoCommand(cmd)
        self._commands.append(cmd)

    def print(self, *args, **kwargs):
        '''Mostly provided as an easy way to override output'''

        print(*args, **kwargs)

    def invalid_command_trigger(self, s):
        '''Fired when an incorrect command is executed'''

        self.print()
        self.print('Not a valid command: %s' % s)
        self.print()
        self.print_usage()

    def run(self, argv=sys.argv[1:]):
        if len(argv) == 0:
            self.print_usage()
            return

        cmd = self.find_command(argv[0])
        if cmd is None:
            self.invalid_command_trigger(argv[0])
            return

        cmd.run(argv[1:])

    def print_usage(self):
        self.print('Commands:')
        for x in self._commands:
            name = x.__name__
            c = (20-len(name))
            if c < 2:
                spaces = '  '
            else:
                spaces = (c * ' ') + '  '
            line = '    %s%s%s' % (x.__name__, spaces, (x.__doc__ or '').strip())
            self.print(textwrap.fill(line))

    def find_command(self, s):
        for x in self._commands:
            if x.__name__ == s:
                return x
        return None

    @classmethod
    def scan(cls, ns=globals()):
        '''A constructor for Commander that will scan the given dict
        for functions marked with the command decorator and register
        them as new commands.
        '''

        commander = cls()
        for k, v in ns.items():
            if hasattr(v, '__clue_script_command'):
                commander.add(PseudoCommand(v))
        return commander

class PseudoCommand(Command):
    '''A simple command that acts as a proxy for any sort
    of callable.
    '''

    def __init__(self, func, name=None, doc=None):
        if not callable(func):
            raise TypeError('First argument must be a callable')

        self.func = func
        self.name = name or func.__name__
        self.__doc__ = doc or func.__doc__

    def run(self, argv):
        self.func(*argv)

    @property
    def __name__(self):
        return self.name

def command(f):
    '''A decorator that marks the given function as being command-able'''

    f.__clue_script_command = True
    return f
