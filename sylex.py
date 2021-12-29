#! /bin/env python3

# SyLeX
#   Build descriptor for LaTeX

import re
import sys
import os
import jinja2 as j2
from argparse import ArgumentParser

from error import Err
import lib
import parse
from expand import expand

def print_common():
    with open(f"{lib.templ_dir}/common.tex.mk.j2", 'r') as f:
        template = j2.Template(f.read())
    text = template.render(header=lib.autogen_header)
    os.makedirs('build', exist_ok=True)
    with open("build/common-tex.mk", 'w') as f:
        f.write(text.replace("    ", "\t"))

def print_texwatch():
    with open(f"{lib.templ_dir}/texwatch.j2", 'r') as f:
        template = j2.Template(f.read())
    text = template.render(header=lib.autogen_header)
    with open("texwatch", 'w') as f:
        f.write(text)
    os.chmod("texwatch", 0o755)

def print_init():
    with open(f"{lib.templ_dir}/Makefile.j2", 'r') as f:
        template = j2.Template(f.read())
    text = template.render(header=lib.autogen_header)
    with open("Makefile", 'w') as f:
        f.write(text.replace("    ", "\t"))
    # _If it doesn't exist_, clone .conf
    if not os.path.exists("sylex.conf"):
        with open(f"{lib.templ_dir}/sylex.conf.j2", 'r') as f:
            template = j2.Template(f.read())
        text = template.render(header=lib.autogen_header)
        with open(f"sylex.conf", 'w') as f:
            f.write(text.replace("    ", "\t"))
    # Also clone source into .sylex
    os.makedirs(".sylex", exist_ok=True)
    for mod in ["lib", "error", "parse", "sylex", "expand"]:
        with open(f"{lib.slx_dir}/{mod}.py", 'r') as f:
            text = f.read()
        with open(f".sylex/{mod}.py", 'w') as f:
            f.write(text)
    os.makedirs(".sylex/templates", exist_ok=True)
    for templ in ["common.tex.mk", "Makefile", "specific.tex.mk", "texwatch"]:
        with open(f"{lib.templ_dir}/{templ}.j2", 'r') as f:
            text = f.read()
        with open(f".sylex/templates/{templ}.j2", 'w') as f:
            f.write(text)

class ProjFile:
    def __init__(self, s):
        self.name = s
        self.src = f"cfg_{s}.slx"
        self.dest = f"build/doc_{s}.tex.mk"
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
