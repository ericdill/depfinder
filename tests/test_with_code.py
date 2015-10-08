import depfinder

# Testing spec:
# - targets: dict
#   - required: Iterable of library imports that should be found
#   - questionable: Iterable of library imports that should be found
# - code: String. Code that will be parsed to look for imports


complex_imports = [
    {'targets':
     {'questionable': ['atom', 'chemist', 'molecule', 'physicist']},
     'code': """try:
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
]


simple_imports = [
    {'targets': {'required': ['foo']},
     'code': 'import foo'},
    {'targets': {'required': ['bar', 'foo']},
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
        self.targets = {k: set(v) for k, v in targets.items()}
        self.code = artifact['code']


def test_imports():
    for simple_import in complex_imports + simple_imports:
        test_object = Initter(simple_import)
        imports = depfinder.get_imported_libs(test_object.code)
        assert imports.describe() == test_object.targets


def test_relative_imports():
    for rel in relative_imports:
        test_object = Initter(rel)
        imports = depfinder.get_imported_libs(test_object.code)
        assert imports.describe() == test_object.targets


def test_for_smoke():
    """Do not validate the output of the functions, just make sure that calling
    them does not make depfinder blow up
    """
    deps = list(depfinder.iterate_over_library('.'))
    assert deps is not None
    assert str(deps) is not None
    assert repr(deps) is not None
    # hit the simple api
    assert depfinder.simple_import_search('.') is not None