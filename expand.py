from error import Err
import re

def expand(file):
    print(file)
    if not file.endswith("tex"): return
    # Replace $(HERE) with the actual path
    file_root = file.replace("build/", "")
    here = "__".join(file_root.split("__")[:-1])
    if here != "": here += "__"
    re_here = r"\$\(HERE\)/"
    with open(file, 'r') as f:
        text = f.read()
    text = re.sub(re_here, here, text)
    # Replace "/" with "__"
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
