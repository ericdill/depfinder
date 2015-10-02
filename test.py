import depfinder

test_cases = [
    ('import depfinder', 'depfinder'),
    ('from matplotlib import pyplot', 'matplotlib'),
    ('from numpy import warnings as npwarn', 'numpy'),
    ("""from long_library_name import (long_module_name as lmn,
                                   an_even_longer_module_name as elmn)""",
                                   'long_library_name'),
    ("""from long_library_name import long_module_name as lmn, \
                                  an_even_longer_module_name as elmn""",
                                  'long_library_name'),
    ('from . import bar', '.'),
    ('from . import bar as baz', '.'),
]


def _test_helper(test_string, target_string):
    assert depfinder.determine_imported_library(test_string)[1] == target_string

def test_determine_imported_library():
    for test_string, target_string in test_cases:
        yield _test_helper, test_string, target_string

# these are lines that definder.regexer should **not** think are import lines
lines_that_should_not_pass = [
    'some random list of characters',
    '"""\n',
]
