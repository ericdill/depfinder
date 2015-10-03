.. image:: https://travis-ci.org/ericdill/depfinder.svg?branch=master
    :target: https://travis-ci.org/ericdill/depfinder
.. image:: http://codecov.io/github/ericdill/depfinder/coverage.svg?branch=master
    :target: http://codecov.io/github/ericdill/depfinder?branch=master


depfinder
---------
Find all the unique imports in your library, automatically, because who likes
do it by hand? Also, and perhaps a bit more seriously, keeping track of
imports in a rapidly evolving library is a terrible chore for which I have a
great amount of personal distaste.

Usage
-----
::

    git clone git@github.com:ericdill/depfinder
    cd depfinder
    python setup.py install
    python -c "
    import depfinder;
    libs = depfinder.iterate_over_library('.');
    print(libs)"

The return value of `iterate_over_library` has two keys:
`definitely_questionable` and `probably_fine`.  `definitely_questionable` are
imports that were found within a try/except block and `probably_fine` are
imports that occur at the top level of a module.


