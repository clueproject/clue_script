from __future__ import print_function

import StringIO
import sys
import textwrap

from khufu.script._base import __version__, Command

def display_usage(commands):
    s = StringIO.StringIO()
    print('Commands:', file=s)
    for x in commands:
        print('    ' + x.__name__ + '     ' + (x.__doc__ or '').strip(), file=s)
    for x in s.getvalue().split('\n'):
        print(textwrap.fill(x), file=s)

def find_command(s, commands):
    for x in commands:
        if x.__name__ == s:
            return x
    return None

def make_reloadable_server_command(*args, **kwargs):
    from khufu.script._wsgi import ReloadableServerCommand
    return ReloadableServerCommand(*args, **kwargs)

def make_syncdb_command(*args, **kwargs):
    from khufu.script._syncdb import SyncDBCommand
    return SyncDBCommand(*args, **kwargs)   

def run(argv=sys.argv[1:], commands=[]):
    if len(argv) == 0:
        display_usage(commands)
        return

    cmd = find_command(argv[0], commands)
    if cmd is None:
        print('Not a valid command: %s' % argv[0])
        print()
        display_usage(commands)
        return

    cmd.run(argv[1:])
