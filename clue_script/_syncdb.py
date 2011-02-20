from clue_script import Command


class SyncDBCommand(Command):
    '''Update the database.
    '''

    __name__ = 'syncdb'

    def __init__(self, session_factory, *update_callables):
        self.session_factory = session_factory
        self.update_callables = update_callables

    def run(self, argv):
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
