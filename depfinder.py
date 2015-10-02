import re
import os

regexer = re.compile(r'(from?)?([a-zA-Z0-9\.])?(import?)(.*)')


def determine_imported_library(line):
    res = regexer.findall(line)
    print(res)
    res = [r for tup in res for r in tup if r]
    print(res)
    return res

def iterate_over_library(path_to_source_code):
    libs = []
    for parent, folders, files in os.walk(path_to_source_code):
        for file in files:
            if file.endswith('.py'):
                # search it for imports
                with open(file, 'r') as f:
                    for line in f.readlines():
                        library = determine_imported_library(line)
                        libs.append(library[1])

    return libs
