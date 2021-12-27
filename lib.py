# SyLeX
#   Build descriptor for LaTeX

import re
import sys
import os

slx_dir = "/".join(d for d in __file__.split("/")[:-1] if d != ".")
templ_dir = f"{slx_dir}/templates"

autogen_header = """\
# This file is autogenerated.
# It should not be edited manually, as it will be overwritten
# by `sylex init` without confirmation
#
# SyLeX
# Build tool for LaTeX
# Written by Vanille-N <vanille@crans.org> (Neven Villani)
#   https://github.com/Vanille-N/sylex
#   https://perso.crans.org/vanille
# Last updated 2021-12-27 and tested with Python 3.10
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
