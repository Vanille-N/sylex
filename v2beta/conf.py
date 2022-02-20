from __future__ import annotations
from libparse import Loc, Stream, Span, Spanned, Head
from libparse import Result, Error, ErrLevel
import sylex_ast as ast
import parse
from typing import Union, Tuple, Callable
from enum import Enum
from dataclasses import dataclass
import os

# should eventually be the path from which sylex.conf was read
root = os.getcwd().split("/")[1:]

@dataclass
class File:
    path: list[str]
    ext: str | None

    def append(self, name: str) -> File:
        return File(self.path + [name], self.ext)

    def with_ext(self, ext: str) -> File:
        return File([*self.path], ext)

    @staticmethod
    def root() -> File:
        return File(root, None)


class Label(Enum):
    ROOT = "root"
    TEX = "tex"
    HDR = "hdr"
    PDF = "pdf"
    FIG = "fig"


@dataclass
class MetaFile:
    file: File
    induce: list[str]
    depend: list[str]
    label: Label|None

    def map(self, fn: Callable[[File], File]) -> MetaFile:
        return MetaFile(fn(self.file), self.induce, self.depend, self.label)

    def with_label(self, label: Label) -> MetaFile:
        return MetaFile(self.file, self.induce, self.depend, label)

    def with_induce(self, induce: str) -> MetaFile:
        return MetaFile(self.file, self.induce + [induce], self.depend, self.label)

    def with_depend(self, depend: str) -> MetaFile:
        return MetaFile(self.file, self.induce, self.depend + [depend], self.label)

    @staticmethod
    def root() -> MetaFile:
        return MetaFile(File.root(), [], [], None)

@dataclass
class Feature:
    path: list[str]


@dataclass
class Target:
    name: str
    files: list[MetaFile]
    figs: list[MetaFile]
    root: File
    features: list[Feature]


@dataclass
class ErrorRecord:
    severity: ErrLevel
    errors: list[Tuple[ErrLevel, Error]]

    @staticmethod
    def new() -> ErrorRecord:
        return ErrorRecord(ErrLevel.NONE, [])

    def append(self, level: ErrLevel, err: Error) -> None:
        self.severity = max(self.severity, level)
        self.errors.append((level, err))

    def extend(self, other: ErrorRecord) -> None:
        self.severity = max(self.severity, other.severity)
        self.errors.extend(other.errors)


@dataclass
class Config:
    targets: list[Target]
    errors: ErrorRecord

    @staticmethod
    def new() -> Config:
        return Config([], ErrorRecord.new())


@dataclass
class Group:
    files: dict[str, dict[str, Tuple[Span, MetaFile]]]

    def add(self, label: str, name: str, span: Span, file: MetaFile) -> Error|None:
        if label not in self.files:
            self.files[label] = {}
        if name in self.files[label]:
            return Error("File defined twice",
                    f"found definition for file '{name}', but it was already defined earlier",
                    span,
                    Error("Caused by:",
                        f"'{name}' already defined here",
                        self.files[label][name][0], None))
        self.files[label][name] = (span, file)
        return None



# Config checks                             Critical ?             Implemented
#  - exist & unique                                                  [ ]
#     * tag for given file                    (C)                    [ ]
#     * root for given STRUCTURE and name     (C)                    [ ]
#  - variable defs                                                   [ ]
#     * exist                                 (C)                    [ ]
#     * well-ordered                          (C)                    [ ]
#     * capital iff builtin                                          [ ]
#     * unused                                                       [ ]
#  - duplicates                                                      [ ]
#     * targets                               (C)                    [ ]
#     * files                                 (C)                    [ ]
#  - dependencies                                                    [ ]
#     * cycle                                 (C)                    [ ]
#     * header depends on non-header                                 [ ]
#  - builtins                                                        [ ]
#     * correct value                                                [ ]
#        + TWICE is either true or false      (C)                    [ ]
#        + ROOT value exists                  (C)                    [ ]
#        + FEATURES has no duplicate                                 [ ]
#        * defined (default value ok)                                [ ]
#        * no tag                                                    [ ]
#  - all files exist                          (C)                    [ ]
#  - unused root                                                     [ ]
#  - dangling dependencies                    (C)                    [ ]
#  - unused dependencies                                             [ ]
#  - unused target                                                   [ ]
#  - no target                                                       [ ]

# Runtime checks
#  - features exist                           (C)                    [ ]
#  - conditional compilation well-formed      (C)                    [ ]
#  - files exist                              (C)                    [ ]
#  - unused feature                                                  [ ]

def group_of_val(name: Spanned[ast.Ident], val: Spanned[ast.ItemList]) -> Tuple[Group|None, ErrorRecord]:
    record = ErrorRecord.new()
    def walk_list(prefix: MetaFile, its: Spanned[ast.ItemList]) -> None:
        print(f"horizontal walk: {prefix}, {its}")
    def walk_item(prefix: MetaFile, it: Spanned[ast.Item]) -> None:
        print(f"vertical walk: {prefix}, {it}")
    walk_list(MetaFile.root(), val)
    record.append(ErrLevel.INTERNAL, Error("Not implemented", "group_of_val", val.span, None))
    return (None, record)

def config_of_tree(tree: Spanned[ast.DefList]) -> Config:
    variables: dict[str, Group] = {}
    config = Config.new()
    for definition in tree.data.defs:
        loc = definition.span
        if isinstance(definition.data, ast.Def):
            name = definition.data.name
            val = definition.data.value
            group,record = group_of_val(name, val)
            print(f">>> Def {name}: {val}")
            config.errors.extend(record)
            if group is None:
                return config
            variables[name.data.name] = group
        else:
            target = definition.data.name
            print(f">>> Target: {target}")
    raise NotImplementedError()


def main(raw: str) -> Result[Config]:
    tree = parse.main(raw, parse.parse_deflist)
    if isinstance(tree, Error):
        return tree
    conf = config_of_tree(tree)
    return conf

if __name__ == "__main__":
    with open("sylex.conf") as f:
        raw = f.read();
    print(main(raw))
