import depfinder
import subprocess

def test_cli():
    output = subprocess.check_output(['depfinder', depfinder.__file__]).decode()
    assert 'stdlib_list' in output

