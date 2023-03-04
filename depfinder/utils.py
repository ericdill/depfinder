from __future__ import print_function, division, absolute_import

import ast
from enum import Enum
import logging
import pkgutil
import sys
from typing import Any
from pydantic import create_model

import requests
import yaml
from .stdliblist import builtin_modules


SKETCHY_TYPES_TABLE: dict[type[ast.AST], str] = {}


class ImportMetadata(BaseModel):
    # this group of vars are set to true when an import occurs within
    # one of their node types
    ast_try = False
    ast_match_case = False
    ast_function_def = False
    ast_async_function_def = False
    ast_if = False
    ast_while = False
    ast_for = False
    ast_async_for = False


try:
    # python 3
    AST_TRY = [ast.Try]
    SKETCHY_TYPES_TABLE[ast.Try] = "try"
except AttributeError:
    # python 2.7
    AST_TRY = [ast.TryExcept, ast.TryFinally]
    SKETCHY_TYPES_TABLE[ast.TryExcept] = "try"
    SKETCHY_TYPES_TABLE[ast.TryFinally] = "try"


try:
    # python 3.10+
    AST_MATCH: list[type[ast.AST]] = [ast.match_case]
    SKETCHY_TYPES_TABLE[ast.match_case] = "match"
except AttributeError:
    # match/case does not exist before 3.10
    AST_MATCH = []


# this AST_QUESTIONABLE list comprises the various ways an import can be weird
# 1. inside a try/except block
# 2. inside a function (async or otherwise)
# 3. part of an if/elif/else
# 4. inside a loop
# 5. (for Python 3.10+) inside a match/case
AST_QUESTIONABLE: tuple[type[ast.AST]] = tuple(
    AST_TRY
    + AST_MATCH
    + [
        ast.FunctionDef,
        ast.AsyncFunctionDef,
        ast.If,
        ast.While,
        ast.For,
        ast.AsyncFor,
    ]
)
SKETCHY_TYPES_TABLE[ast.FunctionDef] = "function"
SKETCHY_TYPES_TABLE[ast.AsyncFunctionDef] = "async-function"
SKETCHY_TYPES_TABLE[ast.If] = "if"
SKETCHY_TYPES_TABLE[ast.While] = "while"
SKETCHY_TYPES_TABLE[ast.For] = "for"
SKETCHY_TYPES_TABLE[ast.AsyncFor] = "async-for"

pydantic_kwargs: dict[str, tuple[Any, Any]] = {}
for node_type, shorthand in SKETCHY_TYPES_TABLE.items():
    pydantic_kwargs[shorthand] = (bool, False)


class ImportType(Enum):
    import_normal = ast.Import
    import_from = ast.ImportFrom


ImportMetadata = create_model(
    "ImportMetadata",
    **pydantic_kwargs,
    exact_line=(str, ""),
    import_type=(ImportType, ...),
    imported_modules=(set[str], []),
    lineno=(int, -1),
    filename=(str, ""),
)

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
    pkgutil.get_data(__name__, "pkg_data/pkg_data.yml").decode(),
    Loader=yaml_loader,
)

req = requests.get(
    "https://raw.githubusercontent.com/regro/cf-graph-countyfair/master/mappings/pypi/name_mapping.yaml"
)
if req.status_code == 200:
    mapping_list = yaml.load(req.text, Loader=yaml_loader)
else:
    mapping_list = yaml.load(
        pkgutil.get_data(__name__, "pkg_data/name_mapping.yml").decode(),
        Loader=yaml_loader,
    )

namespace_packages = {
    pkg["import_name"] for pkg in mapping_list if "." in pkg["import_name"]
}
