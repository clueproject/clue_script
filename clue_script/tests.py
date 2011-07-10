import argparse
import unittest

from clue_script import command, Command, Commander, PseudoCommand


class CommandDecoratorTests(unittest.TestCase):
    def test_foo(self):
        @command()
        def f():
            pass
        assert hasattr(f, '__clue_script_command')


class CommanderTests(unittest.TestCase):

    def test_add(self):
        commander = Commander()
        commander.add(lambda: None)
        assert isinstance(commander.commands.values()[0], PseudoCommand)

        class MockCommand(Command):
            def run(self, argv): pass
        commander.add(MockCommand())
        assert isinstance(commander.commands.values()[1], MockCommand)

    def test_run(self):
        class MockCommander(Commander):
            usage_displayed = False
            invalid = False
            def print_usage(self): self.usage_displayed = True
            def invalid_command_trigger(self, s): self.invalid = True
        commander = MockCommander()
        commander.run([])
        assert commander.usage_displayed

        commander = MockCommander()
        commander.run(['foo'])

        commander = MockCommander()
        def bar(): pass
        commander.add(bar)
        commander.run(['bar'])
        assert commander.usage_displayed is False
        assert commander.invalid is False


class CommandTests(unittest.TestCase):

    def test_complex_command(self):

        ran = []

        def foo(*argv):
            parser = argparse.ArgumentParser()
            parser.add_argument('-x', help='simple test',
                                default='yes', metavar='x')
            ns = parser.parse_args(argv)
            ran.append(ns)

        command = PseudoCommand(foo)
        assert command.__name__ is 'foo'

        command.run([])
        ns = ran.pop()
        assert ns.x is 'yes'

        command.run(['-x', 'abc'])
        ns = ran.pop()
        assert ns.x is 'abc'


class MockSession(object):
    committed = False
    rolled_back = False
    def close(self): pass
    def commit(self): self.committed = True
    def rollback(self): self.rolled_back = True
