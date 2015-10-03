from setuptools import setup
import depfinder

setup(name='depfinder',
      version=depfinder.__version__,
      author='Eric Dill',
      author_email='thedizzle@gmail.com',
      py_modules=['depfinder'],
      description='Find all the imports in your library',
      url='http://github.com/ericdill/depfinder',
      platforms='Cross platform (Linux, Mac OSX, Windows)',
      install_requires=['stdlib_list', 'setuptools'],
)
