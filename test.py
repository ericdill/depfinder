from __future__ import (unicode_literals, print_function, division,
                        absolute_import)

import contextlib
import itertools
import os
import random
import subprocess
import sys
import tempfile
from collections import defaultdict
from os.path import dirname, join

import pytest
import six
from nbformat import v4

import depfinder
from depfinder import cli, main, inspection, parse_file
from depfinder.main import simple_import_search_conda_forge_import_map, simple_import_to_pkg_map
from depfinder.reports import report_conda_forge_names_from_import_map, extract_pkg_from_import, \
    recursively_search_for_name, _builtin_modules

random.seed(12345)

# Testing spec:
# - targets: dict
#   - required: Iterable of library imports that should be found
#   - questionable: Iterable of library imports that should be found
# - code: String. Code that will be parsed to look for imports


complex_imports = [
    {'targets':
         {'questionable': ['atom', 'chemist', 'molecule', 'physicist']},
     'code': """
try:
    import molecule
except ImportError:
    import atom
else:
    import chemist
finally:
    import physicist"""
     },
    {'targets': {'required': ['foo'], 'builtin': ['os']},
     'code': """
import foo
try:
    import os
except ImportError:
    # why would you put this in a try block??
    pass"""},
    {'targets': {'required': ['toplevel', 'toplevelfrom'],
                 'questionable': ['function_inside_class',
                                  'function_inside_class_from',
                                  'inside_class',
                                  'inside_class_from',
                                  'inside_function',
                                  'inside_function_from'],
                 'relative': ['relative_function',
                              'relative_function_inside_class',
                              'relative_inside_class'],
                 'builtin': ['os', 'pprint']},
     'code': """
from toplevelfrom import some_function
import toplevel
def function():
    import inside_function
    from inside_function_from import another_function
    from .relative_function import random_function
class Class:
    import inside_class
    from inside_class_from import some_function
    from .relative_inside_class import a_third_function
    import os
    def __init__(self):
        import function_inside_class
        from function_inside_class_from import some_function
        from .relative_function_inside_class import a_third_function
        import pprint
"""},

    {'targets':
         {'questionable': ['chico', 'groucho', 'harpo']},
     'code': """
if this:
    import groucho
elif that:
    import harpo
else:
    import chico"""
     },
]

simple_imports = [
    {'targets': {'required': ['foo']},
     'code': 'import foo'},
    {'targets': {'required': ['bar', 'foo']},
     'code': 'import foo, bar'},
    {'targets': {'required': ['numpy']},
     'code': 'import numpy'},
    {'targets': {'required': ['matplotlib']},
     'code': 'from matplotlib import pyplot'},
    # Hit the fake packages code block in main.sanitize_deps()
    {'targets': {'required': ['numpy']},
     'code': 'from numpy import warnings as npwarn'},
]

relative_imports = [
    {'targets': {},
     'code': 'from . import bar'},
    {'targets': {'relative': ['bar']},
     'code': 'from .bar import baz'},
    {'targets': {'relative': ['bar']},
     'code': 'from ..bar import baz'},
]

@pytest.fixture(scope='module')
def using_stdlib_list():
    try:
        import stdlib_list
        return True
    except ImportError:
        return False

def test_nested_namespace_builtins(using_stdlib_list):
    if using_stdlib_list:
        expected = {'builtin': ['concurrent.futures']}
    else:
        expected = {'builtin': ['concurrent']}
    code = 'import concurrent.futures'



    test_object = Initter({'targets': expected, 'code': code})
    imports = main.get_imported_libs(test_object.code)
    assert imports.describe() == test_object.targets


class Initter(object):
    def __init__(self, artifact):
        targets = artifact.get('targets', {})
        self.targets = {k: set(v) for k, v in targets.items()}
        self.code = artifact['code']


def test_imports():
    for simple_import in complex_imports + simple_imports:
        test_object = Initter(simple_import)
        imports = main.get_imported_libs(test_object.code)
        assert imports.describe() == test_object.targets


def test_relative_imports():
    for rel in relative_imports:
        test_object = Initter(rel)
        imports = main.get_imported_libs(test_object.code)
        assert imports.describe() == test_object.targets


def test_for_smoke():
    """Do not validate the output of the functions, just make sure that calling
    them does not make depfinder blow up
    """
    deps = list(main.iterate_over_library('.'))
    assert deps is not None
    assert str(deps) is not None
    assert repr(deps) is not None
    # hit the simple api
    assert main.simple_import_search('.') is not None


### NOTEBOOK TESTING CODE ###

@contextlib.contextmanager
def write_notebook(cells):
    nb = v4.new_notebook()
    nb['cells'] = [v4.new_code_cell(code_cell) for code_cell in cells]
    fname = tempfile.NamedTemporaryFile(suffix='.ipynb').name
    with open(fname, 'w') as f:
        f.write(v4.writes(nb))

    try:
        yield fname
    finally:
        os.remove(fname)


def test_notebook_remapping():
    code = "import mpl_toolkits"
    with write_notebook([code]) as fname:
        deps = main.notebook_path_to_dependencies(fname, remap=False)
        assert {'required': ['mpl_toolkits']} == deps
        assert {} == main.notebook_path_to_dependencies(fname)


@pytest.mark.parametrize("import_list_dict", [complex_imports,
                                              simple_imports,
                                              relative_imports])
def tester(import_list_dict, capsys):
    # http://nbviewer.ipython.org/gist/fperez/9716279
    for import_dict in import_list_dict:
        cell_code = [import_dict['code']]
        target = import_dict['targets']
        with write_notebook(cell_code) as fname:
            # parse the notebook!
            assert target == main.notebook_path_to_dependencies(fname)
            # check the notebook cli
            _run_cli(path_to_check=fname)
            stdout, stderr = capsys.readouterr()
            assert target == eval(stdout)


def test_multiple_code_cells(capsys):
    targets = defaultdict(set)
    import_list_dict = complex_imports + relative_imports + simple_imports
    # http://nbviewer.ipython.org/gist/fperez/9716279
    code_for_cells = []
    for import_dict in import_list_dict:
        code_for_cells.append(import_dict['code'])
        target = import_dict['targets']
        for k, v in target.items():
            targets[k].update(set(v))

    # turn targets into a dict of sorted lists
    targets = {k: sorted(list(v)) for k, v in targets.items()}
    with write_notebook(code_for_cells) as fname:
        # parse the notebook!
        assert targets == main.notebook_path_to_dependencies(fname)
        # check the notebook cli
        _run_cli(path_to_check=fname)
        stdout, stderr = capsys.readouterr()
        assert targets == eval(stdout)


### CLI TESTING CODE ###

def _process_args(path_to_check, extra_flags):
    """
    Parameters
    ----------
    path_to_check : str, optional
        Defaults to the directory of the depfinder package
    extra_flags : list, optional
        List of extra command line flags to pass.
        Defaults to passing nothing extra.
    """
    if path_to_check is None:
        path_to_check = dirname(depfinder.__file__)
    if isinstance(extra_flags, six.string_types):
        extra_flags = [extra_flags]
    if extra_flags is None:
        extra_flags = []

    return path_to_check, extra_flags


def _subprocess_cli(path_to_check=None, extra_flags=None):
    path_to_check, extra_flags = _process_args(path_to_check, extra_flags)
    p = subprocess.Popen(
        ['depfinder', path_to_check] + extra_flags,
        env=dict(os.environ),
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE
    )

    stdout, stderr = p.communicate()
    returncode = p.returncode
    return stdout, stderr, returncode


def _run_cli(path_to_check=None, extra_flags=None):
    """
    Helper function to run depfinder in its cli mode
    """
    path_to_check, extra_flags = _process_args(path_to_check, extra_flags)
    sys.argv = ['depfinder', path_to_check] + extra_flags
    cli.cli()
    return None


def known_flags():
    # option_strings are the things like ['-h', '--help']
    # or are empty lists if the action is a positional
    flags = [o.option_strings for o in cli._init_parser()._actions]
    # drop the empty flags (these are positional arguments only
    flags = [flag for flag in flags if flag]
    # now flatten the nested list
    flags = [flag for flag_twins in flags for flag in flag_twins]
    flags.remove('-k')
    flags.remove('--key')
    flags.remove('--pdb')
    flags.remove('--ignore')
    flags.remove('--custom-namespaces')
    flags.extend(['-k all', '-k required', '-k optional', '-k builtin',
                  '-k relative'])
    return flags


@pytest.fixture(scope="module")
def flags():
    yield known_flags()


@pytest.mark.parametrize(
    'flags',
    itertools.chain(
        [random.sample(known_flags(), i) for i in range(1, len(known_flags()))]
    )
)
def test_cli_with_random_flags(flags):
    """
    More of a fuzz test for depfinder than a unit test.

    Parameters
    ----------
    flags : list
        Random combination of valid command line flags
    """
    out, err, returncode = _subprocess_cli(extra_flags=flags)
    if returncode != 0:
        # The only thing that I know of that will exit with a nonzero status
        # is if you try to combine quiet mode and verbose mode. This handles
        # that case
        quiet = {'-q', '--quiet'}
        verbose = {'-v', '--verbose'}
        flags = set(flags)
        assert flags & quiet != set() and flags & verbose != set()
        return

    assert returncode == 0


@pytest.mark.parametrize(
    'path, req',
    ((dirname(depfinder.__file__), None),
     (join(dirname(depfinder.__file__), 'main.py'), set()))
)
def test_cli(path, req, capsys):
    """
    Test to ensure that the depfinder cli is finding the dependencies in the
    source the depfinder package that are listed in the requirements.txt file
    """
    main.PACKAGE_NAME = None
    old_argv = sys.argv
    sys.argv = ['depfinder']
    _run_cli(path_to_check=path)
    sys.argv = old_argv
    # read stdout and stderr with pytest's built-in capturing mechanism
    stdout, stderr = capsys.readouterr()
    print('stdout\n{}'.format(stdout))
    print('stderr\n{}'.format(stderr))
    if req is None:
        dependencies_file = join(dirname(dirname(depfinder.__file__)),
                                 'requirements.txt')
        dependencies = set([dep for dep in open(dependencies_file, 'r').read().split('\n') if not dep.startswith("stdlib")])
    else:
        dependencies = req
    assert dependencies == set(eval(stdout).get('required', set()))


def test_known_fail_cli(tmpdir):
    tmpfile = os.path.join(str(tmpdir), 'bad_file.txt')
    import this
    with open(tmpfile, 'w') as f:
        f.write("".join([this.d.get(this.c, this.c) for this.c in this.s]))

    with pytest.raises(RuntimeError):
        _run_cli(path_to_check=tmpfile)


def test_known_fail_cli2():
    with pytest.raises(cli.InvalidSelection):
        _run_cli(extra_flags=['-q', '-v'])


@pytest.mark.parametrize(
    'path',
    (dirname(depfinder.__file__),
     join(dirname(depfinder.__file__), 'main.py'))
)
def test_individual_args(path, flags):
    for flag in flags:
        if flag in ['-h', '--help']:
            # skip the help messages since they cause the system to exit
            continue
        _run_cli(path_to_check=path, extra_flags=[flag])
        _run_cli(path_to_check=path, extra_flags=[flag])


def test_fake_packages():
    fake_import = "import mpl_toolkits"
    imports = main.get_imported_libs(fake_import)
    assert imports.describe() == {'required': {'mpl_toolkits'}}
    assert main.sanitize_deps(imports.describe()) == {}


def test_get_top_level_import():
    name = 'this.that.something'
    top_level_name = inspection.get_top_level_import_name(name)
    assert top_level_name == 'this'

    name = 'google.cloud.storage.something'
    top_level_name = inspection.get_top_level_import_name(name)
    assert top_level_name == 'google.cloud.storage'


def test_report_conda_forge_names_from_import_map():
    m, f, c = parse_file(join(dirname(depfinder.__file__), 'utils.py'))
    report, import_to_artifact, import_to_pkg = report_conda_forge_names_from_import_map(c.total_imports)
    assert report['required'] == {'pyyaml', 'requests'}


def test_report_conda_forge_names_from_import_map_ignore():
    m, f, c = parse_file(join(dirname(depfinder.__file__), 'inspection.py'))
    report, import_to_artifact, import_to_pkg = report_conda_forge_names_from_import_map(c.total_imports,
                                                                                         ignore=['*insp*'])
    assert report['required'] == set()


def test_simple_import_search_conda_forge_import_map():
    path_to_source = dirname(depfinder.__file__)
    expected_result = sorted(list({"pyyaml", "requests"}))
    report = simple_import_search_conda_forge_import_map(path_to_source)
    assert report['required'] == expected_result


@pytest.mark.parametrize('import_name, expected_result', [
    ('six.moves', 'six'),
    ('win32com.shell', 'pywin32'),
    ('win32com', 'pywin32'),
    # this comes from cython but doesn't seem to be a real pkg
    ('refnanny.hi', 'refnanny.hi')
])
def test_extract_pkg_from_import_for_complex_imports(import_name, expected_result):
    result, _, _ = extract_pkg_from_import(import_name)
    assert result == expected_result


@pytest.mark.parametrize('import_name, expected_result', [
    ('six.moves', False),
])
def test_search_for_name(import_name, expected_result):
    builtin_name_maybe = recursively_search_for_name(import_name, _builtin_modules)
    assert builtin_name_maybe == expected_result


def test_simple_import_to_pkg_map():
    path_to_source = dirname(depfinder.__file__)
    import_to_artifact = simple_import_to_pkg_map(path_to_source)
    expected_result = {'builtin': {},
                                  'questionable': {'stdlib_list': {'stdlib-list'}, 'IPython.core.inputsplitter': {'ipython', 'autovizwidget'}},
                                  'questionable no match': {},
                                  'required': {'requests': {'apache-libcloud',
                                                            'arm_pyart',
                                                            'autovizwidget',
                                                            'dbxfs',
                                                            'google-api-core',
                                                            'google-cloud-bigquery-storage-core',
                                                            'requests'},
                                               'yaml': {'google-cloud-bigquery-storage-core', 'pyyaml'}},
                                  'required no match': {}}
    assert import_to_artifact == expected_result