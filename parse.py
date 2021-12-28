# SyLeX
#   Build descriptor for LaTeX

import re
import sys
import os
import jinja2 as j2

from error import Err
import lib

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
            elif not lib.is_filename(d[1:]):
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
                file = lib.File("".join(self.path_stk) + file)
                if not file.with_prefix("src").exists():
                    Err.report(
                        kind="Nonexistent File",
                        msg="file {} was not found".format(file.path()),
                        fatal=False,
                    )
                return (file, tag, refs)

    def print(self, args):
        with open(f"{lib.templ_dir}/specific.tex.mk.j2", 'r') as f:
            template = j2.Template(f.read())
        text = template.render(
            name=args.name,
            txt=[f.with_prefix("build").name_of_path() for f in self.txt + [lib.File(args.name)]],
            fig=[f.with_prefix("build").try_pdf().name_of_path() for f in self.fig],
            bib=[f.with_prefix("build").name_of_path() for f in self.bib],
            hdr=[f.with_prefix("build").name_of_path() for f in self.hdr],
            hasbib=(len(self.bib) > 0),
            header=lib.autogen_header,
        )
        with open(args.dest, 'w') as f:
            f.write(text.replace("    ", '\t'))
            for sources in self.txt + [lib.File(args.name)] + self.fig + self.bib + self.hdr:
                f.write("{}: {}\n\tcp $< $@\n".format(
                    sources.with_prefix("build").name_of_path(),
                    sources.with_prefix("src").path(),
                ))
                f.write("\tpython3 .sylex/sylex.py expand file=$@\n")
            graph = Refs.into_graph(self.refs)
            for pre in graph:
                post = graph[pre]
                if type(pre) == lib.File:
                    f.write("{}: {}\n".format(
                        pre.with_prefix("build").name_of_path(),
                        " ".join(p.with_prefix("build").name_of_path() for ps in post for p in graph[ps]),
                    ))
            f.write("\n")

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

