import depfinder
from nbformat import v4
from test_with_code import complex_imports, relative_imports, simple_imports
import pytest
import tempfile
import os
from collections import defaultdict

@pytest.mark.parametrize("import_list_dict", [complex_imports, simple_imports,
                                              relative_imports])
def tester(import_list_dict):
    # http://nbviewer.ipython.org/gist/fperez/9716279
    for import_dict in import_list_dict:
        code = import_dict['code']
        target = import_dict['targets']
        nb = v4.new_notebook()
        cells = [v4.new_code_cell(code)]
        nb['cells'].extend(cells)
        fname = tempfile.NamedTemporaryFile(suffix='.ipynb').name
        with open(fname, 'w') as f:
            f.write(v4.writes(nb))

        # parse the notebook!
        assert target == depfinder.notebook_path_to_dependencies(fname)

        os.remove(fname)



def test_multiple_code_cells():
    nb = v4.new_notebook()
    targets = defaultdict(set)
    import_list_dict = complex_imports + relative_imports + simple_imports
    # http://nbviewer.ipython.org/gist/fperez/9716279
    for import_dict in import_list_dict:
        code = import_dict['code']
        target = import_dict['targets']
        cells = [v4.new_code_cell(code)]
        nb['cells'].extend(cells)
        for k, v in target.items():
            targets[k].update(set(v))

    # turn targets into a dict of sorted lists
    targets = {k: sorted(list(v)) for k, v in targets.items()}

    fname = tempfile.NamedTemporaryFile(suffix='.ipynb').name
    with open(fname, 'w') as f:
        f.write(v4.writes(nb))

    print('temp file name = %s' % fname)

    # parse the notebook!
    assert targets == depfinder.notebook_path_to_dependencies(fname)

    # note this might fail on windows
    # os.unlink(fname)
