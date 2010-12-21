import abc
import logging
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

    def run(self, argv):
        logging.basicConfig()
        self.do_work(argv)

    @abc.abstractproperty
    def __name__(self): pass

    @abc.abstractmethod
    def do_work(self, argv): pass
