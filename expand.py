from error import Err
import re
import lib

@lib.Trace.path('Expand {BLU}{i}{WHT} to {BLU}{o}{WHT}\nwith features {features}')
def expand(*, i, o, features):
    Err.in_file(i)
    with open(i, 'r') as f:
        text = f.read()
    if i.endswith('tex'):
        text = filepaths(text, o)
        text = trim(text, features)
    with open(o, 'w') as f:
        f.write(text)

re_here = r"\$\(HERE\)/"
re_root = r"\$\(ROOT\)/"
re_prev = r"\$\(PREV\)/"
re_slash = re.compile(r"\\(input|includegraphics|include)")

@lib.Trace.path('Resolve file paths')
def filepaths(text, name):
    # Replace $(HERE) with the actual path
    file_root = name.replace("build/", "")
    split = file_root.split("__")
    if len(split) > 0: split.pop()
    here = "__".join(split)
    if len(split) > 0: split.pop()
    prev = "__".join(split)
    root = ""
    if here != "": here += "__"
    text = re.sub(re_here, here, text)
    text = re.sub(re_root, root, text)
    text = re.sub(re_prev, prev, text)
    # Replace "/" with "__"
    # This is an overapproximation, since it will replace
    # all "/" in the same line as a input|includegraphics|include
    # If this causes problems I'll implement a finer criteria
    lines = text.split("\n")
    text = []
    for line in lines:
        search = re_slash.search(line)
        if search:
            line = line.replace("/", "__")
        text.append(line)
    return "\n".join(text)

class Cond:
    def __init__(self, val):
        self.true = val
        self.has_else = False
        self.was_true = val
    def do_elif(self, val):
        if not self.was_true:
            self.true = val
            self.was_true = val
    def do_else(self):
        self.do_elif(True)
        self.has_else = True

def re_kw(kw): return f"^{kw}$"
def re_fn(fn): return f"^{fn}\\((.*)\\)$"
cmds = [
    (re.compile(r"^\((.*)\)$"), ''),
    (re.compile(r"^ENDIF$"), 'ENDIF'),
    (re.compile(r"^IF\((.*)\)$"), 'IF'),
    (re.compile(r"^NOT\((.*)\)$"), 'NOT'),
    (re.compile(r"^ELSE$"), 'ELSE'),
    (re.compile(r"^ELIF\((.*)\)$"), 'ELIF'),
    (re.compile(r"^TRUE$"), 'TRUE'),
    (re.compile(r"^FALSE$"), 'FALSE'),
]
re_feature = re.compile(r"^[a-z]+$")
re_cond = re.compile(r"^(\s|%)*\$\((.*)\)\s*")

def evaluate(features, cmd):
    match cmd[0]:
        case ("IF"|"ELIF"):
            return evaluate(features, cmd[1][0])
        case "VAR":
            return (cmd[1] in features)
        case "NOT":
            return not evaluate(features, cmd[1][0])
        case "TRUE":
            return True
        case "FALSE":
            return False
        case _:
            Err.report(
                kind="Unable to evaluate",
                msg=f"'{cmd[0]}' is not a known construct",
                fatal=True,
            )

def structure(group):
    for (c,n) in cmds:
        search = c.search(group)
        if search:
            return (n, [structure(g) for g in search.groups()])
    search = re_feature.search(group)
    if search:
        return ('VAR', search.group(0))
    Err.report(
        kind="Unknown construct in conditional compilation",
        msg=f"'{group}' does not match any known command",
    )
    return ('',[])

@lib.Trace.path('Trim conditional compilation')
def trim(text, features):
    features = set(f for f in features)
    transformed = []
    cond_stack = []
    include = True
    for line in text.split("\n"):
        Err.count_line(line)
        search = re_cond.search(line)
        if search:
            cmd = structure(search.group(2))
            match cmd[0]:
                case "IF":
                    res = evaluate(features, cmd)
                    cond_stack.append(Cond(res))
                case  "ELIF":
                    res = evaluate(features, cmd)
                    if len(cond_stack) > 0:
                        if cond_stack[-1].has_else:
                            Err.report(
                                kind="Duplicate else clause",
                                msg="corresponding $(IF(...)) already has an $(ELSE), this $(ELIF(...)) is unreachable",
                            )
                        cond_stack[-1].do_elif(res)
                    else:
                        Err.report(
                            kind="Not in a conditional block",
                            msg="$(ELIF(...)) provided without matching $(IF(...)) conditional",
                            fatal=True,
                        )

                case "ENDIF":
                    if len(cond_stack) > 0:
                        cond_stack.pop()
                    else:
                        Err.report(
                            kind="Not in a conditional block",
                            msg="$(ENDIF) provided without matching $(IF(...)) conditional",
                            fatal=True,
                        )
                case "ELSE":
                    if len(cond_stack) > 0:
                        if cond_stack[-1].has_else:
                            Err.report(
                                kind="Duplicate else clause",
                                msg="corresponding $(IF(...)) already has an $(ELSE), this $(ELSE) is unreachable",
                            )
                        cond_stack[-1].do_else()
                    else:
                        Err.report(
                            kind="Not in a conditional block",
                            msg="$(ELSE) provided without matching $(IF(...)) conditional",
                            fatal=True,
                        )
            include = all(c.true for c in cond_stack)
            print(cmd)
            print(f"depth:{cond_stack}, include:{include}")
        elif include:
            transformed.append(line)
    if len(cond_stack) > 0:
        Err.report(
            kind="Unterminated conditional",
            msg=f"file ended with {len(cond_stack)} $(IF(...)) still open, consider adding $(ENDIF) where appropriate",
        )
    return '\n'.join(transformed)



