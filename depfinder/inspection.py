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
from collections import defaultdict
from typing import Iterable

from pydantic import BaseModel

from .stdliblist import builtin_modules

from .utils import (
    AST_QUESTIONABLE,
    ImportType,
    namespace_packages,
    ast_types_to_str,
    ast_import_types,
    ImportMetadata,
)

logger = logging.getLogger("depfinder.inspection")


current_package_name: str = ""
STRICT_CHECKING = False


class FoundModules(BaseModel):
    required: set[str]
    questionable: set[str]
    builtin: set[str]
    relative: set[str]


def get_top_level_import_name(name: str, custom_namespaces: list[str] = None) -> str:
    num_dot = name.count(".")
    custom_namespaces = custom_namespaces or []

    if (
        name in namespace_packages
        or name in custom_namespaces
        or name in builtin_modules
    ):
        return name
    elif any(
        ((num_dot - nsp.count(".")) == 1) and name.startswith(nsp + ".")
        for nsp in custom_namespaces
    ):
        # this branch happens when name is foo.bar.baz and the namespace is
        # foo.bar
        return name
    else:
        if "." not in name:
            return name
        else:
            return get_top_level_import_name(
                name.rsplit(".", 1)[0], custom_namespaces=custom_namespaces
            )


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

    def __init__(self, filename: str = "", custom_namespaces: list[str] = None):
        self.filename = filename
        self.required_modules: set[str] = set()
        self.questionable_modules: set[str] = set()
        self.builtin_modules: set[str] = set()
        self.relative_modules: set[str] = set()
        self.imports: list[ast.AST] = []
        self.import_froms: list[ast.AST] = []
        self.total_imports_new: list[ImportMetadata] = list()
        self.total_imports: dict[
            str, dict[tuple[str, int], ImportMetadata]
        ] = defaultdict(dict)
        self.sketchy_nodes: dict[ast.AST, ast.AST] = {}
        self.custom_namespaces: list[str] = custom_namespaces or []
        super(ImportFinder, self).__init__()

    def visit(self, node: ast.AST):
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

        If ImportFinder is inside of a try block then the import that has just
        been encountered will be added to the `sketchy_modules` instance
        attribute. Otherwise the module will be added to the `required_modules`
        instance attribute
        """
        self.imports.append(node)
        self._add_to_total_imports(node)

        imports: set[str] = set()
        for name in node.names:
            import_name = get_top_level_import_name(
                name.name, custom_namespaces=self.custom_namespaces
            )
            imports.add(import_name)

        for import_name in imports:
            self._add_import_node(import_name)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Executes when an ast.ImportFrom node is encountered

        an ast.ImportFrom node is something like 'from foo import bar'

        If ImportFinder is inside of a try block then the import that has just
        been encountered will be added to the `sketchy_modules` instance
        attribute. Otherwise the module will be added to the `required_modules`
        instance attribute
        """
        logger.debug(f"node={node}, node.lineno={node.lineno}")
        self.import_froms.append(node)
        if node.module is None:
            # this is a relative import like 'from . import bar'
            # so do nothing
            return
        if node.level > 0:
            # this is a relative import like 'from .foo import bar'
            node_name = get_top_level_import_name(
                node.module, custom_namespaces=self.custom_namespaces
            )
            self.relative_modules.add(node_name)
            return
        # this is a non-relative import like 'from foo import bar'
        self._add_to_total_imports(node)
        node_name = get_top_level_import_name(
            node.module,
            custom_namespaces=self.custom_namespaces,
        )
        self._add_import_node(node_name)

    def _add_to_total_imports(self, node: ast_import_types):
        logger.debug(f"_add_to_total_imports node={node}, node.lineno={node.lineno}")

        import_metadata = ImportMetadata()
        try:
            import_metadata.exact_line = ast.unparse(node)
        except AttributeError:
            # what are the circumstances where we hit this exception?
            pass

        # import_metadata.update({v: False for v in SKETCHY_TYPES_TABLE.values()})
        # For all of the sketchy nodes, update the import metadata to "True" for
        # each of the node types that our import is found within. e.g., if the
        # import is found within a try block and a function definition, then
        # set import_metadata.try = True and import_metadata.function = True

        for sketchy_node in self.sketchy_nodes:
            logger.debug(f"sketchy_node={sketchy_node}")
            import_metadata.__setattr__(ast_types_to_str[sketchy_node.__class__], True)

        if isinstance(node, ast.Import):
            # import nodes can have multiple imports, e.g.
            # import foo, bar, baz
            names: set[str] = set()
            for node_alias in node.names:
                names.add(node_alias.name)
            import_metadata.imported_modules = names
            import_metadata.import_type = ImportType.import_normal
        elif isinstance(node, ast.ImportFrom):
            import_metadata.import_type = ImportType.import_from
            if node.module is not None:
                import_metadata.imported_modules = {node.module}
        else:
            # defensive coding. This will only be hit if a new
            # `visit_*` method is added to this class
            raise NotImplementedError(
                f"Expected ast.Import or ast.ImportFrom this is {type(node)}"
            )
        import_metadata.lineno = node.lineno
        import_metadata.filename = self.filename
        self.total_imports_new.append(import_metadata)
        for import_name in import_metadata.imported_modules:
            self.total_imports[import_name].update(
                {(self.filename, node.lineno): import_metadata}
            )

    def _add_import_node(self, node_name: str):
        # see if the module is a builtin
        if node_name in builtin_modules:
            self.builtin_modules.add(node_name)
            return

        # see if we are in a try block
        if self.sketchy_nodes:
            self.questionable_modules.add(node_name)
            return

        # if none of the above cases are true, it is likely that this
        # ImportFrom node occurs at the top level of the module
        self.required_modules.add(node_name)

    def describe_pydantic(self) -> FoundModules:
        """Return the found imports

        Returns
        -------
        FoundModules :
            'required': The modules that were encountered outside of a
                        try/except block
            'questionable': The modules that were encountered inside of a
                            try/except block
            'relative': The modules that were imported via relative import
                        syntax
            'builtin' : The modules that are part of the standard library
        """
        found_modules = FoundModules(
            required=self.required_modules,
            relative=self.relative_modules,
            questionable=self.questionable_modules,
            builtin=self.builtin_modules,
        )
        return found_modules

    def describe(self) -> dict[str, set[str]]:
        """Return the found imports

        Returns
        -------
        FoundModules :
            'required': The modules that were encountered outside of a
                        try/except block
            'questionable': The modules that were encountered inside of a
                            try/except block
            'relative': The modules that were imported via relative import
                        syntax
            'builtin' : The modules that are part of the standard library
        """
        deps = {
            "required": self.required_modules,
            "relative": self.relative_modules,
            "questionable": self.questionable_modules,
            "builtin": self.builtin_modules,
        }

        deps = {k: v for k, v in deps.items() if v}
        return deps

    def __repr__(self):
        return "ImportFinder: %s" % repr(self.describe())


def get_imported_libs(
    code: str, filename: str = "", custom_namespaces: list[str] = None
) -> ImportFinder:
    """Given a code snippet, return a list of the imported libraries

    Parameters
    ----------
    code : str
        The code to parse and look for imports

    Returns
    -------
    ImportFinder
        The ImportFinder is the object in `depfinder` that contains all the
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
    code = "\n".join([line for line in code.split("\n") if not line.startswith("%")])
    tree = ast.parse(code)
    import_finder = ImportFinder(filename=filename, custom_namespaces=custom_namespaces)
    import_finder.visit(tree)
    return import_finder


def parse_file(
    python_file: str, custom_namespaces: list[str] = None
) -> tuple[str, str, ImportFinder]:
    """Parse a single python file

    Parameters
    ----------
    python_file : str
        Path to the python file to parse for imports

    Returns
    -------
    tuple
        Yields tuples of (module_name, full_path_to_module, ImportFinder)
    """
    global current_package_name
    if not current_package_name:
        # this might have a potential bug if the filename has more than one "."
        current_package_name = os.path.basename(python_file).split(".")[0]
        logger.debug(
            "Setting PACKAGE_NAME global variable to {}" "".format(current_package_name)
        )
    # Try except block added for adal package which has a BOM at the beginning,
    # requiring a different encoding to load properly
    try:
        with open(python_file, "r") as f:
            code = f.read()
        import_finder = get_imported_libs(
            code, filename=python_file, custom_namespaces=custom_namespaces
        )
    except SyntaxError:
        with open(python_file, "r", encoding="utf-8-sig") as f:
            code = f.read()
        import_finder = get_imported_libs(
            code, filename=python_file, custom_namespaces=custom_namespaces
        )
    import_finder.total_imports = dict(import_finder.total_imports)
    return current_package_name, python_file, import_finder


def iterate_over_library(
    path_to_source_code: str, custom_namespaces: list[str] = None
) -> Iterable[tuple[str, str, ImportFinder]]:
    """Helper function to recurse into a library and find imports in .py files.

    This allows the user to apply filters on the user-side to exclude imports
    based on their file names.

    Parameters
    ----------
    path_to_source_code : str

    Yields
    -------
    tuple
        Yields tuples of (module_name, full_path_to_module, ImportFinder)
    """
    global current_package_name
    global STRICT_CHECKING
    if not current_package_name:
        current_package_name = os.path.basename(path_to_source_code).split(".")[0]
        logger.debug(
            "Setting PACKAGE_NAME global variable to {}" "".format(current_package_name)
        )
    skipped_files: list[str] = []
    all_files: list[str] = []
    for parent, _, files in os.walk(path_to_source_code):
        for f in files:
            if f.endswith(".py"):
                full_file_path = os.path.join(parent, f)
                all_files.append(full_file_path)
                try:
                    yield parse_file(
                        full_file_path, custom_namespaces=custom_namespaces
                    )
                except Exception:
                    logger.exception("Could not parse file: {}".format(full_file_path))
                    skipped_files.append(full_file_path)
    if skipped_files:
        logger.warning("Skipped {}/{} files".format(len(skipped_files), len(all_files)))
        for idx, f in enumerate(skipped_files):
            logger.warn("%s: %s" % (str(idx), f))

    if skipped_files and STRICT_CHECKING:
        raise RuntimeError(
            "Some files failed to parse. See logs for full stack traces."
        )
