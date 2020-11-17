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

import copy
import io
import json
import logging
from collections import defaultdict
from fnmatch import fnmatch

from .inspection import iterate_over_library, get_imported_libs
from .reports import report_conda_forge_names_from_import_map
from .utils import pkg_data

logger = logging.getLogger('depfinder')

STRICT_CHECKING = False


def simple_import_search(path_to_source_code, remap=True, ignore=None):
    """Return all imported modules in all .py files in `path_to_source_code`

    Parameters
    ----------
    path_to_source_code : str
    remap : bool, optional
        Normalize the import names to be synonymous with their conda/pip names
    ignore : list, optional
        String pattern which if matched causes the file to not be inspected

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
        # if ignore provided skip things which match the ignore pattern
        if ignore and any(fnmatch(path, i) for i in ignore):
            continue
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
    try:
        from IPython.core.inputsplitter import IPythonInputSplitter
        transform = IPythonInputSplitter(line_input_checker=False).transform_cell
    except:
        transform = lambda code: code

    nb = json.load(io.open(path_to_notebook, encoding='utf8'))
    codeblocks = [''.join(cell['source']) for cell in nb['cells']
                  if cell['cell_type'] == 'code']
    all_deps = defaultdict(set)

    for codeblock in codeblocks:
        codeblock = transform(codeblock)
        # TODO this may fail on py2/py3 syntax when running in the other runtime. 
        # May want to consider updating some error handling around that case.
        # Will wait until that use case surfaces before modifying
        deps_dict = get_imported_libs(codeblock).describe()
        for k, v in deps_dict.items():
            all_deps[k].update(v)

    all_deps = {k: sorted(list(v)) for k, v in all_deps.items()}
    if remap:
        return sanitize_deps(all_deps)
    return all_deps


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
    from .inspection import PACKAGE_NAME
    new_deps_dict = {}
    list_of_possible_fakes = set([v for val in pkg_data['_FAKE_PACKAGES'].values() for v in val])
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
            pkg_to_add = pkg_data['_PACKAGE_MAPPING'].get(pkg, pkg)
            if pkg != pkg_to_add:
                logger.debug("Renaming {} to {}".format(pkg, pkg_to_add))
            new_deps_dict[k].add(pkg_to_add)
    new_deps_dict = {k: sorted(list(v)) for k, v in new_deps_dict.items() if v}
    return new_deps_dict


def simple_import_search_conda_forge_import_map(path_to_source_code, builtins=None):
    """Return all conda-forge packages used in all .py files in `path_to_source_code`

    Parameters
    ----------
    path_to_source_code : str
    builtins : list, optional
        List of python builtins to partition into their own section

    Returns
    -------
    dict
        The list of all imported modules, sorted according to the keys listed
        in the docstring of depfinder.ImportCatcher.describe()

    Examples
    --------
    >>> depfinder.simple_import_search_conda_forge_import_map('/path/to/depfinder/source')
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
    # run depfinder on source code
    total_imports_list = []
    for _, _, c in iterate_over_library(path_to_source_code):
        total_imports_list.append(c.total_imports)
    total_imports = defaultdict(dict)
    for total_import in total_imports_list:
        for name, md in total_import.items():
            total_imports[name].update(md)
    imports, _, _ = report_conda_forge_names_from_import_map(
        total_imports, builtin_modules=builtins,
    )
    return {k: sorted(list(v)) for k, v in imports.items()}
