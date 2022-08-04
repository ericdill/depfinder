import sys


try:
    from stdlib_list import stdlib_list
    pyver = '%s.%s' % (sys.version_info.major, sys.version_info.minor)
    builtin_modules = stdlib_list(pyver)
    del pyver
except ImportError:
    # assuming py>=3.10
    builtin_modules = list(set(list(sys.stdlib_module_names) + list(sys.builtin_module_names)))
