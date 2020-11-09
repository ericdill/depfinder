from __future__ import print_function, division, absolute_import

import ast
import logging
import pkgutil
import sys

import requests
import yaml
from stdlib_list import stdlib_list

logger = logging.getLogger('depfinder')

pyver = '%s.%s' % (sys.version_info.major, sys.version_info.minor)
builtin_modules = stdlib_list(pyver)
del pyver


SKETCHY_TYPES_TABLE = {}

try:
    # python 3
    AST_TRY = [ast.Try]
    SKETCHY_TYPES_TABLE[ast.Try] = 'try'
except AttributeError:
    # python 2.7
    AST_TRY = [ast.TryExcept, ast.TryFinally]
    SKETCHY_TYPES_TABLE[ast.TryExcept] = 'try'
    SKETCHY_TYPES_TABLE[ast.TryFinally] = 'try'

# this AST_QUESTIONABLE list comprises the various ways an import can be weird
# 1. inside a try/except block
# 2. inside a function
# 3. inside a class
AST_QUESTIONABLE = tuple(AST_TRY + [ast.FunctionDef, ast.ClassDef, ast.If])
SKETCHY_TYPES_TABLE[ast.FunctionDef] = 'function'
SKETCHY_TYPES_TABLE[ast.ClassDef] = 'class'
SKETCHY_TYPES_TABLE[ast.If] = 'if'
del AST_TRY

pkg_data = yaml.load(
    pkgutil.get_data(__name__, 'pkg_data/pkg_data.yml').decode(),
    Loader=yaml.CSafeLoader,
)

req = requests.get('https://raw.githubusercontent.com/regro/cf-graph-countyfair/master/mappings/pypi/name_mapping.yaml')
if req.status_code == 200:
    mapping_list = yaml.load(req.text, Loader=yaml.CSafeLoader)
else:
    mapping_list = yaml.load(
        pkgutil.get_data(__name__, 'pkg_data/name_mapping.yml').decode(),
        Loader=yaml.CSafeLoader,
    )

namespace_packages = {pkg['import_name'] for pkg in mapping_list if '.' in pkg['import_name']}