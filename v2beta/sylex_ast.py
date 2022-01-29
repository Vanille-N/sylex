from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Sequence, TypeVar, Union

T = TypeVar("T")
U = TypeVar("U")

from libparse import Loc, Span, Spanned


def isname(c: str) -> bool:
    return ("a" <= c <= "z") or ("A" <= c <= "Z") or (c in "_-.")


class Symbol(Enum):
    DECLARE = "$"
    OPENBRACE = "{"
    CLOSEBRACE = "}"
    OPENPAREN = "("
    CLOSEPAREN = ")"
    OPENBRACK = "["
    CLOSEBRACK = "]"
    EQUAL = "="
    RIGHT = "->"
    LEFT = "<-"
    COMMA = ","
    SEMI = ";"
    SCOPE = "::"
    COLON = ":"


def indent(text: str) -> str:
    return "\n".join("    " + line for line in text.split("\n"))


@dataclass
class Ident:
    name: Spanned[str]

    @staticmethod
    def concat(s: list[Spanned[str]]) -> Ident:
        print(s)
        string = "".join(c.data for c in s)
        span = Spanned.union(s)
        return Ident(span.with_data(string))

    def __str__(self) -> str:
        return f"Ident({self.name})"


@dataclass
class DefList:
    defs: Sequence[Spanned[Def] | Spanned[Target]]

    def __str__(self) -> str:
        return "DefList {\n" + "\n".join(indent(f"{d}") for d in self.defs) + "\n}"


@dataclass
class Target:
    name: Spanned[Ident]

    def __str__(self) -> str:
        return f"Target {self.name}"


@dataclass
class Def:
    name: Spanned[Ident]
    value: Spanned[ItemList]

    def __str__(self) -> str:
        return f"Def {self.name} := " + self.value.__str__()


@dataclass
class ItemList:
    items: Sequence[Spanned[Item] | Spanned[Expand]]

    def __str__(self) -> str:
        return (
            "ItemList {\n" + "\n".join(indent(i.__str__()) for i in self.items) + "\n}"
        )


@dataclass
class Item:
    entry: Spanned[Entry]
    tail: Optional[Spanned[ItemList]]

    def __str__(self) -> str:
        if self.tail is None:
            return f"Leaf ({self.entry})"
        else:
            return f"Branch ({self.entry}) :: \n" + indent(self.tail.__str__())


@dataclass
class Expand:
    name: Spanned[Ident]

    def __str__(self) -> str:
        return f"Expand({self.name})"


@dataclass
class Label:
    name: Spanned[Ident]
    params: Spanned[Params]

    def __str__(self) -> str:
        return f"Label({self.name})\n  {self.params}"


@dataclass
class Induce:
    name: Spanned[Ident]
    params: Spanned[Params]

    def __str__(self) -> str:
        return f"Induce({self.name})\n  {self.params}"


@dataclass
class Depend:
    name: Spanned[Ident]
    params: Spanned[Params]

    def __str__(self) -> str:
        return f"Depend({self.name})\n  {self.params}"


@dataclass
class Params:
    vals: list[Spanned[Ident]]

    def __str__(self) -> str:
        return "Params(" + ",".join(f"{v}" for v in self.vals) + ")"


Tag = Union[Label, Induce, Depend]


@dataclass
class Entry:
    name: Spanned[Ident]
    labels: list[Spanned[Label]]
    induce: list[Spanned[Induce]]
    depend: list[Spanned[Depend]]

    @staticmethod
    def from_name(name: Spanned[Ident]) -> Entry:
        return Entry(name, [], [], [])

    def push(self, mk: Spanned[Tag]) -> None:
        if isinstance(mk.data, Induce):
            self.induce.append(mk.span.with_data(mk.data))
        elif isinstance(mk.data, Label):
            self.labels.append(mk.span.with_data(mk.data))
        elif isinstance(mk.data, Depend):
            self.depend.append(mk.span.with_data(mk.data))
        else:
            raise TypeError(f"{mk} of type {type(mk)} is not a valid entry marker")

    def __str__(self) -> str:
        s = f"Entry({self.name})"
        for l in self.labels:
            s += "\n" + indent(f"{l}")
        for i in self.induce:
            s += "\n" + indent(f"{i}")
        for d in self.depend:
            s += "\n" + indent(f"{d}")
        return s
