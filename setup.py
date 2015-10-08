from setuptools import setup
VERSION = 'v1.0.0'
setup(name='depfinder',
      version=VERSION,
      author='Eric Dill',
      author_email='thedizzle@gmail.com',
      py_modules=['depfinder'],
      description='Find all the imports in your library',
      url='http://github.com/ericdill/depfinder',
      platforms='Cross platform (Linux, Mac OSX, Windows)',
      install_requires=['stdlib_list', 'setuptools'],
)
