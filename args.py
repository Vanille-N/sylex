#! /bin/env python3

# SyLeX
#   Build descriptor for LaTeX

import re
import sys
import os
import jinja2 as j2

from error import Err

class Args:
    def __init__(self, args):
        self.fail = None
        self.name = None
        Err.in_file("<cmdline>")
        self.action = None
        self.mode = None
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
                elif self.mode == "build" and key == "name":
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
                if a == "make":
                    self.mode = "make"
                elif a == "build":
                    self.mode = "build"
                elif a == "init":
                    self.mode = "init"
                elif a == "help":
                    print("Help unavailable at the moment")
                    sys.exit(255)
                elif self.mode == "make":
                    if a == "common" or a == "watcher":
                        if self.action is not None:
                            Err.report(
                                kind="Argparse: Multiple Actions",
                                msg="can only perform one action at a time",
                            )
                        self.action = a
                    else:
                        Err.report(
                            kind="Argparse: Unknown Flag",
                            msg="'{}' is not recognized in mode '{}'".format(a, self.mode),
                        )
                else:
                    Err.report(
                        kind="Argparse: Unknown Mode",
                        msg="'{}' is not a known mode".format(a),
                    )
        if Err.fatality >= Err.WARNING:
            if Err.fatality == Err.NEVER:
                sys.exit(0)
            sys.exit(1)
        if self.fail is None:
            self.fail = Err.ERROR
        if self.name is not None:
            self.src = f"cfg_{self.name}.slx"
            os.makedirs('build', exist_ok=True)
            self.dest = f"build/doc_{self.name}.tex.mk"

