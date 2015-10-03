import ast


def get_imported_libs(code):
    tree = ast.parse(code)
    # ast.Import represents lines like 'import foo' and 'import foo, bar'
    # the extra for name in t.names is needed, because names is a list that
    # would be ['foo'] for the first and ['foo', 'bar'] for the second
    imports = [name.name.split('.')[0] for t in tree.body
               if type(t) == ast.Import for name in t.names]
    # ast.ImportFrom represents lines like 'from foo import bar'
    import_froms = [t.module.split('.')[0] for t in tree.body if type(t) == ast.ImportFrom if t.module]
    return imports + import_froms
