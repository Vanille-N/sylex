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

def print_texwatch():
    lib.j2_render(
        "texwatch",
        "texwatch",
    )
    os.chmod("texwatch", 0o755)

def print_common():
    os.makedirs(f"{lib.build_dir}", exist_ok=True)
    lib.j2_render(
        f"common.tex.mk",
        f"{lib.build_dir}/common.tex.mk",
        tabs=False,
    )

def print_init():
    if os.path.abspath(lib.local_slx_dir) == lib.slx_dir:
        print("Warning: sylex launched with `init` is attempting to override itself")
        print("Aborted")
        return
    lib.rm_r(f"{lib.local_slx_dir}")
    lib.rm_r(f"{lib.build_dir}") 
    # First clone source into .sylex
    os.makedirs(f"{lib.local_slx_dir}", exist_ok=True)
    for mod in lib.py_files:
        lib.copy_file(
            lib.slx_dir,
            lib.local_slx_dir,
            file=f"{mod}.py",
        )
    os.makedirs(f"{lib.local_templ_dir}", exist_ok=True)
    for templ in lib.j2_files:
        lib.copy_file(
            lib.templ_dir,
            lib.local_templ_dir,
            file=f"{templ}.j2",
        )
    # _If it doesn't exist_, clone .conf
    if not os.path.exists("sylex.conf"):
        lib.j2_render(
            "sylex.conf",
            "sylex.conf",
            tabs=False,
        )
    # Then the main Makefile
    lib.j2_render(
        "Makefile",
        "Makefile",
        tabs=False,
    )
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
