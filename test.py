import depfinder

# Testing spec:
# - targets: dict
#   - required: Iterable of library imports that should be found
#   - questionable: Iterable of library imports that should be found
# - code: String. Code that will be parsed to look for imports


complex_imports = [
    {'targets':
     {'questionable': ['molecule', 'atom', 'physicist']},
     'code': """
try:
    import molecule
except ImportError:
    import atom
finally:
    import physicist"""
    },
]

simple_imports = [
    {'targets': {'required': ['foo']},
     'code': 'import foo'},
    {'targets': {'required': ['foo', 'bar']},
     'code': 'import foo, bar'},
    {'targets': {'required': ['depfinder']},
     'code': 'import depfinder'},
    {'targets': {'required': ['matplotlib']},
     'code': 'from matplotlib import pyplot'},
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

class Initter:
    def __init__(self, artifact):
        targets = artifact.get('targets', {})
        self.targets = {
            'required': set(targets.get('required', [])),
            'questionable': set(targets.get('questionable', [])),
            'builtin': set(targets.get('builtin', [])),
            'relative': set(targets.get('relative', []))
        }
        self.code = artifact['code']


def test_imports():
    for simple_import in complex_imports + simple_imports:
        test_object = Initter(simple_import)
        imports = depfinder.get_imported_libs(test_object.code)
        assert imports.describe() == test_object.targets
            # print('targets = %s' % targets)
            # print('code = %s\n\n' % code)
    # for targetse, target_list in simple_imports.items():
    #     yield _test_yielder, test_list, target_list


def test_relative_imports():
    for rel in relative_imports:
        test_object = Initter(rel)
        imports = depfinder.get_imported_libs(test_object.code)
        assert imports.describe() == test_object.targets


def test_for_smoke():
    depfinder.iterate_over_library('.')