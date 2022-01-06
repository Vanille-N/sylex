#! /bin/env python3

# SyLeX
#   Build descriptor for LaTeX

import sys
import os
import jinja2 as j2
import shutil
from argparse import ArgumentParser

from error import Err
import lib
import expand
import parse


@lib.Trace.path('Create directory {BLU}{0}{WHT}')
def mkdir(path):
    os.makedirs(path, exist_ok=True)


@lib.Trace.path('Write watcher')
def print_texwatch():
    lib.j2_render(
        "texwatch",
        f"{lib.build_dir}/texwatch",
    )
    os.chmod(f"{lib.build_dir}/texwatch", 0o755)


@lib.Trace.path('Write common make definitions')
def print_common():
    mkdir(f"{lib.build_dir}")
    lib.j2_render(
        f"common.tex.mk",
        f"{lib.build_dir}/common.tex.mk",
        tabs=False,
    )


@lib.Trace.path('Clone project locally')
def print_init():
    if os.path.abspath(lib.local_slx_dir) == lib.slx_dir:
        print("Warning: sylex launched with `init` is attempting to override itself")
        print("Aborted")
        return

    @lib.Trace.path()
    def cleanup():
        lib.rm_r(f"{lib.build_dir}") 
    cleanup()

    # First clone source into .sylex
    @lib.Trace.path()
    def clone_source():
        lib.rm_r(f"{lib.local_slx_dir}")
        mkdir(f"{lib.local_slx_dir}")
        for mod in lib.py_files:
            lib.copy_file(
                lib.slx_dir,
                lib.local_slx_dir,
                file=f"{mod}.py",
            )
    clone_source()

    @lib.Trace.path()
    def clone_templates():
        mkdir(f"{lib.local_templ_dir}")
        for templ in lib.j2_files:
            lib.copy_file(
                lib.templ_dir,
                lib.local_templ_dir,
                file=f"{templ}.j2",
            )
    clone_templates()

    @lib.Trace.path()
    def clone_configuration():
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
    clone_configuration()


class ProjFile:
    def __init__(self, s):
        self.name = s
        self.src = f"cfg_{s}.slx"
        self.dest_build = f"{lib.build_dir}/pdf_{s}.tex.mk"
        self.dest_param = f"{lib.build_dir}/param_{s}.tex.mk"
        self.dest_deps = f"{lib.build_dir}/deps_{s}.tex.mk"
        if not os.path.exists(self.src):
            return TypeError(f"Configuration file '{self.src}' does not exist")


def warnlevel(s):
    value = s.upper()
    match value:
        case ("0"|"N"|"NEVER"):
            return Err.NEVER
        case ("1"|"E"|"ERROR"):
            return Err.ERROR
        case ("2"|"W"|"WARNING"):
            return Err.WARNING
        case ("3"|"A"|"ALWAYS"):
            return Err.ALWAYS
        case _:
            return TypeError(f"'{s}' is not a valid warning level. Use 0-3 or NEVER/ERROR/WARNING/ALWAYS")


class Args:
    def __init__(self, args):
        parser = ArgumentParser(
            usage="""\
sylex <command> [<args>]

with commands:
  build-aux      write auxiliary files from templates
  build-conf     instanciate makefiles for specific project
  init           sync source code and templates
  expand         resolve relative filenames and conditional inclusions
  help           print help message
"""
        )
        parser.add_argument('command', help='available commands')
        res = parser.parse_args(args[:1])
        args = args[1:]
        match res.command:
            case 'build-aux': self.build_aux(args)
            case 'build-conf': self.build_conf(args)
            case 'init': self.init(args)
            case 'expand': self.expand(args)
            case 'help': self.help(args)
            case other:
                print(f"Unknown command: '{other}' is not an available subcommand")
                sys.exit(1)


    def build_aux(self, args):
        parser = ArgumentParser(description='write auxiliairy files from templates')
        parser.add_argument('--common', action='store_true', help='generic TeX-related targets')
        parser.add_argument('--watcher', action='store_true', help='recompile after each write')
        res = parser.parse_args(args)
        if res.common:
            print_common()
        if res.watcher:
            print_texwatch()


    def build_conf(self, args):
        parser = ArgumentParser(description='instanciate makefiles for specific project')
        parser.add_argument('--proj', type=ProjFile, help='which project to build')
        parser.add_argument('--level', type=warnlevel, help='error failure threshold')
        res = parser.parse_args(args)
        cfg = parse.parse_cfg(res.proj, res.level)
        mkdir(f"{lib.build_dir}")
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
        parser.add_argument('--i', help='input file')
        parser.add_argument('--o', help='output file (if different from input)', required=False)
        parser.add_argument('--features', nargs='*', help='features to include', required=False,
                default=set())
        res = parser.parse_args(args)
        expand.expand(i=res.i, o=res.o or res.i, features=res.features)


    #def trim(self, args):
    #    parser = ArgumentParser(description='trim document according to features')
    #    parser.add_argument('--file', help='file to expand')
    #    parser.add_argument('--features', nargs='*', help='features to include')
    #    res = parser.parse_args(args)
    #    expand.trim(res.file, res.features)


    def help(self, args):
        pass


if __name__ == "__main__":
    Args(sys.argv[1:])
