from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Generic, Optional, Tuple, TypeVar, Union

T = TypeVar("T")


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
    U = TypeVar("U")

    start: Loc
    end: Loc
    text: Text|None

    @staticmethod
    def empty() -> Span:
        return Span(Loc.max(), Loc.min(), None)

    @staticmethod
    def max() -> Span:
        return Span(Loc.max(), Loc.max(), None)

    @staticmethod
    def unit(loc: Loc, text: Text) -> Span:
        return Span(loc, loc, text)

    def with_data(self, data: U) -> Spanned[U]:
        return Spanned(data, self)

    def until(self, other: Optional[Loc | Span] = None) -> Span:
        if other is None:
            return self

        if isinstance(other, Loc):
            return Span(min(other, self.start), max(other, self.end), self.text)
        else:
            text = self.text or other.text
            return Span(min(other.start, self.start), max(other.end, self.end), text)

    def line_diff(self) -> int:
        return self.end.line - self.start.line

    def __str__(self) -> str:
        return f"({self.start}..{self.end})"

    def show(self, color="") -> str:
        if self.text is None:
            if self.start > self.end:
                return "Empty span"
            else:
                return "At end of file"
        return self.text.show(self, color)

class Text:
    def __init__(self, raw: str) -> None:
        self.lines = raw.split('\n')

    RED = "\x1b[31m"
    GREEN = "\x1b[32m"
    YELLOW = "\x1b[33m"
    BLUE = "\x1b[34m"

    def show(self, span: Span, color="") -> str:
        reset = "\x1b[0m"
        bold = "\x1b[1m"
        grey = "\x1b[97m"
        assert span.start <= span.end
        assert span.end.line < len(self.lines)
        nlines = span.line_diff()
        linenum_length = len(str(len(self.lines))) + 1
        blank = "     "
        start_dots = "  ..."
        end_dots = "...  "
        def lineno(n: int|None) -> str:
            s = str(n) if n is not None else ""
            padding = " " * (linenum_length - len(s))
            return f"{color}{bold}{padding}{s} | {reset}"
        if nlines == 0:
            line = self.lines[span.start.line]
            before = span.start.col
            after = span.end.col + 1 - span.start.col
            s = lineno(span.start.line) + blank + grey + line[:before] + reset + bold + line[before:before+after] + reset + grey + line[before+after:] + reset + "\n"
            s += lineno(None) + blank + " " * before + color + "^" * after + reset
            return s
        else:
            top_line = self.lines[span.start.line]
            bot_line = self.lines[span.end.line]
            top_before = span.start.col
            top_after = len(top_line) - top_before
            bot_before = 0
            bot_after = span.end.col + 1
            s = lineno(span.start.line) + blank + grey + top_line[:top_before] + reset + bold + top_line[top_before:] + reset + "\n"
            s += lineno(None) + blank + " " * top_before + color + "^" * top_after + end_dots + reset + "\n"
            if nlines >= 2:
                s += lineno(span.start.line + 1) + blank + bold + self.lines[span.start.line + 1] + "\n"
            if nlines >= 4:
                nbcut = nlines - 3
                s += lineno(None) + blank + f"    {grey}({nbcut} lines cut){reset}\n"
            if nlines >= 3:
                s += lineno(span.end.line - 1) + blank + bold + self.lines[span.end.line - 1] + reset + "\n"
            s += lineno(span.end.line) + blank + bold + bot_line[:bot_after] + reset + grey + bot_line[bot_after:] + reset + "\n"
            s += lineno(None) + color + start_dots + "^" * bot_after + reset
            return s

if __name__ == "__main__":
    text = Text('\n'.join(f"0123456789ABCDEFGHIJKLMNOPQRST ({i})" for i in range(20)))
    print("=" * 50)
    print(text.show(Span(Loc(0,3), Loc(0,7), None), Text.RED))
    print("=" * 50)
    print(text.show(Span(Loc(1,9), Loc(2,3), None), Text.GREEN))
    print("=" * 50)
    print(text.show(Span(Loc(1,9), Loc(3,3), None), Text.YELLOW))
    print("=" * 50)
    print(text.show(Span(Loc(1,9), Loc(4,3), None), Text.BLUE))
    print("=" * 50)
    print(text.show(Span(Loc(1,9), Loc(5,3), None), Text.BLUE))
    print("=" * 50)
    print(text.show(Span(Loc(5,9), Loc(15,3), None), Text.BLUE))
    print("=" * 50)

@dataclass
class Spanned(Generic[T]):
    U = TypeVar("U")

    data: T
    span: Span

    @staticmethod
    def union(lst: list[Spanned[Any]]) -> Span:
        span = Span.empty()
        if len(lst) > 0:
            span.start = min(span.start, lst[0].span.start)
            span.end = max(span.end, lst[-1].span.end)
        return span

    def map(self, fn: Callable[[T], U]) -> Spanned[U]:
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

    def peek(self, idx: int) -> Spanned[T] | None:
        if idx >= len(self.data):
            return None
        return self.data[idx]

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


Result = Union[T, Error]
SpanResult = Result[Spanned[T]]


@dataclass
class Maybe(Generic[T]):
    data: T
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
class Hint:
    peek_idx: int
    take_idx: int
    bump_idx: int

    @staticmethod
    def start() -> Hint:
        return Hint(-1, -1, -1)

    def clone(self) -> Hint:
        return Hint(self.peek_idx, self.take_idx, self.bump_idx)

    def commit(self, other: Hint) -> None:
        self.peek_idx = other.peek_idx
        self.take_idx = other.take_idx
        self.bump_idx = other.bump_idx

    def bump(self, idx: int, value: Any) -> None:
        print(f"bump from {self.bump_idx} to {idx}")
        if idx <= self.bump_idx:
            raise Exception(f"cannot bump '{value}': {idx} has already been bumped before")
        if idx > self.take_idx:
            raise Exception(f"cannot bump '{value}': {idx} must be taken before bumped")
        if idx > self.bump_idx + 1:
            raise Exception(f"cannot bump '{value}': {self.bump_idx + 1} has not been bumped before {idx}")
        self.bump_idx = idx

    def take(self, idx: int, value: Any) -> None:
        print(f"take from {self.take_idx} to {idx}")
        if idx <= self.take_idx:
            raise Exception(f"cannot take '{value}': {idx} has already been taken before")
        if idx <= self.bump_idx:
            raise Exception(f"cannot take '{value}': {idx} has already been bumped before")
        if idx > self.take_idx + 1:
            raise Exception(f"cannot take '{value}': {self.take_idx + 1} has not been taken before {idx}")
        self.take_idx = idx


@dataclass
class Head(Generic[T]):
    U = TypeVar("U")

    _stream: Stream[T]
    _cursor: int
    _hint: Hint

    @staticmethod
    def start(stream: Stream[T]) -> Head[T]:
        return Head(stream, 0, Hint.start())

    def bump(self, nb: int = 1) -> None:
        self._cursor += nb
        self._hint.bump(self._cursor - 1, self._peek_absolute(self._cursor - 1))

    def _peek_absolute_spanned(self, idx: int) -> Optional[Spanned[T]]:
        return self._stream.peek(idx)

    def _peek_absolute(self, idx: int) -> Optional[T]:
        res = self._peek_absolute_spanned(idx)
        if res is None:
            return None
        return res.data

    def _peek(self, nb: int, take: bool) -> Optional[T]:
        idx = self._cursor + nb
        value = self._peek_absolute(idx)
        if take:
            self._hint.take(idx, value)
        return value

    def peek(self, nb: int = 0) -> Optional[T]:
        return self._peek(nb, False)

    def take(self, nb: int = 0) -> Optional[T]:
        return self._peek(nb, True)

    def clone(self) -> Head[T]:
        return Head(self._stream, self._cursor, self._hint.clone())

    def commit(self, other: Head[T]) -> None:
        self._cursor = other._cursor
        self._hint.commit(other._hint)

    def until(self, other: int | Head[T] | Span | None) -> Span:
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
        start = copy.span()
        res = fn(copy)
        end = copy.span(-1)
        print(
            f"function {fn.__name__}\n\tread {res}\n=====\n{start.until(end).show(Text.YELLOW)}\n====="
        )
        if isinstance(res, Error):
            return res
        span = Spanned.union(self._stream[self._cursor : copy._cursor].data)
        self.commit(copy)
        return span.with_data(res)

    def _span_absolute(self, idx: int) -> Span:
        pk = self._peek_absolute_spanned(idx)
        if pk is None:
            return Span.max()
        return pk.span

    def span(self, idx: int = 0) -> Span:
        return self._span_absolute(self._cursor + idx)

    def err(self, kind: str, msg: str, span: Span) -> Error:
        return Error(kind, msg, self.until(span))
