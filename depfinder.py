import re
import os

regexer = re.compile(r'(from)?(.*)?(import)(.*)')

skip_conditions = {
    'startswith': ['#']
}

def determine_imported_library(line):
    res = regexer.findall(line)
    print(res)
    res = [r.strip() for tup in res for r in tup if r]
    print(res)
    return res

def iterate_over_library(path_to_source_code):
    libs = {}
    for parent, folders, files in os.walk(path_to_source_code):
        for file in files:
            if file.endswith('.py'):
                full_file_path = os.path.join(parent, file)
                # search it for imports
                with open(full_file_path, 'r') as f:
                    for line in f.readlines():
                        # here's a real easy hack
                        if 'import' not in line:
                            continue
                        library = determine_imported_library(line)
                        libs[line] = library[1]

    return libs
