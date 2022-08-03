


.. depfinder documentation master file, created by
   sphinx-quickstart on Wed Oct  7 22:23:01 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

depfinder
=========

.. image:: https://github.com/ericdill/depfinder/actions/workflows/tests.yml/badge.svg
   :target: https://github.com/ericdill/depfinder/actions/workflows/tests.yml
.. image:: http://codecov.io/github/ericdill/depfinder/coverage.svg?branch=master
   :target: http://codecov.io/github/ericdill/depfinder?branch=master

- `docs <https://ericdill.github.io/depfinder>`_
- `github repo <https://github.com/ericdill/depfinder>`_

Installation
------------

``depfinder`` is on pypi. It is tested against Python 2.7 and 3.6-3.8.

    pip install depfinder

It is available via conda. ::

    conda install -c conda-forge depfinder

It is also via github. ::

    git clone git@github.com:ericdill/depfinder
    cd depfinder
    python setup.py install

or ::

    pip install https://github.com/ericdill/depfinder/zipball/master#egg=depfinder



Using depfinder
---------------

::

    $ depfinder -h
    usage: depfinder [-h] [-y] [-V] [--no-remap] [-v] [-q] [-k KEY] [--conda]
                 [--pdb]
                 file_or_directory

    Tool for inspecting the dependencies of your python project.

    positional arguments:
      file_or_directory  Valid options are a single python file, a single jupyter
                         (ipython) notebook or a directory of files that include
                         python files

    optional arguments:
      -h, --help         show this help message and exit
      -y, --yaml         Output in syntactically valid yaml when true. Defaults to
                         False
      -V, --version      Print out the version of depfinder and exit
      --no-remap         Do not remap the names of the imported libraries to their
                         proper conda name
      -v, --verbose      Enable debug level logging info from depfinder
      -q, --quiet        Turn off all logging from depfinder
      -k KEY, --key KEY  Select some or all of the output keys. Valid options are
                         'required', 'optional', 'builtin', 'relative', 'all'.
                         Defaults to 'all'
      --conda            Format output so it can be passed as an argument to conda
                         install or conda create
      --pdb              Enable PDB debugging on exception

Ok, great. That's the help output.  Not super helpful.  What does the output of
depfinder look like when we run it on the source code for depfinder?

::

    $ depfinder depfinder
    {'builtin': ['__future__',
                 'argparse',
                 'ast',
                 'collections',
                 'copy',
                 'errno',
                 'json',
                 'logging',
                 'os',
                 'pprint',
                 're',
                 'subprocess',
                 'sys'],
     'relative': ['_version', 'main'],
     'required': ['pyyaml', 'stdlib-list']}

So, what do these things mean?  Well `builtin` are modules that are built in to
the standard library.  `required` are modules that are not from the standard
library or from within the `depfinder` package and `relative` are modules that
are imported from one module to another within the `depfinder` source code.

`Also see this notebook <https://github.com/ericdill/depfinder/blob/master/depfinder_usage.ipynb>`_


Description
-----------

Find all the unique imports in your library, automatically, because who likes
do it by hand?  `depfinder <https://github.com/ericdill/depfinder>`_ uses the `ast
<https://docs.python.org/2/library/ast.html>`_ (Abstract Syntax Tree) module
(and `more ast docs <https://greentreesnakes.readthedocs.io/en/latest/>`_) to find
all :py:class:`ast.Try` and :py:class:`ast.ImportFrom` nodes.  These
:py:class:`ast.Import` and :py:class:`ast.ImportFrom` nodes are then grouped
according to the following categories, in order of decreasing precedence:

* **relative**
    The import is a relative import from within the same library

* **builtin**
    The import is built into the standard library, as determined by scraping the
    official python docs for the builtins with `stdlib-list
    <https://github.com/jackmaney/python-stdlib-list>`_

* **questionable**
    The import occurs inside any combination of

    - :py:class:`ast.Try` (:py:class:`ast.TryExcept` on py27)
    - :py:class:`ast.FunctionDef`
    - :py:class:`ast.ClassDef`

    The module may be importable without these imports, but the it will likely
    not have full functionality.

* **required**
    The import occurs at the top level of the module and will get executed
    when the module is imported. These imports must be accounted for in an
    environment, or the module will not be importable.

Testing
-------

It has dependencies on, `stdlib-list
<https://github.com/jackmaney/python-stdlib-list>`_ and `pyyaml
<https://pyyaml.org/wiki/PyYAML>`_. I use ``stdlib-list`` to get the list of
libraries built in to the standard library. These requirements can be installed
via pip ::

    pip install -r requirements.txt

Also install the test-requiements ::

    pip install -r test-requirements.txt

Then you can run the tests from the root of the git repository ::

    coverage run run_tests.py

API
====
.. currentmodule:: depfinder.main
.. autofunction:: get_imported_libs
.. autofunction:: iterate_over_library
.. autofunction:: simple_import_search

IPython/Jupyter Notebook support
================================
``depfinder`` has support for v4 Jupyter notebooks.

.. autofunction:: notebook_path_to_dependencies
