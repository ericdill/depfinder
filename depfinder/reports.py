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
from pprint import pformat
import sys
from concurrent.futures._base import as_completed
from concurrent.futures.thread import ThreadPoolExecutor
from fnmatch import fnmatch
from functools import lru_cache

import requests

from .stdliblist import builtin_modules as _builtin_modules
from .utils import SKETCHY_TYPES_TABLE

logger = logging.getLogger("depfinder")


@lru_cache()
def _import_map_num_letters():
    req = requests.get(
        "https://raw.githubusercontent.com/regro/libcfgraph/master"
        "/import_maps_meta.json"
    )
    req.raise_for_status()
    return int(req.json()["num_letters"])


@lru_cache()
def _import_map_cache(import_first_letters):
    req = requests.get(
        f"https://raw.githubusercontent.com/regro/libcfgraph"
        f"/master/import_maps/{import_first_letters.lower()}.json"
    )
    if not req.ok:
        print("Request to {req_url} failed".format(req_url=req.url))
        return {}
    return {k: set(v["elements"]) for k, v in req.json().items()}


FILE_LISTING = requests.get(
    "https://raw.githubusercontent.com/regro/libcfgraph/master/.file_listing.json"
).json()
# TODO: upstream this to libcfgraph so we just request it, so we reduce bandwidth requirements
ARTIFACT_TO_PKG = {
    v.split("/")[-1].rsplit(".", 1)[0]: v.split("/")[1]
    for v in FILE_LISTING
    if "artifacts" in v
}
hubs_auths = requests.get(
    "https://raw.githubusercontent.com/regro/cf-graph-countyfair/master/ranked_hubs_authorities.json"
).json()


def extract_pkg_from_import(name):
    """Provide the name of the package that matches with the import provided,
    with the maps between the imports and artifacts and packages that matches

    Parameters
    ----------
    name : str
        The name of the import to be searched for

    Returns
    -------

    """
    num_letters = _import_map_num_letters()
    original_name = name
    while True:
        try:
            fllt = name[: min(len(name), num_letters)]
            import_map = _import_map_cache(fllt)
            supplying_artifacts = import_map[name]
        except KeyError:
            if "." not in name:
                return original_name, {}, {}
            name = name.rsplit(".", 1)[0]
            pass
        else:
            break
    import_to_artifact = {name: supplying_artifacts}
    # TODO: launder supplying_pkgs through centrality scoring so we have one thing
    #  but keep the rest for the more detailed reports
    supplying_pkgs = {ARTIFACT_TO_PKG[k] for k in supplying_artifacts}
    import_to_pkg = {name: supplying_pkgs}

    return (
        next(iter(k for k in hubs_auths if k in supplying_pkgs), original_name),
        import_to_artifact,
        import_to_pkg,
    )


def recursively_search_for_name(name, module_names):
    while True:
        if name in module_names:
            logger.debug("found name: %s in module_names var", name)
            return name
        else:
            if "." in name:
                name2 = name.rsplit(".", 1)[0]
                logger.debug('found "." in name, splitting %s to %s', name, name2)
                name = name2
            else:
                logger.debug("found nothing, returning False")
                return False


def report_conda_forge_names_from_import_map(
    total_imports, builtin_modules=None, ignore=None
):
    if ignore is None:
        ignore = []
    if builtin_modules is None:
        builtin_modules = _builtin_modules
    report_keys = [
        "required",
        "questionable",
        "builtin",
        "questionable no match",
        "required no match",
    ]
    report = {k: set() for k in report_keys}
    import_to_pkg = {k: {} for k in report_keys}
    import_to_artifact = {k: {} for k in report_keys}
    futures = {}

    with ThreadPoolExecutor() as pool:
        for name, md in total_imports.items():
            logger.debug("checking for match against name: %s", name)
            if all(
                [
                    any(fnmatch(filename, ignore_element) for ignore_element in ignore)
                    for filename, _ in md
                ]
            ):
                logger.debug("found ignore match for name: %s", name)
                continue
            elif recursively_search_for_name(name, builtin_modules):
                logger.debug("found builtin module: %s", name)
                report["builtin"].add(name)
                continue
            future = pool.submit(extract_pkg_from_import, name)
            futures[future] = md

    logger.debug("futures: %s", pformat(futures))

    for future in as_completed(futures):
        md = futures[future]
        most_likely_pkg, _import_to_artifact, _import_to_pkg = future.result()

        for (filename, lineno), import_metadata in md.items():
            # Make certain to throw out imports, since an import can happen multiple times
            # under different situations, import matplotlib is required by a test file
            # but is questionable for a regular file
            if any(fnmatch(filename, ignore_element) for ignore_element in ignore):
                continue
            if any(import_metadata.get(v, False) for v in SKETCHY_TYPES_TABLE.values()):
                # if we couldn't find any artifacts to represent this then it doesn't exist in our maps
                if not _import_to_artifact:
                    report_key = "questionable no match"
                else:
                    report_key = "questionable"
            else:
                # if we couldn't find any artifacts to represent this then it doesn't exist in our maps
                if not _import_to_artifact:
                    report_key = "required no match"
                else:
                    report_key = "required"

            report[report_key].add(most_likely_pkg)
            import_to_pkg[report_key].update(_import_to_pkg)
            import_to_artifact[report_key].update(_import_to_artifact)

    logger.debug("builtins: %s", sorted(builtin_modules))
    return report, import_to_artifact, import_to_pkg
