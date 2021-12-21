#! /bin/env python3

# SyLeX
#   Build descriptor for LaTeX

import re
import sys
import os
import jinja2 as j2

home = "/home/vanille"
slx_dir = f"{home}/bin/sylex"
templ_dir = f"{slx_dir}/templates"

# TODO:
# - warning when init if Makefile already exists
# - Jinja2 templating

# Error reporting with uniform formatting and colored output
class Err:
    fname = ""
    line = 0

    ALWAYS = 0
    WARNING = 1
    ERROR = 2
    NEVER = 3
    fatality = ALWAYS

    def in_file(fname):
        Err.fname = fname
        Err.line = 0

    def count_line(text):
        Err.line += 1
        Err.text = text

    def report(*,
        kind,
        msg,
        fatal=True,
    ):
        Err.fatality = max(Err.fatality, Err.ERROR if fatal else Err.WARNING)
        print("fatality: {}".format(Err.fatality))
        print("In \x1b[36m{}:{}\x1b[0m, '{}'".format(Err.fname, Err.line, Err.text))
        print("{}: {}\x1b[0m".format(
            "\x1b[1;31mError" if fatal else "\x1b[1;33mWarning", kind
        ))
        print("    {}".format(msg))
        print()

def is_filename(s):
    for c in s:
        if not (
            'a' <= c <= 'z' or
            'A' <= c <= 'Z' or
            c in "-_."
        ):
            return False
    return True

class File:
    def __init__(self, path):
        spath = path.rsplit("/", 1)
        dir = spath[0] if len(spath) > 1 else ""
        name = spath[-1]
        sname = name.rsplit(".", 1)
        name = sname[0]
        ext = sname[1] if len(sname) > 1 else None
        self.dir = dir
        self.name = name
        self.ext = ext

    def with_prefix(self, pre):
        f = File("")
        f.dir = pre + ("/" if self.dir != "" else "") + self.dir
        f.name = self.name
        f.ext = self.ext
        return f

    def with_ext(self, ext):
        f = File("")
        f.dir = self.dir
        f.name = self.name
        f.ext = ext
        return f

    def exists(self):
        return os.path.isfile(self.path())

    def path(self):
        return self.dir + "/" + self.name + "." + (self.ext or "tex")

    def __str__(self):
        return "File({})".format(self.path())

    def try_pdf(self):
        if (self.ext or "tex") == "tex":
            return self.with_ext("pdf")
        else:
            return self

class Refs:
    def __init__(self, decl=[]):
        self.induce = set()
        self.depend = set()
        for d in decl:
            if d == "":
                continue
            elif len(d) == 1:
                Err.report(
                    kind="Empty Reference",
                    msg="< or > must be followed by a name",
                    fatal=False,
                )
            elif not is_filename(d[1:]):
                Err.report(
                    kind="Invalid Reference",
                    msg="'{}' contains characters outside of azAZ_-.".format(d[1:]),
                    fatal=False,
                )
            elif d[0] == ">":
                self.induce.add(d[1:])
            elif d[0] == "<":
                self.depend.add(d[1:])
            else:
                Err.report(
                    kind="Not a Reference",
                    msg="references must start with > or <",
                    fatal=False,
                )

    def union(self, other):
        u = Refs()
        u.induce = self.induce.union(other.induce)
        u.depend = self.depend.union(other.depend)
        return u

    def __str__(self):
        return "<({}) >({})".format(",".join(self.depend), ",".join(self.induce))

    def into_graph(refs):
        graph = {}
        for file in refs:
            rs = refs[file]
            if len(rs.induce) > 0:
                graph[file] = rs.induce
            for d in rs.depend:
                if d not in graph:
                    graph[d] = []
                graph[d].append(file)
        return graph



class Cfg:
    def __init__(self):
        self.txt = []
        self.fig = []
        self.bib = []
        self.hdr = []
        self.tag_stk = ['txt']
        self.path_stk = []
        self.ref_stk = [Refs()]
        self.refs = {}

    def trim_comment(line):
        i = line.find("#")
        if i == -1:
            return line
        else:
            return line[:i]

    def push(self, line):
        line = Cfg.trim_comment(line)
        Err.count_line(line)
        item = self.read_path(line)
        if item is not None:
            (file, tag, refs) = item
            self.refs[file] = refs
            if tag == 'fig':
                self.fig.append(file)
            elif tag == 'bib':
                self.bib.append(file)
            elif tag == 'hdr':
                self.hdr.append(file)
            elif tag == 'txt':
                self.txt.append(file)
            else:
                Err.report(
                    kind="Unknown Tag",
                    msg="'{}' should be in fig,bib,hdr,txt".format(tag),
                    fatal=False,
                )

    def read_path(self, line):
        # compute indentation depth
        depth = 0
        while line != "" and line[0] == ' ':
            depth += 1
            line = line[1:]
        while line != "" and line[-1] == ' ':
            line = line[:-1]
        if line == '':
            return None
        if depth % 4 != 0:
            Err.report(
                kind="Invalid Indentation",
                msg="current indentation {} is not a multiple of 4 spaces".format(depth),
            )
            return None
        else:
            depth = depth // 4
            file, *refs = line.split(" ")
            refs = Refs(refs)
            s = file.split(':')
            if len(s) == 1:
                tag = None
            else:
                if len(s) > 2:
                    Err.report(
                        kind="Too Many Tags",
                        msg="':' separates tag, first one overriden",
                    )
                tag = s[-2]
                file = s[-1]
            if depth > len(self.path_stk):
                Err.report(
                    kind="Too Much Indentation",
                    msg="indentation is a lot more than previous level",
                    fatal=False,
                )
            while depth > len(self.path_stk):
                self.path_stk.append("")
                self.tag_stk.append(self.tag_stk[-1])
                self.ref_stk.append(self.ref_stk[-1])
            while len(self.path_stk) > depth:
                self.path_stk.pop()
                self.tag_stk.pop()
                self.ref_stk.pop()
                assert len(self.ref_stk) == len(self.tag_stk)
            if tag is None:
                tag = self.tag_stk[-1]
            refs = refs.union(self.ref_stk[-1])
            if "/../" in file or file.startswith("../") or file.endswith("/..") or file == "..":
                Err.report(
                    kind="Directory Climbing",
                    msg="using .. is discouraged",
                )
                return None
            if file == "":
                Err.report(
                    kind="Empty Filename",
                    msg="use of ./ is preferred to artificially introduce a hierarchy",
                    fatal=False,
                )
                self.path_stk.append(file)
                self.tag_stk.append(tag)
                self.ref_stk.append(refs)
                assert len(self.ref_stk) == len(self.tag_stk)
                return None
            elif file[-1] == '/':
                self.path_stk.append(file)
                self.tag_stk.append(tag)
                self.ref_stk.append(refs)
                assert len(self.ref_stk) == len(self.tag_stk)
                return None
            else:
                file = File("".join(self.path_stk) + file)
                if not file.with_prefix("src").exists():
                    Err.report(
                        kind="Nonexistent File",
                        msg="file {} was not found".format(file.path()),
                        fatal=False,
                    )
                return (file, tag, refs)

    def print(self, args):
        with open(f"{templ_dir}/specific.tex.mk.j2", 'r') as f:
            template = j2.Template(f.read())
        text = template.render(
            name=args.name,
            txt=[f.with_prefix("build").path() for f in self.txt + [File(args.name)]],
            fig=[f.with_prefix("build").try_pdf().path() for f in self.fig],
            bib=[f.with_prefix("build").path() for f in self.bib],
            hdr=[f.with_prefix("build").path() for f in self.hdr],
            hasbib=(len(self.bib) > 0),
        )
        with open(args.dest, 'w') as f:
            f.write(text.replace("    ", '\t'))
            graph = Refs.into_graph(self.refs)
            for pre in graph:
                post = graph[pre]
                if type(pre) == File:
                    f.write("{}: {}\n".format(
                        pre.with_prefix("build").path(),
                        " ".join(p.with_prefix("build").path() for ps in post for p in graph[ps]),
                    ))
            f.write("\n")

def print_common():
    with open(f"{templ_dir}/common.tex.mk.j2", 'r') as f:
        template = j2.Template(f.read())
    text = template.render()
    os.makedirs('build', exist_ok=True)
    with open("build/common-tex.mk", 'w') as f:
        f.write(text.replace("    ", "\t"))

def print_texwatch():
    with open(f"{templ_dir}/texwatch.j2", 'r') as f:
        template = j2.Template(f.read())
    text = template.render()
    with open("texwatch", 'w') as f:
        f.write(text)
    os.chmod("texwatch", 0o755)

def print_init():
    with open("{templ_dir}/Makefile.j2", 'r') as f:
        template = j2.Template(f.read())
    text = template.render()
    with open("Makefile", 'w') as f:
        f.write(text.replace("    ", "\t"))


class Args:
    def __init__(self, args):
        self.fail = None
        self.name = None
        Err.in_file("<cmdline>")
        self.action = None
        for a in args:
            Err.count_line(a)
            if "=" in a:
                (key, value) = a.split("=", 1)
                if key == "fail":
                    value = value.upper()
                    if value in ["0", "N", "NEVER"]:
                        self.fail = Err.NEVER
                    elif value in ["1", "E", "ERROR"]:
                        self.fail = Err.ERROR
                    elif value in ["2", "W", "WARNING"]:
                        self.fail = Err.WARNING
                    elif value in ["3", "A", "ALWAYS"]:
                        self.fail = Err.ALWAYS
                    else:
                        Err.report(
                            kind="Argparse: Unknown Fail Level",
                            msg="fail level is among NEVER,ERROR,WARNING,ALWAYS",
                        )
                elif key == "name":
                    self.name = value
                    if self.action is not None:
                        Err.report(
                            kind="Argparse: Multiple Actions",
                            msg="can only perform one action at a time",
                        )
                    self.action = "parse"
                else:
                    Err.report(
                        kind="Argparse: No Keyword",
                        msg="in key=value '{}={}', key is not assigned".format(key, value),
                    )
            else:
                if a == "help":
                    print("Help unavailable at the moment")
                    sys.exit(255)
                elif a == "common" or a == "init" or a == "watcher":
                    if self.action is not None:
                        Err.report(
                            kind="Argparse: Multiple Actions",
                            msg="can only perform one action at a time",
                        )
                    self.action = a
                else:
                    Err.report(
                        kind="Argparse: Unknown Flag",
                        msg="'{}' is not recognized".format(a),
                    )
        if Err.fatality >= Err.WARNING:
            if Err.fatality == Err.NEVER:
                sys.exit(0)
            sys.exit(1)
        if self.fail is None:
            self.fail = Err.ERROR
        if self.name is not None:
            self.src = f"cfg_{self.name}.slx"
            self.dest = f"build/doc_{self.name}.tex.mk"

# Read file f (in the texmk format) and return a workable descriptor
def parse_cfg(args):
    with open(args.src, 'r') as f:
        Err.in_file(args.src)
        cfg = Cfg()
        for line in f.readlines():
            cfg.push(line.rstrip())
            if Err.fatality >= Err.WARNING:
                return None
        if args.fail <= Err.fatality:
            return None
        else:
            return cfg

def main(args):
    args = Args(args[1:])
    if args.action == "common":
        print_common()
        return
    elif args.action == "watcher":
        print_texwatch()
        return
    elif args.action == "init":
        print_init()
        return
    if os.path.isfile(args.dest):
        os.remove(args.dest)
    elif os.path.isdir(args.dest):
        Err.report(
            kind="Argparse: Destination is a Directory",
            msg="not going to remove '{}', it's probably a mistake".format(args.dest),
        )
        if args.fail == Err.NEVER:
            sys.exit(0)
        sys.exit(1)
    if not os.path.isfile(args.src):
        Err.report(
            kind="Argparse: Source not Found",
            msg="'{}' cannot be read: it may be a directory or missing".format(args.src),
        )
        if args.fail == Err.NEVER:
            sys.exit(0)
        sys.exit(1)
    cfg = parse_cfg(args)
    if cfg is not None:
        cfg.print(args)
    elif args.fail <= Err.fatality:
        if args.fail == Err.NEVER:
            sys.exit(0)
        sys.exit(2)

if __name__ == "__main__":
    main(sys.argv)
