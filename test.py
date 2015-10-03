import depfinder

easy_imports = [
    # easy_imports
    ('import foo, bar', set(['foo', 'bar'])),
    ('import depfinder', set(['depfinder'])),
    # from imports
    ('from matplotlib import pyplot', set(['matplotlib'])),
    ('from numpy import warnings as npwarn', set(['numpy'])),
    # relative imports
    ('from . import bar', set()),
    ('from . import bar as baz', set()),
    ('from . import bar, baz, eggs as green', set()),
]


def _test_yielder(test_list, target_list):
    assert depfinder.get_imported_libs(test_list)['probably_fine'] == target_list


def test_imports():
    for test_list, target_list in easy_imports:
        yield _test_yielder, test_list, target_list
