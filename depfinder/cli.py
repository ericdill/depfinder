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


from .main import (simple_import_search, notebook_path_to_dependencies,
                   parse_file)

def cli():
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
    args = p.parse_args()
    if args.version:
        from . import __version__
        print(__version__)

    file_or_dir = args.file_or_directory

    def dump_deps(deps):
        if args.yaml:
            print(yaml.dump(deps, default_flow_style=False))
        else:
            pprint(deps)

    if os.path.isdir(file_or_dir):
        deps = simple_import_search(file_or_dir)
        dump_deps(deps)
    elif os.path.isfile(file_or_dir):
        if file_or_dir.endswith('ipynb'):
            deps = notebook_path_to_dependencies(file_or_dir)
            dump_deps(deps)
        elif file_or_dir.endswith('.py'):
            mod, path, catcher = parse_file(file_or_dir)
            mods = defaultdict(set)
            for k, v in catcher.describe().items():
                mods[k].update(v)
            deps = {k: sorted(list(v)) for k, v in mods.items() if v}
            dump_deps(deps)
        else:
            raise RuntimeError("I do not know what to do with the file %s" %
                               file_or_dir)
    else:
        raise RuntimeError("I do not know what to do with %s" % file_or_dir)


if __name__ == "__main__":
    cli()
