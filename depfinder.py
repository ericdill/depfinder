# depfinder
# Copyright (C) 2015 Eric Dill
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function, division, absolute_import
import json
import ast
import os
from collections import defaultdict
from stdlib_list import stdlib_list

import sys
pyver = '%s.%s' % (sys.version_info.major, sys.version_info.minor)
builtin_modules = stdlib_list(pyver)
del pyver
del sys

try:
    # python 3
    AST_TRY = [ast.Try]
except AttributeError:
    # python 2.7
    AST_TRY = [ast.TryExcept, ast.TryFinally]

# this AST_QUESTIONABLE list comprises the various ways an import can be weird
# 1. inside a try/except block
# 2. inside a function
# 3. inside a class
AST_QUESTIONABLE = tuple(list(AST_TRY) + [ast.FunctionDef, ast.ClassDef])
del AST_TRY

class ImportCatcher(ast.NodeVisitor):
    """Find all imports in an Abstract Syntax Tree (AST).

    Attributes
    ----------
    required_modules : list
        The list of imports that were found outside of try/except blocks,
        function definitions and class definitions
    sketchy_modules : list
        The list of imports that were found inside of try/except blocks,
        function definitions and class definitions
    imports : list
        The list of all ast.Import nodes in the AST
    import_froms : list
        The list of all ast.ImportFrom nodes in the AST

    """
    def __init__(self):
        self.required_modules = set()
        self.sketchy_modules = set()
        self.builtin_modules = set()
        self.relative_modules = set()
        self.imports = []
        self.import_froms = []
        self.sketchy_nodes = {}
        super(ImportCatcher, self).__init__()

    def visit(self, node):
        """Recursively visit all ast nodes.

        Look for Import and ImportFrom nodes. Classify them as being imports
        that are built in, relative, required or questionable. Qustionable
        imports are those that occur within the context of a try/except block, a
        function definition or a class definition.

        Parameters
        ----------
        node : ast.AST
            The node to start the recursion
        """
        # add the node to the try/except block to signify that
        # something potentially odd is going on in this import
        if isinstance(node, AST_QUESTIONABLE):
            self.sketchy_nodes[node] = node
        super(ImportCatcher, self).visit(node)
        # after the node has been recursed in to, remove the try node
        self.sketchy_nodes.pop(node, None)

    def visit_Import(self, node):
        """Executes when an ast.Import node is encountered

        an ast.Import node is something like 'import bar'

        If ImportCatcher is inside of a try block then the import that has just
        been encountered will be added to the `sketchy_modules` instance
        attribute. Otherwise the module will be added to the `required_modules`
        instance attribute
        """
        self.imports.append(node)
        mods = set([name.name.split('.')[0] for name in node.names])
        for mod in mods:
            self._add_import_node(mod)

    def visit_ImportFrom(self, node):
        """Executes when an ast.ImportFrom node is encountered

        an ast.ImportFrom node is something like 'from foo import bar'

        If ImportCatcher is inside of a try block then the import that has just
        been encountered will be added to the `sketchy_modules` instance
        attribute. Otherwise the module will be added to the `required_modules`
        instance attribute
        """
        self.import_froms.append(node)
        if node.module is None:
            # this is a relative import like 'from . import bar'
            # so do nothing
            return
        if node.level > 0:
            # this is a relative import like 'from .foo import bar'
            node_name = node.module.split('.')[0]
            self.relative_modules.add(node_name)
            return
        # this is a non-relative import like 'from foo import bar'
        node_name = node.module.split('.')[0]
        self._add_import_node(node_name)

    def _add_import_node(self, node_name):
        # see if the module is a builtin
        if node_name in builtin_modules:
            self.builtin_modules.add(node_name)
            return

        # see if we are in a try block
        if self.sketchy_nodes:
            self.sketchy_modules.add(node_name)
            return

        # if none of the above cases are true, it is likely that this
        # ImportFrom node occurs at the top level of the module
        self.required_modules.add(node_name)

    def describe(self):
        """Return the found imports

        Returns
        -------
        dict :
            'required': The modules that were encountered outside of a
                        try/except block
            'questionable': The modules that were encountered inside of a
                            try/except block
            'relative': The modules that were imported via relative import
                        syntax
            'builtin' : The modules that are part of the standard library
        """
        desc =  {
            'required': self.required_modules,
            'relative': self.relative_modules,
            'questionable': self.sketchy_modules,
            'builtin': self.builtin_modules
        }
        desc = {k: v for k, v in desc.items() if v}
        return desc


    def __repr__(self):
        return 'ImportCatcher: %s' % repr(self.describe())


def get_imported_libs(code):
    """Given a code snippet, return a list of the imported libraries

    Parameters
    ----------
    code : str
        The code to parse and look for imports

    Returns
    -------
    ImportCatcher
        The ImportCatcher is the object in `depfinder` that contains all the
        information regarding which imports were found where.  You will most
        likely be interested in calling the describe() function on this return
        value.

    Examples
    --------
    >>> depfinder.get_imported_libs('from foo import bar')
    {'required': {'foo'}, 'questionable': set()}
    >>> with open('depfinder.py') as f:
            code = f.read()
            imports = depfinder.get_imported_libs(code)
            print(imports.describe())
    {'builtin': {'__future__', 'json', 'ast', 'os', 'sys', 'collections'},
     'required': {'stdlib_list'}}
    """
    tree = ast.parse(code)
    catcher = ImportCatcher()
    catcher.visit(tree)
    return catcher


def iterate_over_library(path_to_source_code):
    """Helper function to recurse into a library and find imports in .py files.

    This allows the user to apply filters on the user-side to exclude imports
    based on their file names.
    `conda-skeletor <https://github.com/ericdill/conda-skeletor>`_
    makes heavy use of this function

    Parameters
    ----------
    path_to_source_code : str

    Yields
    -------
    catchers : tuple
        Yields tuples of (module_name, full_path_to_module, ImportCatcher)
    """
    for parent, folders, files in os.walk(path_to_source_code):
        for file in files:
            if file.endswith('.py'):
                full_file_path = os.path.join(parent, file)
                with open(full_file_path, 'r') as f:
                    code = f.read()
                catcher = get_imported_libs(code)
                yield (file[:-3], full_file_path, catcher)


def simple_import_search(path_to_source_code):
    """Return all imported modules in all .py files in `path_to_source_code`

    Parameters
    ----------
    path_to_source_code : str

    Returns
    -------
    dict
        The list of all imported modules, sorted according to the keys listed
        in the docstring of depfinder.ImportCatcher.describe()

    Examples
    --------
    >>> depfinder.simple_import_search('/path/to/depfinder/source')
    {'builtin': ['__future__',
                 'ast',
                 'collections',
                 'json',
                 'os',
                 'shlex',
                 'sys',
                 'tempfile'],
     'required': ['depfinder',
                  'nbformat',
                  'pytest',
                  'setuptools',
                  'sphinx_rtd_theme',
                  'stdlib_list',
                  'test_with_code']}
    """
    mods = defaultdict(set)
    catchers = iterate_over_library(path_to_source_code)
    for mod, path, catcher in catchers:
        for k, v in catcher.describe().items():
            mods[k].update(v)

    mods = {k: sorted(list(v)) for k, v in mods.items() if v}
    return mods


def notebook_path_to_dependencies(path_to_notebook):
    """Helper function that turns a jupyter notebook into a list of dependencies

    Parameters
    ----------
    path_to_notebook : str

    Returns
    -------
    dict
        Dict of dependencies keyed on

        - 'builtin' - libraries built in to python
        - 'required' - libraries that are found at the top level of your modules
        - 'questionable' - libraries that are found inside try/except blocks
        - 'relative' - libraries that are relative imports

    Examples
    --------
    >>> depfinder.notebook_path_to_dependencies('depfinder_usage.ipynb')
    {'builtin': ['os', 'pprint'], 'required': ['depfinder']}
    """
    nb = json.load(open(path_to_notebook))
    codeblocks = [''.join(cell['source']) for cell in nb['cells']
                  if cell['cell_type'] == 'code']
    all_deps = defaultdict(set)
    for codeblock in codeblocks:
        deps_dict = get_imported_libs(codeblock).describe()
        for k, v in deps_dict.items():
            all_deps[k].update(v)

    all_deps = {k: sorted(list(v)) for k, v in all_deps.items()}
    return all_deps
