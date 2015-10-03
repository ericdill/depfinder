from setuptools import setup

setup(name='depfinder',
      version='0.0.1',
      author='Eric Dill',
      author_email='thedizzle@gmail.com',
      py_modules=['depfinder'],
      description='Find all the imports in your library',
      url='http://github.com/ericdill/depfinder',
      platforms='Cross platform (Linux, Mac OSX, Windows)',
      install_requires=['stdlib_list', 'setuptools'],
)
