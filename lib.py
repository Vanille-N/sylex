# SyLeX
#   Build descriptor for LaTeX

import os
import shutil
import jinja2 as j2

slx_dir = "/".join(d for d in __file__.split("/")[:-1] if d != ".")
templ_dir = f"{slx_dir}/templates"

local_slx_dir = ".sylex"
local_templ_dir = f"{local_slx_dir}/templates"
build_dir = "build"

py_files = ["error", "expand", "lib", "parse", "sylex"]
j2_mk_files = ["common", "pdf", "param", "deps"]
j2_files = ["Makefile", "texwatch"] + [f + ".tex.mk" for f in j2_mk_files]

date_modified = "2021-12-30"
now = __import__('datetime').datetime.now()
autogen_header = f"""\
# This file is autogenerated.
# It should not be edited manually, as it will be overwritten
# by `sylex init` without confirmation
#
# SyLeX
# Build tool for LaTeX
# Written by Vanille-N <vanille@crans.org> (Neven Villani)
#   https://github.com/Vanille-N/sylex
#   https://perso.crans.org/vanille
# Last updated {date_modified} and tested with Python 3.10
#
# File generated: {now}
"""

def is_filename(s):
    for c in s:
        if not (
            'a' <= c <= 'z' or
            'A' <= c <= 'Z' or
            c in "-_."
        ):
            return False
    return True

def j2_render(src, dest, tabs=True, params={}):
    with open(f"{templ_dir}/{src}.j2", 'r') as f:
        template = j2.Template(f.read())
    text = template.render(
        header=autogen_header,
        build=build_dir,
        **params,
    )
    if not tabs:
        text = text.replace(" "*4, "\t")
    with open(dest, 'w') as f:
        f.write(text)

def rm_r(path):
    if not os.path.exists(path):
        return
    if os.path.isfile(path) or os.path.islink(path):
        os.unlink(path)
    else:
        shutil.rmtree(path)

def copy_file(src, dest, file=None):
    src = os.path.abspath(src)
    dest = os.path.abspath(dest)
    if file is not None:
        src = f"{src}/{file}"
        dest = f"{dest}/{file}"
    shutil.copy(src, dest)

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
        p = self.dir + "/" + self.name + "." + (self.ext or "tex")
        return p.replace("./", "")

    def name_of_path(self):
        return self.path().replace("/", "__").replace("__", "/", 1)

    def __str__(self):
        return "File({})".format(self.path())

    def try_pdf(self):
        if (self.ext or "tex") == "tex":
            return self.with_ext("pdf")
        else:
            return self
