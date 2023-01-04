import sys
import logging

logger = logging.getLogger('depfinder')

if sys.version_info.major >= 10:
    builtin_modules = list(set(list(sys.stdlib_module_names) + list(sys.builtin_module_names)))
else:
    try:
        from stdlib_list import stdlib_list
        pyver = '%s.%s' % (sys.version_info.major, sys.version_info.minor)
        builtin_modules = stdlib_list(pyver)
        del pyver
    except ImportError:
        logger.exception('stdlib-list required for python <= 3.9')
        raise