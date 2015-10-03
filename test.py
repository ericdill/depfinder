import depfinder
import copy

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
    {'targets': {'required': []},
     'code': 'from . import bar'},
    {'targets': {'required': ['bar']},
     'code': 'from .bar import baz'},
    {'targets': {'required': ['bar']},
     'code': 'from ..bar import baz'},
]

class Initter:
    def __init__(self, artifact):
        targets = artifact.get('targets', {})
        self.targets = {
            'required': set(targets.get('required', [])),
            'questionable': set(targets.get('questionable', []))
        }
        self.code = artifact['code']


def test_imports():
    for simple_import in complex_imports + simple_imports:
        test_object = Initter(simple_import)
        imports = depfinder.get_imported_libs(test_object.code)
        assert imports == test_object.targets
            # print('targets = %s' % targets)
            # print('code = %s\n\n' % code)
    # for targetse, target_list in simple_imports.items():
    #     yield _test_yielder, test_list, target_list


def test_relative_imports():
    # Ensure that relative imports are found when 'include_relative_imports'
    # is toggled on
    original_config = copy.copy(depfinder.conf)
    depfinder.conf['ignore_builtin_modules'] = True
    depfinder.conf['include_relative_imports'] = True

    for rel in relative_imports:
        test_object = Initter(rel)
        imports = depfinder.get_imported_libs(test_object.code)
        assert imports == test_object.targets

    # now we make sure that relative imports are being ignored when we turn
    # off that flag
    depfinder.conf['include_relative_imports'] = False

    for rel in relative_imports:
        test_object = Initter(rel)
        imports = depfinder.get_imported_libs(test_object.code)
        assert imports == {k: set() for k, v in test_object.targets.items()}

    # and now we reset the config back to its original state
    depfinder.conf = original_config