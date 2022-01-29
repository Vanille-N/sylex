from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Generic, Optional, Tuple, TypeVar, Union

T = TypeVar("T")
U = TypeVar("U")
V = TypeVar("V")
TCo = TypeVar("TCo", covariant=True)
UCo = TypeVar("UCo", covariant=True)
VCo = TypeVar("VCo", covariant=True)


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

    def newline(self) -> Loc:
        return Loc(self.line + 1, 0)

    def newcol(self) -> Loc:
        return Loc(self.line, self.col + 1)

    def cmp(self, other: Loc) -> int:
        if self.line < other.line:
            return -1
        elif self.line > other.line:
            return 1
        elif self.col < other.col:
            return -1
        elif self.col > other.col:
            return 1
        else:
            return 0

    def __lt__(self, other: Loc) -> bool:
        return self.cmp(other) < 0

    def __le__(self, other: Loc) -> bool:
        return self.cmp(other) <= 0

    def __gt__(self, other: Loc) -> bool:
        return self.cmp(other) > 0

    def __ge__(self, other: Loc) -> bool:
        return self.cmp(other) >= 0

    def __str__(self) -> str:
        return f"{self.line}:{self.col}"


@dataclass
class Span:
    start: Loc
    end: Loc

    @staticmethod
    def empty() -> Span:
        return Span(Loc.max(), Loc.min())

    @staticmethod
    def unit(loc: Loc) -> Span:
        return Span(loc, loc)

    def with_data(self, data: T) -> Spanned[T]:
        return Spanned(data, self)

    def until(self, other: Optional[Union[Loc, Span]]) -> Span:
        if other is None:
            return self
        elif isinstance(other, Loc):
            return Span(min(other, self.start), max(other, self.end))
        else:
            return Span(min(other.start, self.start), max(other.end, self.end))

    def __str__(self) -> str:
        return f"({self.start}..{self.end})"


@dataclass
class Spanned(Generic[TCo]):
    data: TCo
    span: Span

    @staticmethod
    def union(lst: list[Spanned[Any]]) -> Span:
        span = Span.empty()
        if len(lst) > 0:
            span.start = min(span.start, lst[0].span.start)
            span.end = max(span.end, lst[-1].span.end)
        return span

    def map(self: Spanned[TCo], fn: Callable[[TCo], U]) -> Spanned[U]:
        return Spanned(fn(self.data), self.span)

    def __str__(self) -> str:
        return f"({self.span.start}@ {self.data} @{self.span.end})"


@dataclass
class Stream(Generic[T]):
    data: list[Spanned[T]]

    @staticmethod
    def empty() -> Stream[T]:
        return Stream([])

    def append(self, data: Spanned[T]) -> None:
        self.data.append(data)

    def peek(self, idx: int) -> Optional[Spanned[T]]:
        if idx < len(self.data):
            return self.data[idx]
        else:
            return None

    def __getitem__(self, idx: slice) -> Stream[T]:
        return Stream(self.data[idx])


BackRef = Tuple[Span, Span]
ErrExtra = Span | None | BackRef


@dataclass
class Error:
    kind: str
    msg: str
    extra: ErrExtra


class ErrLevel(Enum):
    CRITICAL = 4
    WARNING = 3
    DETAIL = 2
    INFO = 1


Result = Union[UCo, Error]
SpanResult = Result[Spanned[UCo]]


@dataclass
class Maybe(Generic[UCo]):
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
class Head(Generic[T]):
    _stream: Stream[T]
    _cursor: int

    @staticmethod
    def start(stream: Stream[T]) -> Head[T]:
        return Head(stream, 0)

    def bump(self, nb: int = 1) -> None:
        self._cursor += nb

    def _peek_absolute(self, idx: int) -> Optional[Spanned[T]]:
        return self._stream.peek(idx)

    def peek(self, nb: int = 0) -> Optional[Spanned[T]]:
        return self._peek_absolute(self._cursor + nb)

    def clone(self) -> Head[T]:
        return Head(self._stream, self._cursor)

    def commit(self, other: Head[T]) -> None:
        self._cursor = other._cursor

    def until(self, other: Union[int, Head[T], Span, None]) -> Span:
        if other is None:
            span = Span.empty()
        elif isinstance(other, Head):
            span = self._span_absolute(other._cursor)
        elif isinstance(other, Span):
            span = other
        else:
            span = self._span_absolute(self._cursor + other)
        return (self.span() or Span.empty()).until(span)

    def sub(self, fn: Callable[[Head[T]], Result[U]]) -> SpanResult[U]:
        print(f"enter {fn.__name__}")
        copy = self.clone()
        res = fn(copy)
        print(
            f"function {fn.__name__}\n\tread {res}\n\tbetween {self.span()} and {copy.span()}"
        )
        if isinstance(res, Error):
            return res
        span = Spanned.union(self._stream[self._cursor : copy._cursor].data)
        self.commit(copy)
        return span.with_data(res)

    def _span_absolute(self, idx: int) -> Span:
        pk = self._peek_absolute(idx)
        if pk is None:
            return Span(Loc.max(), Loc.max())
        return pk.span

    def span(self, idx: int = 0) -> Span:
        return self._span_absolute(self._cursor + idx)

    def err(self, kind: str, msg: str, span: Span) -> Error:
        return Error(kind, msg, self.until(span))
