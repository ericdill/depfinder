from setuptools import setup, find_packages
import versioneer

required = open('requirements.txt').read().split('\n')

setup(
    name='depfinder',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    author='Eric Dill',
    author_email='thedizzle@gmail.com',
    packages=find_packages(exclude="test"),
    description='Find all the imports in your library',
    url='http://github.com/ericdill/depfinder',
    platforms='Cross platform (Linux, Mac OSX, Windows)',
    install_requires=required,
    license='BSD 3-Clause',
    entry_points={"console_scripts": ['depfinder = depfinder.cli:cli']},
    package_data={'': ['pkg_data/*.yml']},
)
