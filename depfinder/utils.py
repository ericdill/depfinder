from __future__ import print_function, division, absolute_import

import ast
import logging
import pkgutil
import sys

import requests
import requests.exceptions
import yaml
from .stdliblist import builtin_modules

logger = logging.getLogger("depfinder")

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


try:
    # python 3.10+
    AST_MATCH = [ast.match_case]
    SKETCHY_TYPES_TABLE[ast.match_case] = 'match'
except AttributeError:
    # match/case does not exist before 3.10
    AST_MATCH = []


# this AST_QUESTIONABLE list comprises the various ways an import can be weird
# 1. inside a try/except block
# 2. inside a function (async or otherwise)
# 3. part of an if/elif/else
# 4. inside a loop
# 5. (for Python 3.10+) inside a match/case
AST_QUESTIONABLE = tuple(AST_TRY + AST_MATCH + [
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.If,
    ast.While,
    ast.For,
    ast.AsyncFor,
])
SKETCHY_TYPES_TABLE[ast.FunctionDef] = 'function'
SKETCHY_TYPES_TABLE[ast.AsyncFunctionDef] = 'async-function'
SKETCHY_TYPES_TABLE[ast.If] = 'if'
SKETCHY_TYPES_TABLE[ast.While] = 'while'
SKETCHY_TYPES_TABLE[ast.For] = 'for'
SKETCHY_TYPES_TABLE[ast.AsyncFor] = 'async-for'
del AST_TRY
del AST_MATCH

try:
    # Try and use the C extensions because they're faster
    yaml_loader = yaml.CSafeLoader
except ImportError:
    # Fall back to the slower python implementation of the extensions because
    # that is what is available from the PyYAML pip package
    yaml_loader = yaml.SafeLoader

pkg_data = yaml.load(
    pkgutil.get_data(__name__, 'pkg_data/pkg_data.yml').decode(),
    Loader=yaml_loader,
)

try:
    import conda_forge_metadata.autotick_bot
    mapping_list = conda_forge_metadata.autotick_bot.get_pypi_name_mapping()
except (ImportError, AttributeError, requests.exceptions.HTTPError):
    logger.exception(
        "could not get the conda-forge metadata pypi-to-conda name mapping "
        "due to error. defaulting to an internal one which may be out of date."
    )
    mapping_list = yaml.load(
        pkgutil.get_data(__name__, 'pkg_data/name_mapping.yml').decode(),
        Loader=yaml_loader,
    )

namespace_packages = {pkg['import_name'] for pkg in mapping_list if '.' in pkg['import_name']}
