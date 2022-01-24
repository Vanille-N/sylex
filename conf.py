import tokenize as tok

class Conf:
    def __init__(*, name, root, files, features):
        self.name = name
        self.build_dir = f"build/{self.name}"
        self.root = root
        self.files = files
        self.features = features

def read_conf(fname):
    with open(fname, 'r') as f:
        text = f.read()
    chars = tok.chars_of_text(text)
    tokens = tok.tokens_of_chars(chars)
    try:
        res = tok.tree_of_tokens(tokens)
    except tok.toks.ParsingFailure as e:
        print(e)
        return None
    tree = res
    print(tree)
    raise NotImplementedError()
    ok, res = tree.lint()
    if not ok:
        print(res)
        return None
    return res

if __name__ == "__main__":
    print(read_conf("new-lang"))

