from libparse import Loc, Stream, Span, Spanned, Head
from libparse import Result, Wrong, Error, ErrLevel
import sylex_ast as ast
from typing import Union, Tuple
from enum import Enum
from dataclasses import dataclass

@dataclass
class File:
    path: list[str]
    name: str
    ext: str|None

class Label(Enum):
    ROOT = "root"
    TEX = "tex"
    HDR = "hdr"
    PDF = "pdf"
    FIG = "fig"

@dataclass
class MetaFile:
    file: File
    induce: list[File]
    depend: list[File]
    label: Label

@dataclass
class Feature:
    path: list[str]

@dataclass
class Target:
    files: list[MetaFile]
    figs: list[MetaFile]
    name: str
    root: File
    features: list[Feature]

@dataclass
class Config:
    targets: list[Target]
    errors: list[Tuple[ErrLevel, Error]]

# Config checks                             Critical ?
#  - exist & unique
#     * tag for given file                    (C)
#     * root name                             (C)
#     * root for given STRUCTURE and name     (C)
#  - variable defs
#     * exist                                 (C)
#     * well-ordered                          (C)
#     * capital iff builtin
#     * unused
#  - duplicates
#     * targets                               (C)
#     * files                                 (C)
#  - dependencies
#     * cycle                                 (C)
#     * header depends on non-header
#  - builtins
#     * correct value
#        + TWICE is either true or false      (C)
#        + ROOT value exists                  (C)
#        + FEATURES has no duplicate
#        * defined (default value ok)
#        * no tag
#  - all files exist                          (C)
#  - unused root
#  - dangling dependencies                    (C)
#  - unused dependencies
#  - unused target
#  - no target

# Runtime checks
#  - features exist                           (C)
#  - conditional compilation well-formed      (C)
#  - files exist                              (C)
#  - unused feature
