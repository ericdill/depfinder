from __future__ import print_function, division, absolute_import
import ast
import os
from collections import deque, defaultdict
import sys
from stdlib_list import stdlib_list

__version__ = 'v0.0.0'


conf = {
    'include_relative_imports': False,
    'ignore_builtin_modules': True,
    'pyver': None,
}


class ImportCatcher(ast.NodeVisitor):

    def __init__(self, include_relative_imports=False):
        self.include_relative_imports = include_relative_imports
        self.modules = deque()
        self.sketchy_modules = deque()
        self.imports = deque()
        self.import_froms = deque()
        self.trys = {}

    def generic_visit(self, node):
        """Called if no explicit visitor function exists for a node."""
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    # add the node to the try/except block to signify that
                    # something potentially odd is going on in this import
                    if isinstance(item, ast.Try):
                        self.trys[item] = item
                    if isinstance(item, ast.AST):
                        self.visit(item)
                    # after the node has been recursed in to, remove the try node
                    if isinstance(item, ast.Try):
                        del self.trys[item]
            elif isinstance(value, ast.AST):
                self.visit(value)


    def visit_Import(self, node):
        self.imports.append(node)
        mods = [name.name.split('.')[0] for name in node.names]
        if self.trys:
            self.sketchy_modules.extend(mods)
        else:
            self.modules.extend(mods)

    def visit_ImportFrom(self, node):
        self.import_froms.append(node)
        if node.module is None:
            # this is a relative import like 'from . import bar'
            # so do nothing
            return
        elif not self.include_relative_imports and node.level == 0:
            # this is a non-relative import like 'from foo import bar'
            mod = node.module.split('.')[0]
        elif self.include_relative_imports and node.level > 0:
            # this is a relative import like 'from .foo import bar'
            mod = node.module.split('.')[0]
        else:
            return

        if self.trys:
            self.sketchy_modules.append(mod)
        else:
            self.modules.append(mod)



def get_imported_libs(code):
    tree = ast.parse(code)
    catcher = ImportCatcher(include_relative_imports=conf['include_relative_imports'])
    catcher.visit(tree)
    return {'probably_fine': set(catcher.modules),
            'definitely_questionable': set(catcher.sketchy_modules)}


def iterate_over_library(path_to_source_code):
    libs = defaultdict(set)
    probably_fine = set()
    definitely_questionable = set()
    for parent, folders, files in os.walk(path_to_source_code):
        for file in files:
            if file.endswith('.py'):
                print('.', end='')
                full_file_path = os.path.join(parent, file)
                with open(full_file_path, 'r') as f:
                    code = f.read()
                for k, v in get_imported_libs(code).items():
                    libs[k].update(v)

    print(libs)

    if conf['ignore_builtin_modules']:
        if not conf['pyver']:
            pyver = '%s.%s' % (sys.version_info.major, sys.version_info.minor)
        std_libs = stdlib_list("3.4")
        # print(std_libs)
        libs['probably_fine'] = [lib for lib in libs['probably_fine'] if lib not in std_libs]
    libs = {k: sorted(v) for k, v in libs.items()}
    return libs
