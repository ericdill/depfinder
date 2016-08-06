from __future__ import (unicode_literals, print_function, division,
                        absolute_import)
import depfinder
import subprocess
import os
from os.path import dirname, join
import pytest
import random
import itertools
from depfinder import cli
import six
import sys

random.seed(12345)


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


@pytest.fixture(scope="module")
def known_flags():
    # option_strings are the things like ['-h', '--help']
    # or are empty lists if the action is a positional
    flags = [o.option_strings for o in cli._init_parser()._actions]
    # drop the empty flags (these are positional arguments only
    flags = [flag for flag in flags if flag]
    # now flatten the nested list
    flags = [flag for flag_twins in flags for flag in flag_twins]
    return flags


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


def test_cli(capsys):
    """
    Test to ensure that the depfinder cli is finding the dependencies in the
    source the depfinder package that are listed in the requirements.txt file
    """
    old_argv = sys.argv
    sys.argv = ['depfinder', dirname(depfinder.__file__)]
    _run_cli()
    sys.argv = old_argv
    # read stdout and stderr with pytest's built-in capturing mechanism
    stdout, stderr = capsys.readouterr()
    dependencies_file = join(dirname(dirname(depfinder.__file__)),
                             'requirements.txt')
    print('stdout\n{}'.format(stdout))
    print('stderr\n{}'.format(stderr))
    dependencies = set([dep for dep in open(dependencies_file, 'r').read().split('\n') if dep])
    assert dependencies == set(eval(stdout)['required'])


def test_known_fail_cli(tmpdir):
    tmpfile = os.path.join(str(tmpdir), 'bad_file.txt')
    import this
    with open(tmpfile, 'w') as f:
        f.write("".join([this.d.get(this.c, this.c) for this.c in this.s]))

    with pytest.raises(RuntimeError):
        _run_cli(path_to_check=tmpfile)
