import argparse
import unittest

from khufu.script import command, Command, Commander, PseudoCommand

class CommandDecoratorTests(unittest.TestCase):
    def test_foo(self):
        @command
        def f():
            pass
        assert hasattr(f, '__khufu_command')

class CommanderTests(unittest.TestCase):

    def test_add(self):
        commander = Commander()
        commander.add(lambda: None)
        assert isinstance(commander._commands[0], PseudoCommand)

        class MockCommand(Command):
            def do_work(self, argv): pass
        commander.add(MockCommand())
        assert isinstance(commander._commands[1], MockCommand)

    def test_do_work(self):
        class MockCommander(Commander):
            usage_displayed = False
            invalid = False
            def display_usage(self): self.usage_displayed = True
            def invalid_command_trigger(self, s): self.invalid = True
        commander = MockCommander()
        commander.do_work([])
        assert commander.usage_displayed

        commander = MockCommander()
        commander.do_work(['foo'])
        assert commander.usage_displayed is False
        assert commander.invalid

        commander = MockCommander()
        def bar(): pass
        commander.add(bar)
        commander.do_work(['bar'])
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
