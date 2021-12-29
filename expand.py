from error import Err
import re

def expand(file):
    print(file)
    if not file.endswith("tex"): return
    # Replace $(HERE) with the actual path
    file_root = file.replace("build/", "")
    split = file_root.split("__")
    if len(split) > 0: split.pop()
    here = "__".join(split)
    if len(split) > 0: split.pop()
    prev = "__".join(split)
    root = ""
    if here != "": here += "__"
    re_here = r"\$\(HERE\)/"
    re_root = r"\$\(ROOT\)/"
    re_prev = r"\$\(PREV\)/"
    with open(file, 'r') as f:
        text = f.read()
    text = re.sub(re_here, here, text)
    text = re.sub(re_root, root, text)
    text = re.sub(re_prev, prev, text)
    # Replace "/" with "__"
    # This is an overapproximation, since it will replace
    # all "/" in the same line as a input|includegraphics|include
    # If this causes problems I'll implement a finer criteria
    lines = text.split("\n")
    text = []
    re_slash = re.compile(r"\\(input|includegraphics|include)")
    for line in lines:
        search = re_slash.search(line)
        if search:
            line = line.replace("/", "__")
        text.append(line)
    with open(file, 'w') as f:
        f.write("\n".join(text))
