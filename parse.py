# SyLeX
#   Build descriptor for LaTeX

import re
import sys
import os

from error import Err
import lib
import log

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
    def __repr__(self):
        return self.__str__()


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
            match tag:
                case 'fig':
                    self.fig.append(file)
                case 'bib':
                    self.bib.append(file)
                case 'hdr':
                    self.hdr.append(file)
                case 'txt':
                    self.txt.append(file)
                case _:
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
                    msg="using .. is discouraged, make do with $(PREV) instead",
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
                file = lib.File("".join(self.path_stk) + file).try_ext("tex")
                if not file.with_prefix("src").exists():
                    Err.report(
                        kind="Nonexistent File",
                        msg="file {} was not found".format(file.path()),
                        fatal=False,
                    )
                return (file, tag, refs)


    @log.path('Write configuration for {RED}{1.name}{WHT}')
    def print(self, proj):
        into_build = lambda f: f.with_prefix(f"{lib.build_dir}").name_of_path()
        into_pdf_build = lambda f: f.with_prefix(f"{lib.build_dir}").try_pdf().name_of_path()

        @log.call
        @log.path()
        def print_pdf():
            # PDF
            lib.j2_render(
                "pdf.tex.mk",
                proj.dest_build,
                tabs=False,
                params={
                    'name': proj.name,
                    'figs': [{
                        'real_name': fig.with_prefix("build").try_pdf().name_of_path(),
                        'build_name': fig.without_ext().path(),
                        'base_name': fig.try_pdf().filename(),
                    } for fig in self.fig],
                },
            )

        @log.call
        @log.path()
        def print_parameters():
            # Parameters
            lib.j2_render(
                "param.tex.mk",
                proj.dest_param,
                tabs=False,
                params={
                    'name': proj.name,
                    'groups': [{
                        'label': 'TEX_SRC',
                        'files': self.txt,
                        'map': into_build,
                    },{
                        'label': 'TEX_FIG',
                        'files': self.fig,
                        'map': into_pdf_build,
                    },{
                        'label': 'BIBLIO',
                        'files': self.bib,
                        'map': into_build,
                    },{
                        'label': 'HEADERS',
                        'files': self.hdr,
                        'map': into_build,
                    }],
                    'hasbib': (len(self.bib) > 0),
                },
            )

        @log.call
        @log.path()
        def print_dependencies():
            # Dependencies
            for f in self.txt + self.bib + self.fig:
                if len(self.refs[f].depend) > 0:
                    Err.report(
                        kind="Dependency to non-header",
                        msg=f"'{f}' is not a header, having a dependency to it could be a mistake",
                        fatal=False,
                    )
            for f in self.hdr:
                if len(self.refs[f].induce) > 0:
                    Err.report(
                        kind="Dependency of header",
                        msg=f"'{f}' is a header, yet it has dependencies",
                        fatal=False,
                    )
            graph = Refs.into_graph(self.refs)
            lib.j2_render(
                "deps.tex.mk",
                proj.dest_deps,
                tabs=False,
                params={
                    'name': proj.name,
                    'copy': [(
                        sources.with_prefix("src").path(),
                        sources.with_prefix(f"{lib.build_dir}").name_of_path(),
                    ) for sources in self.txt + self.fig + self.bib + self.hdr],
                    'extra': [
                        (
                            pre.with_prefix(f"{lib.build_dir}").name_of_path(),
                            " ".join(
                                p.with_prefix(f"{lib.build_dir}").name_of_path() for ps in graph[pre] for p in graph[ps]
                            )
                        ) for pre in graph if type(pre) == lib.File
                    ],
                },
            )
            #with open(proj.dest_deps + ".bak", 'w') as f:
            #    for sources in self.txt + self.fig + self.bib + self.hdr:
            #        f.write("{}: {}\n\tcp $< $@\n".format(
            #            sources.with_prefix(f"{lib.build_dir}").name_of_path(),
            #            sources.with_prefix("src").path(),
            #        ))
            #        f.write("\t$(BUILDER) expand --file $@\n")
            #    for pre in graph:
            #        post = graph[pre]
            #        if type(pre) == lib.File:
            #            f.write("{}: {}\n".format(
            #                pre.with_prefix(f"{lib.build_dir}").name_of_path(),
            #                " ".join(p.with_prefix(f"{lib.build_dir}").name_of_path() for ps in post for p in graph[ps]),
            #            ))
            #    f.write("\n")


# Read file f (in the texmk format) and return a workable descriptor
@log.path('Read configuration for {RED}{0.name}{WHT}\nfrom {BLU}{0.src}{WHT}')
def parse_cfg(proj, fail):
    with open(proj.src, 'r') as f:
        Err.in_file(proj.src)
        cfg = Cfg()
        for line in f.readlines():
            cfg.push(line.rstrip())
            if Err.fatality >= Err.WARNING:
                return None
        if fail <= Err.fatality:
            return None
        else:
            root = lib.File(proj.name).with_ext("tex")
            cfg.txt.append(root)
            cfg.refs[root] = Refs()
            return cfg

