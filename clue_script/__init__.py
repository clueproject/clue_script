from __future__ import print_function

import abc
import argparse
import logging
import os
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


class OrderedDict(dict):

    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.ordered = []

    def __setitem__(self, k, v):
        if k not in self.ordered:
            self.ordered.append(k)
        dict.__setitem__(self, k, v)

    def keys(self):
        return self.ordered

    def items(self):
        return [(x, self[x]) for x in self.keys()]

    def values(self):
        return [self[x] for x in self.keys()]


class Command(object):
    '''Base class for commands, provides support for setting up default
    logger.
    '''

    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def __name__(self):
        pass

    def __init__(self, logger=None):
        self.logger = logger
        if logger is None:
            self.logger = logging.getLogger(
                '%s.%s' % (__package__, self.__name__))
            self.logger.setLevel(logging.INFO)

    @abc.abstractmethod
    def run(self, argv):
        pass


class Commander(Command):
    '''A command that knows how to run sub-commands.

    :param initial_commands: an iterable of commands to start with
    '''

    __name__ = 'commander'

    def __init__(self, initial_commands=None, prog=None):
        # copy the iterable as our base list
        self.commands = OrderedDict([(x.__name__, x)
                                     for x in initial_commands or []])
        self.prog = prog

    def add(self, cmd):
        '''Add the given subcommand'''

        if not isinstance(cmd, Command):
            cmd = PseudoCommand(cmd)
        self.commands[cmd.__name__] = cmd

    def print(self, *args, **kwargs):
        '''Mostly provided as an easy way to override output'''

        print(*args, **kwargs)

    def run(self, argv=sys.argv[1:]):
        prog = self.prog
        if not prog and len(sys.argv) >= 1:
            prog = os.path.basename(sys.argv[0])

        if len(argv) == 0 or argv[0] in ('-h', '--help'):
            self.print_usage(prog)
            return

        cmd = self.commands.get(argv[0])
        if cmd is None:
            self.print()
            self.print('  ERROR: Not a valid command: %s' % argv[0])
            self.print_usage(prog)
            return

        cmd.run(argv[1:])

    def print_usage(self, prog):
        parser = argparse.ArgumentParser(prog=prog)
        parser.add_argument('command',
                            help='One of the commands to run',
                            default='foo',
                            nargs='?')
        parser.print_help()
        self.print_commands_usage()

    def print_commands_usage(self):
        prog = self.prog
        if not prog and len(sys.argv) >= 1:
            prog = os.path.basename(sys.argv[0])

        screen_width = int(os.environ.get('COLUMNS', 75))
        self.print()
        line = textwrap.fill('note: run any of the commands with a trailing '
                             '--help to get extended information about the '
                             'command',
                             subsequent_indent='      ',
                             width=screen_width)
        self.print(line)

        self.print()
        self.print('commands:')
        self.print()

        max_len = -1
        for name in self.commands:
            if len(name) > max_len:
                max_len = len(name)

        if max_len > 20:
            max_len = 20

        for name, command in self.commands.items():
            line = name
            line += ' ' * (max_len - len(line))
            line += '    '

            doc = self._get_doc(command)
            line += ' '.join([x.strip() for x in doc.split('\n')])
            line = textwrap.dedent(line).strip()
            line = textwrap.fill(line, initial_indent='  ',
                                 subsequent_indent=' ' * (max_len + 6),
                                 width=screen_width)

            self.print(line)

    def _get_doc(self, command):
        s = getattr(command, '__doc__', '')
        period = s.find('.')
        if period > -1:
            return s[0:period]
        return s

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
        self.name = name or getattr(func, '__name__')
        self.__doc__ = doc or func.__doc__

    def run(self, argv):
        self.func(*argv)

    @property
    def __name__(self):
        return self.name


def command(*args, **kwargs):
    '''A decorator that marks the given function as being command-able'''

    def command(f, kwargs=kwargs):
        f.__clue_script_command = True
        f.__clue_script_kwargs = kwargs

    if len(args) > 0:
        return command(args[0])

    return command
