import matplotlib
import os
import depfinder
from pprint import pprint

depfinder_results = depfinder.iterate_over_library(os.path.dirname(matplotlib.__file__))

print('Results of depfinder\n'
      '--------------------')
pprint(depfinder_results)
