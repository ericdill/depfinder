from __future__ import print_function, division, absolute_import

import ast
from enum import Enum
import enum
import pkgutil
from typing import Any, Dict, List, Set, Tuple, Type, Union
from pydantic import BaseModel, create_model

import requests
import yaml
from .stdliblist import builtin_modules


class ImportType(Enum):
    import_normal = ast.Import
    import_from = ast.ImportFrom
    unset = enum.auto()


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
    exact_line = ""
    import_type = ImportType.unset
    imported_modules: Set[str] = set()
    lineno = -1
    filename = "unset"


ast_type = Type[ast.AST]
ast_import_types = Union[ast.Import, ast.ImportFrom]
ast_try: List[ast_type]
ast_match: List[ast_type]
ast_types_to_str: Dict[ast_type, str] = {}

try:
    # python 3
    ast_try = [ast.Try]
    ast_types_to_str[ast.Try] = "ast_try"
except AttributeError:
    # python 2.7
    # honestly could probably drop this section soon
    ast_try = [ast.TryExcept, ast.TryFinally]  # type: ignore
    ast_types_to_str[ast.TryExcept] = "ast_try"  # type: ignore
    ast_types_to_str[ast.TryFinally] = "ast_try"  # type: ignore


try:
    # python 3.10+
    ast_match = [ast.match_case]  # type: ignore
    ast_types_to_str[ast.match_case] = "ast_match_case"  # type: ignore
except AttributeError:
    # match/case does not exist before 3.10
    ast_match = []


# this AST_QUESTIONABLE list comprises the various ways an import can be weird
# 1. inside a try/except block
# 2. inside a function (async or otherwise)
# 3. part of an if/elif/else
# 4. inside a loop
# 5. (for Python 3.10+) inside a match/case
AST_QUESTIONABLE: Tuple[ast_type] = tuple(
    ast_try
    + ast_match
    + [
        ast.FunctionDef,
        ast.AsyncFunctionDef,
        ast.If,
        ast.While,
        ast.For,
        ast.AsyncFor,
    ]
)
ast_types_to_str.update(
    {
        ast.FunctionDef: "ast_function_def",
        ast.AsyncFunctionDef: "ast_async_function_def",
        ast.If: "ast_if",
        ast.While: "ast_while",
        ast.For: "ast_for",
        ast.AsyncFor: "ast_async_for",
    }
)


del ast_try
del ast_match

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
    "https://raw.githubusercontent.com/regro/cf-graph-countyfair/master/mappings/pypi/name_mapping.json"
)
if req.status_code == 200:
    mapping_list = req.json()
else:
    mapping_list = yaml.load(
        pkgutil.get_data(__name__, "pkg_data/name_mapping.yml").decode(),
        Loader=yaml_loader,
    )

namespace_packages = {
    pkg["import_name"] for pkg in mapping_list if "." in pkg["import_name"]
}
