#!/usr/bin/env python
import sys
import pytest

if __name__ == "__main__":
    # show output results from every test function
    args = ["-v", "test.py"]
    # show the message output for skipped and expected failure tests
    args.append("-rxs")
    args.extend(sys.argv[1:])
    # call pytest and exit with the return code from pytest so that
    # travis will fail correctly if tests fail
    sys.exit(pytest.main(args))
