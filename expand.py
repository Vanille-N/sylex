from error import Err
import re
import log

re_replace = re.compile(r"\$\(.*\)/")
re_here = re.compile(r"\$\(HERE\)/")
re_root = re.compile(r"\$\(ROOT\)/")
re_prev = re.compile(r"\$\(PREV([0-9]*)\)/")
re_slash = re.compile(r"\\(input|includegraphics|include)")

@log.path('Resolve file paths')
def filepaths(text, name):
    # Replace $(HERE) with the actual path
    file_root = name.replace("build/", "")
    split = file_root.split("__")
    path = []
    def get(lst, idx):
        if idx < len(lst):
            return lst[idx]
        else:
            return None
    while len(split) > 0:
        split.pop()
        path.append("__".join(split) + "__" if len(split) > 0 else "")
    here = get(path, 0) or ""
    prev = get(path, 1) or ""
    root = ""
    # Expand relative paths
    lines = text.split("\n")
    text = []
    for line in lines:
        if re_replace.search(line) is not None:
            line = re.sub(re_here, here, line)
            line = re.sub(re_root, root, line)
            while True:
                g = re_prev.search(line)
                print(line, g)
                if g is not None:
                    i = int(g.group(1) or 1)
                    print(f"0:'{g.group(0)}' 1:'{g.group(1)}' i:'{i}'")
                    print(line.find(g.group(0)))
                    line = line.replace(g.group(0), get(path, i) or "")
                    print(line)
                else:
                    break
        text.append(line)

    text = "\n".join(text)
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

    def __str__(self):
        return ":True:" if self.true else ":False:"
    def __repr__(self):
        return self.__str__()


re_feature = re.compile(r"^[a-z]+$")
re_cond = re.compile(r"^(\s|%)*\$\((.*)\)\s*")

def parse_assert(cond, msg):
    if not cond:
        Err.report(
            kind="Parsing error",
            msg=msg,
        )


class Args:
    def __init__(self):
        self.list = []
    def push(self, arg):
        self.list.append(arg)

    def check_len(self, length, construct):
        parse_assert(
            len(self.list) == length,
            f"Argument to {construct} should be of length {length}",
        )
    def __str__(self):
        return ",".join(a.__str__() for a in self.list)

    def nonempty(self):
        return len(self.list) > 0


class Cmd:
    def __init__(self, fn, args=None):
        self.fn = fn
        self.args = args or Args()

    def validate(self):
        arity = {
            'IF': 1,
            'ELIF': 1,
            'NOT': 1,
            'TRUE': 0,
            'FALSE': 0,
            'ENDIF': 0,
            'ELSE': 0,
        }.get(self.fn) or 0
        self.args.check_len(arity, self.fn)

    def evaluate(self, features):
        self.validate()
        match self.fn:
            case ("IF"|"ELIF"):
                return self.args.list[0].evaluate(features)
            case "NOT":
                return not self.args.list[0].evaluate(features)
            case "TRUE":
                return True
            case "FALSE":
                return False
            case other:
                if other == other.lower():
                    return features.query(other)
                else:
                    Err.report(
                        kind="Unable to evaluate",
                        msg=f"'{cmd.fn}' is not a known construct",
                    )

    def push(self, arg):
        if arg is not None:
            self.args.push(arg)

    def __str__(self):
        return f"{self.fn}" + (f"({self.args})" if self.args.nonempty() else "")


def structure(string):
    fnames = {}
    def tokenize(string):
        tokens = []
        running = ''
        for c in string:
            if 'A' <= c.upper() <= 'Z':
                running += c
            elif running != '':
                tokens.append(running)
                tokens.append(c)
                running = ''
            elif c == ' ':
                pass
            else:
                tokens.append(c)
        if running != '':
            tokens.append(running)
        return tokens
    tokens = tokenize(string)[::-1]
    def parse():
        if len(tokens) == 0:
            return None
        match tokens[-1]:
            case '(':
                cmd = Cmd('')
            case ')':
                return None
            case ',':
                return None
            case other:
                tokens.pop()
                cmd = Cmd(other)
        if len(tokens) == 0:
            return cmd
        if tokens[-1] == '(':
            tokens.pop()
            while True:
                match tokens.pop():
                    case ')':
                        return cmd
                    case ',':
                        cmd.push(parse())
                    case other:
                        tokens.append(other)
                        cmd.push(parse())
        return cmd
    return parse()


class Features:
    def __init__(self, lst):
        self.all = set(lst)
 
    def __str__(self):
        return ','.join(self.all)
    def __repr__(self):
        return self.__str__()

    def query(self, f):
        return (f in self.all)

    @log.path('Trim conditional compilation')
    def trim(self, text):
        transformed = []
        cond_stack = []
        include = True
        for line in text.split("\n"):
            Err.count_line(line)
            search = re_cond.search(line)
            if search:
                cmd = structure(search.group(2))
                match cmd.fn:
                    case "IF":
                        res = cmd.evaluate(self)
                        cond_stack.append(Cond(res))
                        log.Logger.indent_inc()
                        log.info("{0} -> {YLW}{1}{WHT}", cmd, cond_stack[-1])
                    case  "ELIF":
                        res = cmd.evaluate(self)
                        if len(cond_stack) > 0:
                            if cond_stack[-1].has_else:
                                Err.report(
                                    kind="Duplicate else clause",
                                    msg="corresponding $(IF(...)) already has an $(ELSE), this $(ELIF(...)) is unreachable",
                                )
                            cond_stack[-1].do_elif(res)
                            log.info("{0} -> {YLW}{1}{WHT}", cmd, cond_stack[-1])
                        else:
                            Err.report(
                                kind="Not in a conditional block",
                                msg="$(ELIF(...)) provided without matching $(IF(...)) conditional",
                            )

                    case "ENDIF":
                        if len(cond_stack) > 0:
                            cond_stack.pop()
                            log.info("{0}", cmd)
                            log.Logger.indent_dec()
                        else:
                            Err.report(
                                kind="Not in a conditional block",
                                msg="$(ENDIF) provided without matching $(IF(...)) conditional",
                            )
                    case "ELSE":
                        if len(cond_stack) > 0:
                            if cond_stack[-1].has_else:
                                Err.report(
                                    kind="Duplicate else clause",
                                    msg="corresponding $(IF(...)) already has an $(ELSE), this $(ELSE) is unreachable",
                                )
                            cond_stack[-1].do_else()
                            log.info("{0} -> {YLW}{1}{WHT}", cmd, cond_stack[-1])
                        else:
                            Err.report(
                                kind="Not in a conditional block",
                                msg="$(ELSE) provided without matching $(IF(...)) conditional",
                            )
                    case other:
                        Err.report(
                            kind="Parsing error of conditional marker",
                            msg=f"'{other}' is not a keyword",
                        )
                include = all(c.true for c in cond_stack)
                #print(cmd)
                #print(f"depth:{cond_stack}, include:{include}")
            elif include:
                transformed.append(line)
        if len(cond_stack) > 0:
            Err.report(
                kind="Unterminated conditional",
                msg=f"file ended with {len(cond_stack)} $(IF(...)) still open, consider adding $(ENDIF) where appropriate",
            )
        return '\n'.join(transformed)



@log.path('Expand {BLU}{i}{WHT}\nto {BLU}{o}{WHT}\nwith features {PPL}{features}{WHT}')
def expand(*, i, o, features):
    Err.in_file(i)
    with open(i, 'r') as f:
        text = f.read()
    if i.endswith('tex'):
        text = filepaths(text, o)
        text = features.trim(text)
    with open(o, 'w') as f:
        f.write(text)


