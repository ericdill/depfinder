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
import sys
from concurrent.futures._base import as_completed
from concurrent.futures.thread import ThreadPoolExecutor
from functools import lru_cache

import requests
from stdlib_list import stdlib_list

from .utils import SKETCHY_TYPES_TABLE

logger = logging.getLogger('depfinder')

pyver = '%s.%s' % (sys.version_info.major, sys.version_info.minor)
_builtin_modules = stdlib_list(pyver)
del pyver


@lru_cache()
def _import_map_cache(import_first_two_letters):
    return {k: set(v['elements']) for k, v in requests.get(
        f'https://raw.githubusercontent.com/regro/libcfgraph'
        f'/master/import_maps/{import_first_two_letters.lower()}.json').json().items()}


FILE_LISTING = requests.get('https://raw.githubusercontent.com/regro/libcfgraph/master/.file_listing.json').json()
# TODO: upstream this to libcfgraph so we just request it, so we reduce bandwidth requirements
ARTIFACT_TO_PKG = {v.split('/')[-1].rsplit('.', 1)[0]: v.split('/')[1] for v in FILE_LISTING}

hubs_auths = requests.get(
    'https://raw.githubusercontent.com/regro/cf-graph-countyfair/master/ranked_hubs_authorities.json').json()


def extract_pkg_from_import(name):
    ftl = name[:2]
    import_map = _import_map_cache(ftl)
    supplying_artifacts = import_map[name]
    import_to_artifact = {name: supplying_artifacts}
    # TODO: launder supplying_pkgs through centrality scoring so we have one thing
    #  but keep the rest for the more detailed reports
    supplying_pkgs = {ARTIFACT_TO_PKG[k] for k in supplying_artifacts}
    import_to_pkg = {name: supplying_pkgs}

    return next(iter(k for k in hubs_auths if k in supplying_pkgs)), import_to_artifact, import_to_pkg


def report_conda_forge_names_from_import_map(total_imports, builtin_modules=None):
    if builtin_modules is None:
        builtin_modules = _builtin_modules
    report = {'required': set(), 'questionable': set(), 'builtin': set()}
    import_to_pkg = {}
    import_to_artifact = {}
    futures = {}

    with ThreadPoolExecutor() as pool:
        for name, md in total_imports.items():
            if name in builtin_modules:
                report['builtin'].add(name)
                continue
            future = pool.submit(extract_pkg_from_import, name)
            futures[future] = md
    for future in as_completed(futures):
        md = futures[future]
        most_likely_pkg, _import_to_artifact, _import_to_pkg = future.result()
        import_to_pkg.update(_import_to_pkg)
        import_to_artifact.update(_import_to_artifact)

        for (filename, lineno), import_metadata in md.items():
            if any(import_metadata.get(v, False) for v in SKETCHY_TYPES_TABLE.values()):
                report['questionable'].add(most_likely_pkg)
            else:
                report['required'].add(most_likely_pkg)
    return report, import_to_artifact, import_to_pkg
