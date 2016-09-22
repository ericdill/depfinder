# Copyright (c) <2015-2016>, Eric Dill
#
# All rights reserved.  Redistribution and use in source and binary forms, with
# or without modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
# may be used to endorse or promote products derived from this software without
# specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import print_function, division, absolute_import
import json
import ast
import os
from collections import defaultdict
from pprint import pprint
import logging
import yaml
import sys
import copy
from stdlib_list import stdlib_list

logger = logging.getLogger('depfinder')

pyver = '%s.%s' % (sys.version_info.major, sys.version_info.minor)
builtin_modules = stdlib_list(pyver)
del pyver

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

class ImportFinder(ast.NodeVisitor):
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
        super(ImportFinder, self).__init__()

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
        super(ImportFinder, self).visit(node)
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
    # skip ipython notebook lines
    code = '\n'.join([line for line in code.split('\n')
                      if not line.startswith('%')])
    tree = ast.parse(code)
    import_finder = ImportFinder()
    import_finder.visit(tree)
    return import_finder


def parse_file(python_file):
    """Parse a single python file

    Parameters
    ----------
    python_file : str
        Path to the python file to parse for imports

    Returns
    -------
    catchers : tuple
        Yields tuples of (module_name, full_path_to_module, ImportCatcher)
    """
    global PACKAGE_NAME
    if PACKAGE_NAME is None:
        PACKAGE_NAME = os.path.basename(python_file).split('.')[0]
        logger.debug("Setting PACKAGE_NAME global variable to {}"
                     "".format(PACKAGE_NAME))
    with open(python_file, 'r') as f:
        code = f.read()
    catcher = get_imported_libs(code)
    mod_name = os.path.split(python_file)[:-3]
    return mod_name, python_file, catcher


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
    global PACKAGE_NAME
    if PACKAGE_NAME is None:
        PACKAGE_NAME = os.path.basename(path_to_source_code).split('.')[0]
        logger.debug("Setting PACKAGE_NAME global variable to {}"
                     "".format(PACKAGE_NAME))
    for parent, folders, files in os.walk(path_to_source_code):
        for f in files:
            if f.endswith('.py'):
                full_file_path = os.path.join(parent, f)
                yield parse_file(full_file_path)


def simple_import_search(path_to_source_code, remap=True):
    """Return all imported modules in all .py files in `path_to_source_code`

    Parameters
    ----------
    path_to_source_code : str
    remap : bool, optional
        Normalize the import names to be synonymous with their conda/pip names

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
    all_deps = defaultdict(set)
    catchers = iterate_over_library(path_to_source_code)
    for mod, path, catcher in catchers:
        for k, v in catcher.describe().items():
            all_deps[k].update(v)

    all_deps = {k: sorted(list(v)) for k, v in all_deps.items() if v}
    if remap:
        return sanitize_deps(all_deps)
    return all_deps


def notebook_path_to_dependencies(path_to_notebook, remap=True):
    """Helper function that turns a jupyter notebook into a list of dependencies

    Parameters
    ----------
    path_to_notebook : str
    remap : bool, optional
        Normalize the import names to be synonymous with their conda/pip names


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
    if remap:
        return sanitize_deps(all_deps)
    return all_deps

PACKAGE_NAME = None

_PACKAGE_MAPPING = {
    'av': 'pyav',
    'cv2': 'opencv',
    'IPython': 'ipython',
    'netCDF4': 'netcdf4',
    'PIL': 'pillow',
    'skimage': 'scikit-image',
    'sklearn': 'scikit-learn',
    'stdlib_list': 'stdlib-list',
    'yaml': 'pyyaml',
}
_FAKE_PACKAGES = {
    'matplotlib': {'mpl_toolkits'},
    'pymongo': {'bson', 'gridfs'},
}

def sanitize_deps(deps_dict):
    """
    Helper function that takes the output of `notebook_path_to_dependencies`
    or `simple_import_search` and turns normalizes the import names to be
    synonymous with their conda/pip names

    Parameters
    ----------
    deps_dict : dict
        Output of `notebook_path_to_dependencies` or `simple_import_search`
    Returns
    -------
    deps_dict : dict
        If remap is True: Sanitized `deps_dict`
        If remap is False: `deps_dict`
    """
    new_deps_dict = {}
    list_of_possible_fakes = set([v for val in _FAKE_PACKAGES.values() for v in val])
    for k, packages_list in deps_dict.items():

        pkgs = copy.copy(packages_list)
        new_deps_dict[k] = set()
        for pkg in pkgs:
            # drop fake packages
            if pkg in list_of_possible_fakes:
                logger.debug("Ignoring {} from the list of imports. It is "
                             "installed as part of another package. Set the "
                             "`--no-remap` cli flag if you want to disable "
                             "this".format(pkg))
                continue
            if pkg == PACKAGE_NAME:
                logger.debug("Ignoring {} from the list of imports. It is "
                             "the name of the package that we are trying to "
                             "find the dependencies for. Set the `--no-remap` "
                             "cli flag if you want to disable this.".format(pkg))
                continue
            pkg_to_add = _PACKAGE_MAPPING.get(pkg, pkg)
            if pkg != pkg_to_add:
                logger.debug("Renaming {} to {}".format(pkg, pkg_to_add))
            new_deps_dict[k].add(pkg_to_add)
    new_deps_dict = {k: sorted(list(v)) for k, v in new_deps_dict.items() if v}
    return new_deps_dict
