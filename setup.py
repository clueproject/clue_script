import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.txt')).read()
CHANGES = open(os.path.join(here, 'CHANGES.txt')).read()

requires = ['setuptools']

try:
    import argparse
except ImportError:
    requires.append('argparse')

setup(name='Khufu-Script',
      version='0.2.2',
      description='Khufu component for defining subcommands',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python",
        "Topic :: Internet :: WWW/HTTP :: WSGI",
        ],
      license='BSD',
      author='Rocky Burt',
      author_email='rocky@serverzen.com',
      namespace_packages=['khufu'],
      url='https://github.com/serverzen/Khufu-Script',
      keywords='web',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      test_suite="khufu.script.tests",
      entry_points="",
      )
