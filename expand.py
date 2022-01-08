from error import Err
import re
import log

re_here = r"\$\(HERE\)/"
re_root = r"\$\(ROOT\)/"
re_prev = r"\$\(PREV\)/"
re_slash = re.compile(r"\\(input|includegraphics|include)")

@log.path('Resolve file paths')
def filepaths(text, name):
    # Replace $(HERE) with the actual path
    file_root = name.replace("build/", "")
    split = file_root.split("__")
    #prev = []
    #while len(split) > 0:
    #    split.pop()
    #    prev.append("__".join(split))
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

def check_arglen(cmd, length, construct):
    parse_assert(len(cmd[1]) == length, f"Argument to {construct} should be of length {length}")


class Args:
    def __init__(self):
        self.list = []
    def __push__(self, arg):
        self.list.append(arg)

class Cmd:
    def __init__(self, fn, args):
        self.fn = fn
        self.args = args

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
            else:
                tokens.append(c)
        if running != '':
            tokens.append(running)
        return tokens
    tokens = tokenize(string)[::-1]
    def parse():
        if len(tokens) == 0:
            return ('', [])
        match tokens[-1]:
            case '(':
                name = ''
            case ')':
                return None
            case ',':
                return None
            case other:
                tokens.pop()
                name = other
        if len(tokens) == 0:
            return (name, [])
        if tokens[-1] == '(':
            tokens.pop()
            args = []
            while True:
                match tokens.pop():
                    case ')':
                        return (name, args)
                    case ',':
                        args.append(parse())
                    case other:
                        tokens.append(other)
                        args.append(parse())
        return (name, [])
    return parse()

class Features:
    def __init__(self, lst):
        self.all = set(lst)

    def evaluate(self, cmd):
        match cmd[0]:
            case ("IF"|"ELIF"):
                check_arglen(cmd, 1, "IF/ELIF")
                return self.evaluate(cmd[1][0])
            case "NOT":
                check_arglen(cmd, 1, "NOT")
                return not self.evaluate(cmd[1][0])
            case "TRUE":
                check_arglen(cmd, 0, "TRUE")
                return True
            case "FALSE":
                check_arglen(cmd, 0, "FALSE")
                return False
            case other:
                if other == other.lower():
                    check_arglen(cmd, 0, f"feature {other}")
                    return (other in self.all)
                else:
                    Err.report(
                        kind="Unable to evaluate",
                        msg=f"'{cmd[0]}' is not a known construct",
                    )

    def __str__(self):
        return ','.join(self.all)
    def __repr__(self):
        return self.__str__()


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
                match cmd[0]:
                    case "IF":
                        res = self.evaluate(cmd)
                        cond_stack.append(Cond(res))
                        log.Logger.indent_inc()
                        log.info(f"IF :: {cmd[1]} -> {cond_stack[-1]}")
                    case  "ELIF":
                        res = self.evaluate(cmd)
                        if len(cond_stack) > 0:
                            if cond_stack[-1].has_else:
                                Err.report(
                                    kind="Duplicate else clause",
                                    msg="corresponding $(IF(...)) already has an $(ELSE), this $(ELIF(...)) is unreachable",
                                )
                            cond_stack[-1].do_elif(res)
                            log.info(f"ELIF :: {cmd[1]} -> {cond_stack[-1]}")
                        else:
                            Err.report(
                                kind="Not in a conditional block",
                                msg="$(ELIF(...)) provided without matching $(IF(...)) conditional",
                            )

                    case "ENDIF":
                        check_arglen(cmd, 0, "ENDIF")
                        if len(cond_stack) > 0:
                            cond_stack.pop()
                            log.info(f"ENDIF")
                            log.Logger.indent_dec()
                        else:
                            Err.report(
                                kind="Not in a conditional block",
                                msg="$(ENDIF) provided without matching $(IF(...)) conditional",
                            )
                    case "ELSE":
                        check_arglen(cmd, 0, "ENDIF")
                        if len(cond_stack) > 0:
                            if cond_stack[-1].has_else:
                                Err.report(
                                    kind="Duplicate else clause",
                                    msg="corresponding $(IF(...)) already has an $(ELSE), this $(ELSE) is unreachable",
                                )
                            cond_stack[-1].do_else()
                            log.info(f"ELSE -> {cond_stack[-1]}")
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



@log.path('Expand {BLU}{i}{WHT}\nto {BLU}{o}{WHT}\nwith features {features}')
def expand(*, i, o, features):
    Err.in_file(i)
    with open(i, 'r') as f:
        text = f.read()
    if i.endswith('tex'):
        text = filepaths(text, o)
        text = features.trim(text)
    with open(o, 'w') as f:
        f.write(text)


