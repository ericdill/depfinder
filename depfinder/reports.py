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

import logging
from concurrent.futures._base import as_completed
from concurrent.futures.thread import ThreadPoolExecutor
from fnmatch import fnmatch

from .stdliblist import builtin_modules as _builtin_modules
from .utils import SKETCHY_TYPES_TABLE


logger = logging.getLogger('depfinder')


def extract_pkg_from_import(name):
    """Provide the name of the package that matches with the import provided,
    with the maps between the imports and artifacts and packages that matches

    Parameters
    ----------
    name : str
        The name of the import to be searched for

    Returns
    -------
    most_likely_pkg : str
        The most likely conda-forge package.
    import_to_pkg : dict mapping str to sets
        A dict mapping the import name to a set of possible packages that supply that import.
    """
    from conda_forge_metadata.autotick_bot import map_import_to_package
    from conda_forge_metadata.libcfgraph import get_libcfgraph_pkgs_for_import
    try:
        supplying_pkgs, _ = get_libcfgraph_pkgs_for_import(name)
        best_import = map_import_to_package(name)
    except Exception:
        logger.exception(
            "could not get package name from conda-forge metadata "
            f"for import {name} due to an error"
        )
        supplying_pkgs = set()
        best_import = name
    import_to_pkg = {name: supplying_pkgs or set()}
    return best_import, import_to_pkg


def recursively_search_for_name(name, module_names):
    while True:
        if name in module_names:
            return name
        else:
            if '.' in name:
                name = name.rsplit('.', 1)[0]
            else:
                return False


def report_conda_forge_names_from_import_map(total_imports, builtin_modules=None, ignore=None):
    if ignore is None:
        ignore = []
    if builtin_modules is None:
        builtin_modules = _builtin_modules
    report_keys = ['required', 'questionable', 'builtin', 'questionable no match', 'required no match']
    report = {k: set() for k in report_keys}
    import_to_pkg = {k: {} for k in report_keys}
    futures = {}

    with ThreadPoolExecutor() as pool:
        for name, md in total_imports.items():
            if all([any(fnmatch(filename, ignore_element) for ignore_element in ignore) for filename, _ in md]):
                continue
            elif recursively_search_for_name(name, builtin_modules):
                report['builtin'].add(name)
                continue
            future = pool.submit(extract_pkg_from_import, name)
            futures[future] = md
    for future in as_completed(futures):
        md = futures[future]
        most_likely_pkg, _import_to_pkg = future.result()

        for (filename, lineno), import_metadata in md.items():
            # Make certain to throw out imports, since an import can happen multiple times
            # under different situations, import matplotlib is required by a test file
            # but is questionable for a regular file
            if any(fnmatch(filename, ignore_element) for ignore_element in ignore):
                continue
            _name = list(_import_to_pkg.keys())[0]
            if any(import_metadata.get(v, False) for v in SKETCHY_TYPES_TABLE.values()):
                # if we couldn't find any artifacts to represent this then it doesn't exist in our maps
                if not _import_to_pkg[_name]:
                    report_key = 'questionable no match'
                else:
                    report_key = 'questionable'
            else:
                # if we couldn't find any artifacts to represent this then it doesn't exist in our maps
                if not _import_to_pkg[_name]:
                    report_key = 'required no match'
                else:
                    report_key = 'required'

            report[report_key].add(most_likely_pkg)
            import_to_pkg[report_key].update(_import_to_pkg)

    return report, import_to_pkg
