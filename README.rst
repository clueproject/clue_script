.. -*-rst-*-

=============
 clue_script
=============

Overview
========

clue_script is used for defining subcommands with a special focus on
web-style apps.  The functionality is inspired by the Django ``manage.py``
script.

Requirements
============

  * Python 2.6 or 2.7 (not tested with Python 3.x)


runserver support (optional)
----------------------------

  * Paste
  * argparse *(if deploying on Python < 2.7)*


Usage
=====

A simple example to add a command that prints "hello world"::

  from clue_script import command, Commander

  @command
  def helloworld():
      print 'hello world'

  if __name__ == '__main__':
      Commander.scan(globals()).run()

To do a more complicated command you can use something similar to
Python 2.7's ``argparse`` (also available on 2.6).
::

  import argparse
  from clue_script import command, Commander

  @command
  def foo(*argv):
      parser = argparse.ArgumentParser()
      parser.add_argument('-x', help='simple test',
                          default='yes', metavar='x')
      ns = parser.parse_args(argv)
      # do something

  if __name__ == '__main__':
      Commander.scan(globals()).run()

Provided Commands
=================

There are currently two provided command factories.

  1. ``make_reloadable_server_command`` *(see above note about requirements for runserver)*

  2. ``make_syncdb_command``

A typical web app could use these commands as follows::

  if __name__ == '__main__':
      def createtables(session):
          models.Base.metadata.create_all(session.bind)
  
      settings = init_settings()
      commander = script.Commander([script.make_reloadable_server_command(make_app),
                                    script.make_syncdb_command(settings['spitter.db_session_factory'],
                                                               createtables)])
      commander.scan(globals())
      commander.run()

Running the script with no args will yield something similar to::

  Commands:
      runserver     Run a reloadable development web server.
      syncdb        Update the database.

Credits
=======

  * Developed and maintained by Rocky Burt <rocky AT serverzen DOT com>
