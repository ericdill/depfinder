import depfinder

easy_imports = [
    # easy_imports
    ('import foo, bar', ['foo', 'bar']),
    ('import depfinder', ['depfinder']),
    # from imports
    ('from matplotlib import pyplot', ['matplotlib']),
    ('from numpy import warnings as npwarn', ['numpy']),
    # relative imports
    ('from . import bar', []),
    ('from . import bar as baz', []),
    ('from . import bar, baz, eggs as green', []),
]


def _test_yielder(test_list, target_list):
    depfinder.get_imported_libs(test_list) == target_list


def test_imports():
    for test_list, target_list in easy_imports:
        yield _test_yielder, test_list, target_list
