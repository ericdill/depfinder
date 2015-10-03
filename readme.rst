.. image:: https://travis-ci.org/ericdill/depfinder.svg?branch=master
    :target: https://travis-ci.org/ericdill/depfinder
.. image:: http://codecov.io/github/ericdill/depfinder/coverage.svg?branch=master
    :target: http://codecov.io/github/ericdill/depfinder?branch=master


depfinder
---------
Find all the unique imports in your library, automatically, because who likes
do it by hand? Keeping track of imports in a rapidly evolving library is a
terrible chore for which I have great distaste.


Usage
-----

`depfinder` is not yet on pypi. For now, clone it from github and install it: ::

    git clone git@github.com:ericdill/depfinder
    cd depfinder
    python setup.py install

Then use it! ::

    python -c "
    import depfinder;
    tups = list(depfinder.iterate_over_library('.'));
    for tup in tups:
        print(tup)"

You should see ::

  ('setup', './setup.py', ImportCatcher: {'required': {'setuptools'}})
  ('test', './test.py', ImportCatcher: {'required': {'depfinder'}})
  ('depfinder', './depfinder.py', ImportCatcher: {'required': {'stdlib_list'}, 'builtin': {'__future__', 'ast', 'sys', 'os'}})


`iterate_over_library` is a function that yields tuples of `module_name`,
`full_path_to_module` and `ImportCatcher` objects.

- `module_name` is the name of the module (i.e., the file name without the
  `.py` suffix)
- `full_path_to_module` is the full path to the file
- `ImportCatcher` is a data bucket for information that was obtained by
  rendering the `module_name` as an Abstract Syntax Tree (AST) and searching the
  tree for import nodes.
