# depfinder
# Copyright (C) 2015 Eric Dill
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import, division, print_function
from argparse import ArgumentParser
from collections import defaultdict
import logging
import os
from pprint import pprint
import yaml
import sys
logger = logging.getLogger('depfinder')

from .main import (simple_import_search, notebook_path_to_dependencies,
                   parse_file, sanitize_deps)


class InvalidSelection(RuntimeError):
    pass


def _init_parser():
    p = ArgumentParser(
        description="""
Tool for inspecting the dependencies of your python project.
""",
    )
    p.add_argument(
        'file_or_directory',
        help=("Valid options are a single python file, a single jupyter "
              "(ipython) notebook or a directory of files that include "
              "python files")
    )
    p.add_argument(
        '-y',
        '--yaml',
        action='store_true',
        default=False,
        help=("Output in syntactically valid yaml when true. Defaults to "
              "%(default)s"))
    p.add_argument(
        '-V',
        '--version',
        action='store_true',
        default=False,
        help="Print out the version of depfinder and exit"
    )
    p.add_argument(
        '--no-remap',
        action='store_true',
        default=False,
        help=("Do not remap the names of the imported libraries to their "
              "proper conda name")
    )
    p.add_argument(
        '-v',
        '--verbose',
        action='store_true',
        default=False,
        help="Enable debug level logging info from depfinder"
    )
    p.add_argument(
        '-q',
        '--quiet',
        action='store_true',
        default=False,
        help="Turn off all logging from depfinder"
    )
    return p


def cli():
    p = _init_parser()
    args = p.parse_args()
    if args.verbose and args.quiet:
        msg = ("You have enabled both verbose mode (--verbose or -v) and "
               "quiet mode (-q or --quiet).  Please pick one. Exiting...")
        raise InvalidSelection(msg)

    # Configure Logging
    loglevel = logging.INFO
    if args.quiet:
        loglevel = logging.ERROR
    elif args.verbose:
        loglevel = logging.DEBUG
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(loglevel)
    f = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(f)
    stream_handler.setFormatter(formatter)
    logger.setLevel(loglevel)
    logger.addHandler(stream_handler)

    if args.version:
        # handle the case where the user just cares about the version. Print
        # version and exit
        from . import __version__
        print(__version__)
        return 0

    file_or_dir = args.file_or_directory

    def dump_deps(deps):
        """
        Helper function to print the dependencies to the console.

        Parameters
        ----------
        deps : dict
            Dictionary of dependencies that were found
        """
        if args.yaml:
            deps = {k: list(v) for k, v in deps.items()}
            print(yaml.dump(deps, default_flow_style=False))
        else:
            pprint(deps)

    if os.path.isdir(file_or_dir):
        logger.debug("Treating {} as a directory and recursively searching "
                     "it for python files".format(file_or_dir))
        # directories are a little easier from the purpose of the API call.
        # print the dependencies to the console and then exit
        deps = simple_import_search(file_or_dir, remap=not args.no_remap)
        dump_deps(deps)
        return 0
    elif os.path.isfile(file_or_dir):
        if file_or_dir.endswith('ipynb'):
            logger.debug("Treating {} as a jupyter notebook and searching "
                         "all of its code cells".format(file_or_dir))
            deps = notebook_path_to_dependencies(file_or_dir,
                                                 remap=not args.no_remap)
            sanitized = sanitize_deps(deps)
            # print the dependencies to the console and then exit
            dump_deps(sanitized)
            return 0
        elif file_or_dir.endswith('.py'):
            logger.debug("Treating {} as a single python file"
                         "".format(file_or_dir))
            mod, path, import_finder = parse_file(file_or_dir)
            mods = defaultdict(set)
            for k, v in import_finder.describe().items():
                mods[k].update(v)
            deps = {k: sorted(list(v)) for k, v in mods.items() if v}

            sanitized = sanitize_deps(deps)
            # print the dependencies to the console and then exit
            dump_deps(sanitized)
            return 0
        else:
            # Any file with a suffix that is not ".ipynb" or ".py" will not
            # be parsed correctly
            msg = ("depfinder is only configured to work with jupyter "
                   "notebooks and python source code files. It is anticipated "
                   "that the file {} will not work with depfinder"
                   "".format(file_or_dir))
            raise RuntimeError(msg)
