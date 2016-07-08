


.. depfinder documentation master file, created by
   sphinx-quickstart on Wed Oct  7 22:23:01 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

depfinder
=========

.. image:: https://travis-ci.org/ericdill/depfinder.svg?branch=master
   :target: https://travis-ci.org/ericdill/depfinder
.. image:: http://codecov.io/github/ericdill/depfinder/coverage.svg?branch=master
   :target: http://codecov.io/github/ericdill/depfinder?branch=master

- `docs <https://ericdill.github.io/depfinder>`_
- `github repo <https://github.com/ericdill/depfinder>`_

Using depfinder
---------------
::

    $ depfinder depfinder.py
    {'builtin': ['__future__',
                 'argparse',
                 'ast',
                 'collections',
                 'json',
                 'os',
                 'pprint',
                 'sys'],
     'required': ['stdlib_list', 'yaml']}

`Also see this notebook <https://github.com/ericdill/depfinder/blob/master/depfinder_usage.ipynb>`_


Description
-----------

Find all the unique imports in your library, automatically, because who likes
do it by hand?  `depfinder <https://github.com/ericdill/depfinder>`_ uses the `ast
<https://docs.python.org/2/library/ast.html>`_ (Abstract Syntax Tree) module
(and `more ast docs <https://greentreesnakes.readthedocs.org/en/latest/>`_) to find
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

Installation
------------

``depfinder`` is on pypi. It is tested against Python 2.7, 3.3, 3.4 and 3.5.  ::

    pip install depfinder

It is available via conda. ::

    conda install -c ericdill depfinder

It is also via github. ::

    git clone git@github.com:ericdill/depfinder
    cd depfinder
    python setup.py install

or ::

    pip install https://github.com/ericdill/depfinder/zipball/master#egg=depfinder


It has one dependency, `stdlib_list
<https://github.com/jackmaney/python-stdlib-list>`_, which is where I get the
list of libraries built in to the standard library. ``stdlib-list`` can be
installed via pip ::

    pip install stdlib-list

or conda ::

    conda install -c ericdill stdlib-list

API
====
.. currentmodule:: depfinder
.. autofunction:: get_imported_libs
.. autofunction:: iterate_over_library
.. autofunction:: simple_import_search

IPython/Jupyter Notebook support
================================
``depfinder`` has support for v4 Jupyter notebooks.

.. autofunction:: notebook_path_to_dependencies
