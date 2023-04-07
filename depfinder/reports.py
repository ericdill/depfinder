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
from fnmatch import fnmatch
from functools import lru_cache
from typing import Dict, Iterable, List, Set, Tuple
from pydantic import BaseModel
import pydantic

import requests

from .stdliblist import builtin_modules as _builtin_modules
from .utils import ImportMetadata, ast_types_to_str

logger = logging.getLogger("depfinder")


@lru_cache()
def _import_map_num_letters():
    """
    Conda-forge, in libcfgraph, has a ton of json files that are grouped by the first N letters of the import name. the value of N is maintained in the file "import_maps_meta.json. so we download that from libcfgraph and use it to determine how many letters to use in the import map file name we request from libcfgraph.
    """
    req = requests.get(
        "https://raw.githubusercontent.com/regro/libcfgraph/master/import_maps_meta.json"
    )
    req.raise_for_status()
    return int(req.json()["num_letters"])


@lru_cache()
def _import_map_cache(import_first_letters) -> Dict[str, Set[str]]:
    """Get the packages that supply the import provided"""
    req = requests.get(
        f"https://raw.githubusercontent.com/regro/libcfgraph"
        f"/master/import_maps/{import_first_letters.lower()}.json"
    )
    if not req.ok:
        print("Request to {req_url} failed".format(req_url=req.url))
        return {}
    return {k: set(v["elements"]) for k, v in req.json().items()}

class FileListingMeta(BaseModel):
    n_files: int

@lru_cache()
def _artifact_to_pkg_cache() -> Dict[str,str]:
    file_listing_meta_raw = requests.get(
        "https://raw.githubusercontent.com/regro/libcfgraph/master/.file_listing_meta.json"
    ).text
    file_listing_meta = FileListingMeta.parse_raw(file_listing_meta_raw)
    files_from_libcfgraph = (f'.file_listing_{i}.json' for i in range(file_listing_meta.n_files))
    artifact_to_pkg_name: Dict[str, str] = {}
    for filename in files_from_libcfgraph:
        file_listing: List[str] = requests.get(
            f"https://raw.githubusercontent.com/regro/libcfgraph/master/{filename}"
        ).json()
        # Each row looks something like:
        #   "artifacts/cryptography/conda-forge/osx-64/cryptography-39.0.0-py38ha6c3189_0.json",
        # ARTIFACT_TO_PKG ultimately results in something like
        # cryptography-39.0.0-py38ha6c3189_0: cryptography
        for entry in file_listing:
            artifacts, pkg_name, channel, platform, build_string = entry.split("/")
            build_string, suffix = build_string.rsplit('.', maxsplit=1)
            # TODO: upstream this to libcfgraph so we just request it, so we reduce bandwidth requirements
            artifact_to_pkg_name[build_string] = pkg_name

    return artifact_to_pkg_name

# hubs_auth is a ranked list of the conda-forge packages that are the
hubs_auths = requests.get(
    "https://raw.githubusercontent.com/regro/cf-graph-countyfair/master/ranked_hubs_authorities.json"
).json()


class PackageExtraction(BaseModel):
    import_name: str
    inferred_import_name: str
    supplying_artifacts: Set[str]
    supplying_pkgs: Set[str]
    most_likely_pkg: str


def extract_pkg_from_import(
    name: str,
) -> PackageExtraction:
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
                return PackageExtraction(
                    import_name=original_name,
                    inferred_import_name=name,
                    supplying_artifacts=set(),
                    supplying_pkgs=set(),
                    most_likely_pkg=original_name,
                )
            name = name.rsplit(".", 1)[0]
            pass
        else:
            break

    # import_to_artifact = {name: supplying_artifacts}
    # TODO: launder supplying_pkgs through centrality scoring so we have one thing
    #  but keep the rest for the more detailed reports
    artifact_to_pkg = _artifact_to_pkg_cache()
    supplying_pkgs = {artifact_to_pkg[k] for k in supplying_artifacts}
    # import_to_pkg = {name: supplying_pkgs}
    # get the "most authoritative" provider of the import from the sorted hubs_auth list from conda-forge
    ret = next(iter(k for k in hubs_auths if k in supplying_pkgs), original_name)

    report = PackageExtraction(
        import_name=original_name,
        inferred_import_name=name,
        supplying_artifacts=supplying_artifacts,
        supplying_pkgs=supplying_pkgs,
        most_likely_pkg=ret,
    )

    # return (
    #     ret,
    #     import_to_artifact,
    #     import_to_pkg,
    # )
    return report


def recursively_search_for_name(name, module_names):
    while True:
        if name in module_names:
            return name
        else:
            if "." in name:
                name = name.rsplit(".", 1)[0]
            else:
                return False


def report_conda_forge_names_from_import_map(
    total_imports: Dict[str, Dict[Tuple[str, int], ImportMetadata]],
    builtin_modules: Iterable[str] = (),
    ignore: Iterable[str] = _builtin_modules,
):
    report_keys = [
        "required",
        "questionable",
        "builtin",
        "questionable no match",
        "required no match",
    ]
    report: Dict[str, Set[str]] = {k: set() for k in report_keys}
    import_to_pkg = {k: {} for k in report_keys}
    import_to_artifact = {k: {} for k in report_keys}
    futures = {}

    with ThreadPoolExecutor() as pool:
        for name, md in total_imports.items():
            if all(
                [
                    any(fnmatch(filename, ignore_element) for ignore_element in ignore)
                    for filename, _ in md
                ]
            ):
                continue
            elif recursively_search_for_name(name, builtin_modules):
                report["builtin"].add(name)
                continue
            future = pool.submit(extract_pkg_from_import, name)
            futures[future] = md
    for future in as_completed(futures):
        md = futures[future]
        # most_likely_pkg, _import_to_artifact, _import_to_pkg = future.result()
        extraction: PackageExtraction = future.result()
        most_likely_pkg = extraction.most_likely_pkg
        _import_to_artifact = {
            extraction.inferred_import_name: extraction.supplying_artifacts
        }
        _import_to_pkg = {extraction.inferred_import_name: extraction.supplying_pkgs}

        for (filename, lineno), import_metadata in md.items():
            # Make certain to throw out imports, since an import can happen multiple times
            # under different situations, import matplotlib is required by a test file
            # but is questionable for a regular file
            if any(fnmatch(filename, ignore_element) for ignore_element in ignore):
                continue
            if any(
                import_metadata.__getattribute__(v) for v in ast_types_to_str.values()
            ):
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
    return report, import_to_artifact, import_to_pkg
