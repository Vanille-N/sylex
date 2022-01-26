from enum import Enum
import typing as ty
from dataclasses import dataclass

T = ty.TypeVar("T")
U = ty.TypeVar("U")

@dataclass
class Loc:
    line: int
    col: int

    @staticmethod
    def max() -> Loc:
        return Loc(1_000_000, 1_000_000)
    @staticmethod
    def min() -> Loc:
        return Loc(-1, -1)

    def cmp(self, other: Loc) -> int:
        if self.line < other.line: return -1
        elif self.line > other.line: return 1
        elif self.col < other.col: return -1
        elif self.col > other.col: return 1
        else: return 0

    def __lt__(self, other: Loc): return self.cmp(other) < 0
    def __le__(self, other: Loc): return self.cmp(other) <= 0

@dataclass
class Span(ty.Generic[T]):
    data: T
    start: Loc
    end: Loc

    @staticmethod
    def default() -> Span[None]:
        return Span(None, Loc.max(), Loc.min())

    @staticmethod
    def unit(data: T, loc: Loc) -> Span[T]:
        return Span(data, loc, loc)

    @staticmethod
    def union(lst: list[Span[ty.Any]]) -> Span[None]:
        start = Loc.max()
        end = Loc.min()
        for s in lst:
            start = min(start, s.start)
            end = max(end, s.end)
        return Span(None, start, end)

    def map(self: Span[T], fn: ty.Callable[[T], U]) -> Span[U]:
        return Span(fn(self.data), self.start, self.end)

    def replace(self, new: U) -> Span[U]:
        return Span(new, self.start, self.end)

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
    name: Span[str]

    @staticmethod
    def concat(s: list[Span[str]]) -> Ident:
        print(s)
        string = ''.join(c.data for c in s)
        span = Span.union(s)
        return Ident(span.replace(string))

    def __str__(self):
        return f"'{self.name}'"

@dataclass
class DefList:
    defs: list[Span[Def]]

    def __str__(self):
        return "DefList {\n" + '\n'.join(indent(f"{d}") for d in self.defs) + "\n}"

@dataclass
class Target:
    name: Span[Ident]

    def __str__(self):
        return f"Target {self.name}"

@dataclass
class Def:
    name: Span[Ident]
    value: Span[ItemList]

    def __str__(self):
        return f"Def {self.name} := " + self.value.__str__()

@dataclass
class ItemList:
    items: list[Item]

    def __str__(self):
        return "ItemList {\n" + '\n'.join(indent(i.__str__()) for i in self.items) + "\n}"

@dataclass
class Item:
    entry: Span[Entry]
    tail: ty.Optional[Span[ItemList]]

    def __str__(self):
        if self.tail is None:
            return f"Leaf ({self.entry})"
        else:
            return f"Branch ({self.entry}) :: \n" + indent(self.tail.__str__())

@dataclass
class Expand:
    name: Span[Ident]

    def __str__(self):
        return f"Expand({self.name})"

@dataclass
class Tag:
    name: Span[Ident]
    params: Span[Params]

    def __str__(self):
        return f"Tag({self.name}:{','.join(p.__str__() for p in self.params)})"

@dataclass
class Entry:
    name: Span[Ident]
    labels: list[Span[Label]]
    induce: list[Span[Induce]]
    depend: list[Span[Depend]]

    def extend(self, markers: list[ty.Union[Span[Label], Span[Induce], Span[Depend]]]):
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
    name: Span[Ident]
    params: Span[Params]

    def __str__(self):
        return f"Label({self.name})\n  {self.params}"

@dataclass
class Induce:
    name: Span[Ident]
    params: Span[Params]

    def __str__(self):
        return f"Induce({self.name})\n  {self.params}"


@dataclass
class Depend:
    name: Span[Ident]
    params: Span[Params]

    def __str__(self):
        return f"Depend({self.name})\n  {self.params}"

@dataclass
class Params:
    vals: list[Span[Ident]]

    def __str__(self):
        return "Params(" + ",".join(f"{v}" for v in self.vals) + ")"

