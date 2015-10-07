.. image:: https://travis-ci.org/ericdill/depfinder.svg?branch=master
    :target: https://travis-ci.org/ericdill/depfinder
.. image:: http://codecov.io/github/ericdill/depfinder/coverage.svg?branch=master
    :target: http://codecov.io/github/ericdill/depfinder?branch=master
.. image:: https://coveralls.io/repos/ericdill/depfinder/badge.svg?branch=master&service=github
    :target: https://coveralls.io/github/ericdill/depfinder?branch=master


depfinder
---------
Find all the unique imports in your library, automatically, because who likes
do it by hand?  ``depfinder`` uses the `ast (Abstract Syntax Tree) module
<https://docs.python.org/2/library/ast.html>`_ `(and more docs)
<https://greentreesnakes.readthedocs.org/en/latest/>`_ to find all ``ast.Import``
and ``ast.ImportFrom`` nodes.  These ``ast.Import`` and ``ast.ImportFrom`` nodes
are then grouped according to the following categories, in order of decreasing
precedence:

- ``relative``. The import is a relative import from within the same library

- ``builtin``. The import is built into the standard library.

- ``questionable``.The import occurs inside of an ``ast.Try`` (``ast.TryExcept`` on py27) node.

- ``required``. The import occurs at the top level of the module and will get executed when the
module is imported.


There are only a few functions in ``depfinder``.

- ``get_imported_libs``

  Accepts code (as a string) as input and returns all imported libraries in
  that code snippet in a dictionary keyed on the categories listed above
  (relative, builtin, questionable, required)

- ``iterate_over_library``

  Accepts ``path_to_source_code`` as input and yields a tuple of
  (module_name, full_path_to_module, depfinder.ImportCatcher object) for each
  python file that was recursively found inside of ``path_to_source_code``.

- ``simple_import_search``

  Accepts ``path_to_source_code`` as input and aggregates the output of
  ``iterate_over_library`` into a dictionary keyed on the categories listed
  above (``relative``, ``builtin``, ``questionable``, ``required``)

- ``notebook_path_to_dependencies``

  Accepts a path to a v4 IPython notebook, parses all code cells with
  **get_imported_libs** and aggregates all found imports into a dictionary
  keyed on the categories listed above (``relative``, ``builtin``,
  ``questionable``, ``required``)


Installation
------------

``depfinder`` is not yet on pypi. It is tested against Python 2.7, 3.3, 3.4 and
3.5. It is available via github. For now, clone it from https://github.com/ericdill/depfinder and install it. ::

    git clone git@github.com:ericdill/depfinder
    cd depfinder
    python setup.py install

or ::

    pip install https://github.com/ericdill/depfinder/zipball/master#egg=depfinder



It has one dependency:
`stdlib_list <https://github.com/jackmaney/python-stdlib-list>`_, which is where
I get the list of libraries built in to the standard library. ``stdlib-list``
can be installed via pip (``pip install stdlib-list``) or conda
(``conda install -c ericdill stdlib-list``).

Usage
-----
``get_imported_libs``
=================
::

    import depfinder
    code = """
    import numpy
    try:
        import PyQt4
    except ImportError:
    import PyQt5"""
    deps = depfinder.get_imported_libs(code)
    print(deps.describe())

**output** ::

    {'questionable': {'PyQt4', 'PyQt5'}, 'required': {'numpy'}}

``iterate_over_library``
====================
::

    import depfinder
    import numpy
    import os
    deps = list(depfinder.iterate_over_library(os.path.dirname(depfinder.__file__)))
    print()
    for mod, full_path, catcher in deps:
        print('module_name = %s' % mod)
        print('full_path = %s' % full_path)
        print('dependencies')
        print(catcher.describe())

**output** ::

    ....
    module_name = setup
    full_path = /home/edill/dev/python/depfinder/setup.py
    dependencies
    {'required': {'setuptools'}}
    module_name = depfinder
    full_path = /home/edill/dev/python/depfinder/depfinder.py
    dependencies
    {'builtin': {'json', '__future__', 'os', 'collections', 'ast', 'sys'}, 'required': {'stdlib_list'}}
    module_name = test_with_notebook
    full_path = /home/edill/dev/python/depfinder/tests/test_with_notebook.py
    dependencies
    {'builtin': {'os', 'collections', 'tempfile'}, 'required': {'pytest', 'test_with_code', 'depfinder', 'nbformat'}}
    module_name = test_with_code
    full_path = /home/edill/dev/python/depfinder/tests/test_with_code.py
    dependencies
    {'required': {'depfinder'}}

``simple_import_search``
====================
::

    import depfinder
    print(depfinder.simple_import_search(os.path.dirname(depfinder.__file__)))

**output** ::

  ....{'builtin': ['__future__',
             'ast',
             'collections',
             'json',
             'os',
             'sys',
             'tempfile'],
 'required': ['depfinder',
              'nbformat',
              'pytest',
              'setuptools',
              'stdlib_list',
              'test_with_code']}

``notebook_path_to_dependencies``
=============================
::

    depfinder.notebook_path_to_dependencies('depfinder_usage.ipynb')

**output** ::

    {'builtin': ['os', 'pprint'], 'required': ['depfinder']}
