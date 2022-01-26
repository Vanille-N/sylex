from enum import Enum
import typing as ty
from dataclasses import dataclass

T = ty.TypeVar("T")
U = ty.TypeVar("U")

from libparse import Loc, Span, Spanned

def isname(c: str) -> bool:
    return ('a' <= c <= 'z') or ('A' <= c <= 'Z') or (c in '_-.')

class Symbol(Enum):
    DECLARE = '$'
    OPENBRACE = '{'
    CLOSEBRACE = '}'
    OPENPAREN = '('
    CLOSEPAREN = ')'
    EQUAL = '='
    RIGHT = '->'
    LEFT = '<-'
    COMMA = ','
    SEMI = ';'
    SCOPE = '::' # Must be _before_ COLON
    COLON = ':'

def indent(text: str) -> str:
    return '\n'.join('    ' + line for line in text.split('\n'))

@dataclass
class Ident:
    name: Spanned[str]

    @staticmethod
    def concat(s: list[Spanned[str]]) -> 'Ident':
        print(s)
        string = ''.join(c.data for c in s)
        span = Spanned.union(s)
        return Ident(span.with_data(string))

    def __str__(self):
        return f"'{self.name}'"

@dataclass
class DefList:
    defs: list[Spanned['Def']]

    def __str__(self):
        return "DefList {\n" + '\n'.join(indent(f"{d}") for d in self.defs) + "\n}"

@dataclass
class Target:
    name: Spanned[Ident]

    def __str__(self):
        return f"Target {self.name}"

@dataclass
class Def:
    name: Spanned[Ident]
    value: Spanned['ItemList']

    def __str__(self):
        return f"Def {self.name} := " + self.value.__str__()

@dataclass
class ItemList:
    items: list[Spanned['Item']]

    def __str__(self):
        return "ItemList {\n" + '\n'.join(indent(i.__str__()) for i in self.items) + "\n}"

@dataclass
class Item:
    entry: Spanned['Entry']
    tail: ty.Optional[Spanned[ItemList]]

    def __str__(self):
        if self.tail is None:
            return f"Leaf ({self.entry})"
        else:
            return f"Branch ({self.entry}) :: \n" + indent(self.tail.__str__())

@dataclass
class Expand:
    name: Spanned[Ident]

    def __str__(self):
        return f"Expand({self.name})"

@dataclass
class Tag:
    name: Spanned[Ident]
    params: Spanned['Params']

    def __str__(self):
        return f"Tag({self.name}:{','.join(p.__str__() for p in self.params)})"

@dataclass
class Entry:
    name: Spanned[Ident]
    labels: list[Spanned['Label']]
    induce: list[Spanned['Induce']]
    depend: list[Spanned['Depend']]

    def extend(self, markers: list[ty.Union[Spanned['Label'], Spanned['Induce'], Spanned['Depend']]]):
        for mk in markers:
            if isinstance(mk.data, Induce): self.induce.append(mk)
            elif isinstance(mk.data, Label): self.labels.append(mk)
            elif isinstance(mk.data, Depend): self.depend.append(mk)
            else: raise TypeError(f"{mk} of type {type(mk)} is not a valid entry marker")

    def __str__(self):
        s = f"Entry({self.name})"
        for m in self.label + self.induce + self.depend:
            s += '\n' + indent(f"{m}")
        return s

@dataclass
class Label:
    name: Spanned[Ident]
    params: Spanned['Params']

    def __str__(self):
        return f"Label({self.name})\n  {self.params}"

@dataclass
class Induce:
    name: Spanned[Ident]
    params: Spanned['Params']

    def __str__(self):
        return f"Induce({self.name})\n  {self.params}"


@dataclass
class Depend:
    name: Spanned[Ident]
    params: Spanned['Params']

    def __str__(self):
        return f"Depend({self.name})\n  {self.params}"

@dataclass
class Params:
    vals: list[Spanned[Ident]]

    def __str__(self):
        return "Params(" + ",".join(f"{v}" for v in self.vals) + ")"

