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

import ast
import logging
import os
import sys
from collections import defaultdict
from typing import Union

from stdlib_list import stdlib_list

from .utils import AST_QUESTIONABLE, namespace_packages, SKETCHY_TYPES_TABLE

logger = logging.getLogger('depfinder')

pyver = '%s.%s' % (sys.version_info.major, sys.version_info.minor)
builtin_modules = stdlib_list(pyver)
del pyver


PACKAGE_NAME = None
STRICT_CHECKING = False


def get_top_level_import_name(name):
    if name in namespace_packages:
        return name
    else:
        if '.' not in name:
            return name
        else:
            return get_top_level_import_name(name.rsplit('.', 1)[0])


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

    def __init__(self, filename=''):
        self.filename = filename
        self.required_modules = set()
        self.sketchy_modules = set()
        self.builtin_modules = set()
        self.relative_modules = set()
        self.imports = []
        self.import_froms = []
        self.total_imports = defaultdict(dict)
        self.sketchy_nodes = {}
        super(ImportFinder, self).__init__()

    def visit(self, node):
        """Recursively visit all ast nodes.

        Look for Import and ImportFrom nodes. Classify them as being imports
        that are built in, relative, required or questionable. Questionable
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

    def visit_Import(self, node: ast.Import):
        """Executes when an ast.Import node is encountered

        an ast.Import node is something like 'import bar'

        If ImportCatcher is inside of a try block then the import that has just
        been encountered will be added to the `sketchy_modules` instance
        attribute. Otherwise the module will be added to the `required_modules`
        instance attribute
        """
        self.imports.append(node)
        self._add_to_total_imports(node)

        mods = set([get_top_level_import_name(name.name) for name in node.names])
        for mod in mods:
            self._add_import_node(mod)

    def visit_ImportFrom(self, node: ast.ImportFrom):
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
            node_name = get_top_level_import_name(node.module)
            self.relative_modules.add(node_name)
            return
        # this is a non-relative import like 'from foo import bar'
        self._add_to_total_imports(node)
        node_name = get_top_level_import_name(node.module)
        self._add_import_node(node_name)

    def _add_to_total_imports(self, node: Union[ast.Import, ast.ImportFrom]):
        import_metadata = {}
        try:
            import_metadata.update({'exact_line': ast.unparse(node)})
        except AttributeError:
            pass

        import_metadata.update({v: False for v in SKETCHY_TYPES_TABLE.values()})
        import_metadata.update({SKETCHY_TYPES_TABLE[node.__class__]: True for node in self.sketchy_nodes})
        names = set()
        if isinstance(node, ast.Import):
            _names = set(name.name for name in node.names)
            import_metadata['import'] = _names
            names.update(_names)
        elif isinstance(node, ast.ImportFrom):
            import_metadata['import_from'] = {node.module}
            names.add(node.module)
        else:
            raise NotImplementedError(f"Expected ast.Import or ast.ImportFrom this is {type(node)}")

        for name in names:
            self.total_imports[name].update({(self.filename, node.lineno): import_metadata})

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
        desc = {
            'required': self.required_modules,
            'relative': self.relative_modules,
            'questionable': self.sketchy_modules,
            'builtin': self.builtin_modules
        }
        desc = {k: v for k, v in desc.items() if v}
        return desc

    def __repr__(self):
        return 'ImportCatcher: %s' % repr(self.describe())


def get_imported_libs(code, filename=''):
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
    import_finder = ImportFinder(filename=filename)
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
    # Try except block added for adal package which has a BOM at the beginning,
    # requiring a different encoding to load properly
    try:
        with open(python_file, 'r') as f:
            code = f.read()
        catcher = get_imported_libs(code, filename=python_file)
    except SyntaxError:
        with open(python_file, 'r', encoding='utf-8-sig') as f:
            code = f.read()
        catcher = get_imported_libs(code, filename=python_file)
    catcher.total_imports = dict(catcher.total_imports)
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
    global STRICT_CHECKING
    if PACKAGE_NAME is None:
        PACKAGE_NAME = os.path.basename(path_to_source_code).split('.')[0]
        logger.debug("Setting PACKAGE_NAME global variable to {}"
                     "".format(PACKAGE_NAME))
    skipped_files = []
    all_files = []
    for parent, folders, files in os.walk(path_to_source_code):
        for f in files:
            if f.endswith('.py'):
                full_file_path = os.path.join(parent, f)
                all_files.append(full_file_path)
                try:
                    yield parse_file(full_file_path)
                except Exception:
                    logger.exception("Could not parse file: {}".format(full_file_path))
                    skipped_files.append(full_file_path)
    if skipped_files:
        logger.warning("Skipped {}/{} files".format(len(skipped_files), len(all_files)))
        for idx, f in enumerate(skipped_files):
            logger.warn("%s: %s" % (str(idx), f))

    if skipped_files and STRICT_CHECKING:
        raise RuntimeError("Some files failed to parse. See logs for full stack traces.")
