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

class Phantom:
    def __init__(self, data):
        self.data = data
        if hasattr(data, 'span'):
            self.span = data.span

    def __str__(self):
        return self.data.__str__()


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
        print(args)
        print([a for a in args if type(a) != Phantom])
        data = fn(*[a for a in args if type(a) != Phantom])
        res = Localized(span, data, args)
        return res

    def replace(self, val):
        return Localized(self.span, val, self.sub)


class EOS:
    def __str__(self):
        return "<EOS>"

class Peek:
    pass

class ParsingFailure(Exception):
    def __init__(self, msg, peek, child=None):
        self.msg = msg
        self.peek = peek
        self.child = child
        super().__init__(msg)

    def __str__(self):
        def msg(x):
            if x is None:
                return []
            else:
                return [(x.msg, x.peek[0])] + msg(x.child)
        s = f"An error occurred\n  " + '\n  '.join(f"caused by '{msg}' at '{peek}'" for (msg,peek) in msg(self))
        return s

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
        self.select = []
        self.save_start = []
        self.save_head = []
        self.accum = []

    def enter(self):
        self.save_start.append(self.start)
        self.save_head.append(self.head)

    def rollback(self):
        self.start = self.save_start.pop()
        self.head = self.save_head.pop()

    def commit(self):
        self.save_start.pop()
        self.save_head.pop()

    def subproc(fn):
        def inner(st):
            st.enter()
            st.accum.append([])
            try:
                res = fn(st)
                st.accum.pop()
                return True, res
            except ParsingFailure as e:
                st.accum.pop()
                return False, (e.msg, e.peek, e.child)
        return inner
    def subproc_exc(fn):
        def inner(st):
            st.enter()
            st.accum.append([])
            try:
                res = fn(st)
                return res
            finally:
                st.accum.pop()
        return inner

    def fail(self, msg, child=None):
        assert len(self.save_start) > 0
        peek = self.toks[self.save_start[-1]:self.head+1]
        self.rollback()
        print(f"Inner failure: {msg}")
        raise ParsingFailure(msg, peek, child)

    def accept(self, fn):
        self.commit()
        return Localized.map(fn, self.accum[-1])

    def matches(self, *pats):
        old_select = len(self.select)
        if self.head + len(pats) > len(self.toks):
            return False
        def pattern_match(p, t):
            if type(p) == type:
                return type(t.data) == p
            elif callable(p):
                try:
                    return p(t.data)
                except:
                    return False
            else:
                return t.data == p
        for i,p in enumerate(pats):
            t = self.toks[self.head + i]
            if type(p) == Phantom:
                compare = p.data
                record = Phantom(t)
            else:
                compare = p
                record = t
            if pattern_match(compare, t):
                self.select.append(record)
            else:
                self.select = self.select[:old_select]
                return False
        self.head += len(pats)
        return True

    def assert_matches(self, *pats, failure):
        if self.matches(*pats):
            return
        else:
            self.fail(failure)

    def sub(self, fn, failure):
        try:
            return fn(self)
        except ParsingFailure as e:
            self.fail(failure, e)

    def __str__(self):
        return "[" + ", ".join(f"{i}" for i in self.toks) + "]"

    def take(self, fn=None):
        res = Localized.map(fn, self.select)
        self.start = self.head
        self.select = []
        print(res)
        return res

    def take_register(self, fn=None):
        res = self.take(fn)
        self.accum[-1].append(res)

    def register(self, arg):
        self.accum[-1].append(arg)

    def drop(self):
        self.start = self.head
        self.select = []

