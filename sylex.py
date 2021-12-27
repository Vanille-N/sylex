#! /bin/env python3

# SyLeX
#   Build descriptor for LaTeX

import re
import sys
import os
import jinja2 as j2

from error import Err
import lib
import parse
from args import Args

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
    for mod in ["args", "lib", "error", "parse", "sylex"]:
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

def main(args):
    args = Args(args[1:])
    if args.mode == "make":
        if args.action == "common":
            print_common()
            return
        elif args.action == "watcher":
            print_texwatch()
            return
    elif args.mode == "init":
        print_init()
    elif args.mode == "build":
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
        cfg = parse.parse_cfg(args)
        if cfg is not None:
            cfg.print(args)
        elif args.fail <= Err.fatality:
            if args.fail == Err.NEVER:
                sys.exit(0)
            sys.exit(2)
    else:
        Err.report(
            kind="Unspecified mode",
            msg="nothing to do",
        )

if __name__ == "__main__":
    main(sys.argv)
