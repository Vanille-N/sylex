#! /bin/env python3

# SyLeX
#   Build descriptor for LaTeX

import re
import sys
import os
import jinja2 as j2
from argparse import ArgumentParser
import shutil

from error import Err
import lib
import parse
from expand import expand

def j2_render(src, dest, tabs=True, **kwargs):
    with open(f"{src}.j2", 'r') as f:
        template = j2.Template(f.read())
    text = template.render(
        header=lib.autogen_header,
        build=lib.build_dir,
        **kwargs,
    )
    if not tabs:
        text = text.replace(" "*4, "\t")
    with open(dest, 'w') as f:
        f.write(text)

def print_common():
    os.makedirs(f"{lib.build_dir}", exist_ok=True)
    j2_render(
        f"{lib.templ_dir}/common.tex.mk",
        f"{lib.build_dir}/common-tex.mk",
        tabs=False,
    )
    #with open(f"{lib.templ_dir}/common.tex.mk.j2", 'r') as f:
    #    template = j2.Template(f.read())
    #text = template.render(header=lib.autogen_header)
    #with open("build/common-tex.mk", 'w') as f:
    #    f.write(text.replace("    ", "\t"))

def print_texwatch():
    with open(f"{lib.templ_dir}/texwatch.j2", 'r') as f:
        template = j2.Template(f.read())
    text = template.render(header=lib.autogen_header, build=lib.build_dir)
    with open("texwatch", 'w') as f:
        f.write(text)
    os.chmod("texwatch", 0o755)

def rm_r(path):
    if not os.path.exists(path):
        return
    if os.path.isfile(path) or os.path.islink(path):
        os.unlink(path)
    else:
        shutil.rmtree(path)

def print_init():
    rm_r(f"{lib.local_slx_dir}")
    rm_r(f"{lib.build_dir}")
    with open(f"{lib.templ_dir}/Makefile.j2", 'r') as f:
        template = j2.Template(f.read())
    text = template.render(header=lib.autogen_header, build=lib.build_dir)
    with open("Makefile", 'w') as f:
        f.write(text.replace("    ", "\t"))
    # _If it doesn't exist_, clone .conf
    if not os.path.exists("sylex.conf"):
        with open(f"{lib.templ_dir}/sylex.conf.j2", 'r') as f:
            template = j2.Template(f.read())
        text = template.render(header=lib.autogen_header, build=lib.build_dir)
        with open(f"sylex.conf", 'w') as f:
            f.write(text.replace("    ", "\t"))
    # Also clone source into .sylex
    os.makedirs(f"{lib.local_slx_dir}", exist_ok=True)
    for mod in lib.py_files: #["lib", "error", "parse", "sylex", "expand"]:
        with open(f"{lib.slx_dir}/{mod}.py", 'r') as f:
            text = f.read()
        with open(f"{lib.local_slx_dir}/{mod}.py", 'w') as f:
            f.write(text)
    os.makedirs(f"{lib.local_templ_dir}", exist_ok=True)
    for templ in lib.j2_files: #["common.tex.mk", "Makefile", "build.tex.mk", "param.tex.mk", "deps.tex.mk", "texwatch"]:
        with open(f"{lib.templ_dir}/{templ}.j2", 'r') as f:
            text = f.read()
        with open(f"{lib.local_templ_dir}/{templ}.j2", 'w') as f:
            f.write(text)

class ProjFile:
    def __init__(self, s):
        self.name = s
        self.src = f"cfg_{s}.slx"
        self.dest_build = f"build/build_{s}.tex.mk"
        self.dest_param = f"build/param_{s}.tex.mk"
        self.dest_deps = f"build/deps_{s}.tex.mk"
        if not os.path.exists(self.src):
            return TypeError(f"Configuration file '{self.src}' does not exist")

def warnlevel(s):
    value = s.upper()
    if value in ["0", "N", "NEVER"]:
        return Err.NEVER
    elif value in ["1", "E", "ERROR"]:
        return Err.ERROR
    elif value in ["2", "W", "WARNING"]:
        return Err.WARNING
    elif value in ["3", "A", "ALWAYS"]:
        return Err.ALWAYS
    else:
        return TypeError(f"'{s}' is not a valid warning level. Use 0-3 or NEVER/ERROR/WARNING/ALWAYS")

class Args:
    def __init__(self, args):
        parser = ArgumentParser(
            usage="""\
sylex <command> [<args>]

with commands:
  make           write auxiliary files from templates
  build          build makefiles for specific project
  init           sync source code and templates
  expand         replace relative filenames
  help           print help message
"""
        )
        parser.add_argument('command', help='available commands')
        res = parser.parse_args(args[:1])
        getattr(self, res.command)(args[1:])

    def make(self, args):
        parser = ArgumentParser(description='write auxiliairy files from templates')
        parser.add_argument('--common', action='store_true', help='generic TeX-related targets')
        parser.add_argument('--watcher', action='store_true', help='recompile after each write')
        res = parser.parse_args(args)
        if res.common:
            print_common()
        if res.watcher:
            print_texwatch()

    def build(self, args):
        parser = ArgumentParser(description='build makefiles for specific project')
        parser.add_argument('--proj', type=ProjFile, help='which project to build')
        parser.add_argument('--level', type=warnlevel, help='error failure threshold')
        res = parser.parse_args(args)
        cfg = parse.parse_cfg(res.proj, res.level)
        os.makedirs('build', exist_ok=True)
        if cfg is not None:
            cfg.print(res.proj)
        elif res.level <= Err.fatality:
            if res.level == Err.NEVER:
                sys.exit(0)
            sys.exit(2)

    def init(self, args):
        parser = ArgumentParser(description='synchronize source code and templates')
        res = parser.parse_args(args)
        print_init()

    def expand(self, args):
        parser = ArgumentParser(description='replace relative filenames')
        parser.add_argument('--file', help='file to expand')
        res = parser.parse_args(args)
        expand(res.file)

    def help(self, args):
        pass

if __name__ == "__main__":
    Args(sys.argv[1:])
