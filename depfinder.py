import ast
import os
from collections import deque
import sys
from stdlib_list import stdlib_list

conf = {
    'include_relative_imports': False,
    'ignore_builtin_modules': True,
    'pyver': None,
}


class ImportCatcher(ast.NodeVisitor):

    def __init__(self, include_relative_imports=False):
        self.include_relative_imports = include_relative_imports
        self.modules = deque()

    def visit_Import(self, node):
        mods = [name.name.split('.')[0] for name in node.names]
        self.modules.extend(mods)

    def visit_ImportFrom(self, node):
        if node.module is None:
            # this is a relative import like 'from . import bar'
            # so do nothing
            return
        elif not self.include_relative_imports and node.level == 0:
            # this is a non-relative import like 'from foo import bar'
            self.modules.append(node.module.split('.')[0])
        elif self.include_relative_imports and node.level > 0:
            # this is a relative import like 'from .foo import bar'
            self.modules.append(node.module.split('.')[0])


def get_imported_libs(code):
    tree = ast.parse(code)
    catcher = ImportCatcher(include_relative_imports=conf['include_relative_imports'])
    catcher.visit(tree)
    return set(catcher.modules)


def iterate_over_library(path_to_source_code):
    libs = set()
    for parent, folders, files in os.walk(path_to_source_code):
        for file in files:
            if file.endswith('.py'):
                print('.', end='')
                full_file_path = os.path.join(parent, file)
                with open(full_file_path, 'r') as f:
                    code = f.read()
                libs.update(set(get_imported_libs(code)))

    if conf['ignore_builtin_modules']:
        if not conf['pyver']:
            pyver = '%s.%s' % (sys.version_info.major, sys.version_info.minor)
        std_libs = stdlib_list("3.4")
        # print(std_libs)
        libs = [lib for lib in libs if lib not in std_libs]

    return sorted(libs)


parser_handlers = {
    ast.Import: _parse_import,
    ast.ImportFrom: _parse_import_from,
}