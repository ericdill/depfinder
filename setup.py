from setuptools import setup

VERSION = '1.1.2'

required = open('requirements.txt').read().split('\n')

setup(name='depfinder',
      version=VERSION,
      author='Eric Dill',
      author_email='thedizzle@gmail.com',
      py_modules=['depfinder'],
      description='Find all the imports in your library',
      url='http://github.com/ericdill/depfinder',
      platforms='Cross platform (Linux, Mac OSX, Windows)',
      install_requires=required,
      license='GPLv3',
      entry_points = {"console_scripts": ['depfinder = depfinder:cli']},
)
