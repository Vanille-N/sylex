class Loc:
    infty = 1000000
    def __init__(self, line, col):
        self.line = line
        self.col = col

    def newcol(self):
        return Loc(self.line, self.col + 1)

    def newline(self):
        return Loc(self.line + 1, 0)

    def __str__(self):
        return f"{self.line}:{self.col}"

    def cmp(self, other):
        if self.line < other.line: return -1
        elif self.line > other.line: return 1
        elif self.col < other.col: return -1
        elif self.col > other.col: return 1
        else: return 0

    def __le__(self, other): return self.cmp(other) <= 0
    def __lt__(self, other): return self.cmp(other) < 0


class Span:
    def __init__(self, start, end):
        self.start = start
        self.end = end

    def cup(self, other):
        return Span(min(self.start, other.start), max(self.end, other.end))

    def empty():
        return Span(Loc(Loc.infty, Loc.infty), Loc(-Loc.infty, -Loc.infty))

    def bigcup(spans):
        spans = [s for s in spans] + [Span.empty()]
        return Span(min(s.start for s in spans), max(s.end for s in spans))

    def unit(i):
        return Span(i, i)

    def __str__(self):
        return f"({self.start}--{self.end})"

class Localized:
    def __init__(self, span, data, sub):
        self.span = span
        self.data = data
        self.sub = sub

    def unit(idx, data):
        return Localized(Span.unit(idx), data, [])

    def __str__(self):
        return f"[{self.data} @ {self.span}]"
    def __repr__(self):
        return self.__str__()

    def map(fn, args):
        if fn == None:
            if len(args) == 1:
                return args[0]
            else:
                fn = lambda *x: x
        span = Span.bigcup(t.span for t in args)
        data = fn(*[t.data for t in args])
        res = Localized(span, data, args)
        return res

    def replace(self, val):
        return Localized(self.span, val, self.sub)


class EOS:
    def __str__(self):
        return "<EOS>"

class Peek:
    pass

class Stream:
    def __init__(self, it):
        if len(it) == 0:
            last = Loc(0, 0)
        else:
            last = it[-1].span.end.newcol()
        self.toks = [i for i in it] + [Localized.unit(last, EOS())]
        for i,t in enumerate(self.toks):
            if type(t) == Localized:
                pass
            else:
                self.toks[i] = Localized.unit(i, t)
        self.start = 0
        self.head = 0
        self.save_start = []
        self.save_head = []

    def enter(self):
        self.save_start.append(self.start)
        self.save_head.append(self.head)

    def rollback(self):
        self.start = self.save_start.pop()
        self.head = self.save_head.pop()

    def commit(self):
        self.save_start.pop()
        self.save_head.pop()

    def fail(self, msg, child=None):
        assert len(self.save_start) > 0
        peek = self.toks[self.save_start[-1]:self.head+1]
        self.rollback()
        print(f"Inner failure: {msg}")
        return (False, (msg, peek, child))

    def abort(self, msg, child=None):
        assert len(self.save_start) > 0
        peek = self.toks[self.save_start[-1]:self.head+1]
        self.rollback()
        print(f"Inner failure: {msg}")
        return (None, (msg, peek, child))

    def accept(self, fn, args):
        self.commit()
        return (True, Localized.map(fn, args))

    def forward(self, ok, res):
        if ok:
            self.commit()
        else:
            self.rollback()
        return (ok, res)

    def matches(self, *pats):
        if self.head + len(pats) > len(self.toks):
            return False
        for i,p in enumerate(pats):
            if type(p) == type:
                if type(self.toks[self.head + i].data) == p:
                    continue
                else:
                    return False
            elif callable(p):
                try:
                    if p(self.toks[self.head + i].data):
                        continue
                    else:
                        return False
                except:
                    return False
            else:
                if self.toks[self.head + i].data == p:
                    continue
                else:
                    return False
        self.head += len(pats)
        return True

    def __str__(self):
        return "[" + ", ".join(f"{i}" for i in self.toks) + "]"

    def take(self, fn=None):
        res = Localized.map(fn, self.toks[self.start:self.head])
        self.start = self.head
        print(res)
        return res

    def drop(self):
        self.start = self.head

