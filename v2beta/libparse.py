from dataclasses import dataclass
import typing as ty

T = ty.TypeVar("T")
U = ty.TypeVar("U")
V = ty.TypeVar("V")
TCo = ty.TypeVar("TCo", covariant=True)
UCo = ty.TypeVar("UCo", covariant=True)
VCo = ty.TypeVar("VCo", covariant=True)


@dataclass
class Loc:
    line: int
    col: int

    @staticmethod
    def max() -> 'Loc':
        return Loc(1_000_000, 1_000_000)
    @staticmethod
    def min() -> 'Loc':
        return Loc(-1, -1)

    def newline(self) -> 'Loc':
        return Loc(self.line + 1, 0)

    def newcol(self) -> 'Loc':
        return Loc(self.line, self.col + 1)

    def cmp(self, other: 'Loc') -> int:
        if self.line < other.line: return -1
        elif self.line > other.line: return 1
        elif self.col < other.col: return -1
        elif self.col > other.col: return 1
        else: return 0

    def __lt__(self, other: 'Loc'): return self.cmp(other) < 0
    def __le__(self, other: 'Loc'): return self.cmp(other) <= 0

@dataclass
class Span:
    start: Loc
    end: Loc

    @staticmethod
    def empty() -> 'Span':
        return Span(Loc.max(), Loc.min())

    @staticmethod
    def unit(loc: Loc) -> 'Span':
        return Span(loc, loc)

    def with_data(self, data: T) -> 'Spanned[T]':
        return Spanned(data, self)

    def extend(self, other: ty.Union[ty.Optional[Loc], ty.Optional['Span']]) -> 'Span':
        if other is None:
            return self
        elif isinstance(other, Loc):
            return Span(min(other, self.start), max(other, self.end))
        else:
            return Span(min(other.start, self.start), max(other.end, self.end))

@dataclass
class Spanned(ty.Generic[TCo]):
    data: TCo
    span: Span

    @staticmethod
    def union(lst: list['Spanned[ty.Any]']) -> Span:
        span = Span.empty()
        if len(lst) > 0:
            span.start = min(span.start, lst[0].span.start)
            span.end = max(span.end, lst[-1].span.end)
        return span

    def map(self: 'Spanned[TCo]', fn: ty.Callable[[TCo], U]) -> 'Spanned[U]':
        return Spanned(fn(self.data), self.span)

@dataclass
class Stream(ty.Generic[T]):
    data: list[Spanned[T]]

    @staticmethod
    def empty() -> 'Stream[T]':
        return Stream([])

    def append(self, data: Spanned[T]):
        self.data.append(data)

    def peek(self, idx: int) -> ty.Optional[Spanned[T]]:
        if idx < len(self.data):
            return self.data[idx]
        else:
            return None

    def __getitem__(self, idx: slice):
        return self.data[idx]

@dataclass
class Error:
    kind: str
    msg: str
    span: ty.Optional[Span]

@dataclass
class Wrong(ty.Generic[TCo]):
    inner: TCo

class Unreachable(Exception):
    pass

Result = ty.Union[UCo, Wrong[VCo]]

@dataclass
class Maybe(ty.Generic[UCo]):
    data: UCo
    diagnostic: Error
# What's the use-case of Maybe, you may ask ?
# Consider the grammar a?b
# If you reab cb then a? matches nothing and b fails to read c
# The reported error is "found c when b was expected"
# but the actual diagnostic should be "found c when _a_ was expected"
# Thus Maybe[U] is a way of saying "This is as far as I can parse U,
# but if an error were to occur immediately afterwards, blame it on U not
# on what comes after"
# This also holds for lists:
#     [ element, element, elem ]
# should be reported as
#                         ^^^^ unterminated 'element'
# instead of
#                       ^ expected ]

@dataclass
class Head(ty.Generic[T]):
    stream: Stream[T]
    cursor: int

    @staticmethod
    def start(stream: Stream[T]) -> 'Head[T]':
        return Head(stream, 0)

    def bump(self, nb: int = 1):
        self.cursor += 1

    def peek_absolute(self, idx: int):
        return self.stream.peek(idx)

    def peek(self, nb: int = 0):
        return self.peek_absolute(self.cursor + nb)

    def clone(self) -> 'Head[T]':
        return Head(self.stream, self.cursor)

    def commit(self, other: 'Head[T]'):
        self.cursor = other.cursor

    def until(self, idx: ty.Union[int, 'Head[T]']) -> Span:
        if isinstance(idx, Head):
            idx = idx.cursor
        else:
            idx = self.cursor + idx
        return (self.span() or Span.empty()).extend(self.span_absolute(idx))

    def sub(self, fn: ty.Callable[['Head[T]'], ty.Union[U, Wrong[V]]]) -> ty.Union[Spanned[U], Wrong[V]]:
        start = self.cursor
        res = fn(self)
        end = self.cursor
        if isinstance(res, Wrong):
            self.cursor = start
            return res
        else:
            return Spanned.union(self.stream[start:end]).with_data(res)

    def span_absolute(self, idx: int) -> ty.Optional[Span]:
        pk = self.peek_absolute(idx)
        if pk is None:
            return None
        return pk.span

    def span(self, idx: int = 0) -> ty.Optional[Span]:
        return self.span_absolute(self.cursor + idx)

    def err(self, kind: str, msg: str, span: Span = None) -> Wrong[Error]:
        return Wrong(Error(kind, msg, span))

    def current(self) -> int:
        return self.cursor
    def restore(self, idx: int):
        self.cursor = idx



