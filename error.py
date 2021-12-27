#! /bin/env python3

# SyLeX
#   Build descriptor for LaTeX

# Error reporting with uniform formatting and colored output
class Err:
    fname = ""
    line = 0

    ALWAYS = 0
    WARNING = 1
    ERROR = 2
    NEVER = 3
    fatality = ALWAYS

    def in_file(fname):
        Err.fname = fname
        Err.line = 0

    def count_line(text):
        Err.line += 1
        Err.text = text

    def report(*,
        kind,
        msg,
        fatal=True,
    ):
        Err.fatality = max(Err.fatality, Err.ERROR if fatal else Err.WARNING)
        print("fatality: {}".format(Err.fatality))
        print("In \x1b[36m{}:{}\x1b[0m, '{}'".format(Err.fname, Err.line, Err.text))
        print("{}: {}\x1b[0m".format(
            "\x1b[1;31mError" if fatal else "\x1b[1;33mWarning", kind
        ))
        print("    {}".format(msg))
        print()

