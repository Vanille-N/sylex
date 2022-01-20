import tokstream as toks
from enum import Enum

def chars_of_text(text):
    loc = toks.Loc(0, 0)
    chars = []
    for c in text:
        chars.append(toks.Localized.unit(loc, c))
        if c == '\n':
            loc = loc.newline()
        else:
            loc = loc.newcol()

    return chars

def concat(*s):
    return ''.join(s)

def isname(c):
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

class Ident:
    def __init__(self, name):
        self.name = name

    def concat(*s):
        return Ident(''.join(s))

    def __str__(self):
        return f"{self.name}"

def tokens_of_chars(chars):
    st = toks.Stream(chars)
    l = []
    while True:
        for s in Symbol:
            if st.matches(*[c for c in s.value]):
                l.append(st.take().replace(s))
        if st.matches('#'):
            while st.matches(lambda c: c != '\n'):
                pass
            st.drop()
        elif st.matches('\n') or st.matches('\t') or st.matches(' '):
            st.drop()
        elif st.matches(isname):
            while st.matches(isname):
                pass
            l.append(st.take(Ident.concat))
        elif st.matches(toks.EOS):
            l.append(st.take())
            break
        else:
            raise NotImplementedError(",".join(f"{t}" for t in st.toks[st.head:]))
            print(f"head: {st.head}")
    return l

def tree_of_tokens(tokens):
    st = toks.Stream(tokens)
    return parse_def_list(st)

def parse_def_list(st):
    st.enter()
    d = []
    while True:
        ok, res = parse_target(st)
        if ok:
            d.append(res)
            continue
        ok, res = parse_def(st)
        if ok:
            d.append(res)
        else: break
    if st.matches(toks.EOS):
        return st.accept(DefList, d)
    else:
        return st.forward(ok, res)

class DefList:
    def __init__(self, *args):
        print('DefList', *args)

def parse_def(st):
    #   '$' Ident '=' ItemList ';'
    st.enter()
    d = []
    if st.matches(Symbol.DECLARE):
        st.drop()
    else: return st.fail("A definition should begin with a '$'")
    if st.matches(Ident):
        d.append(st.take())
    else: return st.fail("No name given for definition")
    if st.matches(Symbol.EQUAL):
        st.drop()
    else: return st.fail("Expected an '=' sign following Def name")
    ok, res = parse_item_list(st)
    if ok:
        d.append(res)
    else: return st.fail("Parsing error in value", res)
    if st.matches(Symbol.SEMI):
        st.drop()
    else: return st.fail("Expected ';' at end of definition")
    return st.accept(Def, d)

class Target:
    def __init__(self, *args):
        print('Target', *args)

def parse_target(st):
    #   '(' Ident ')' ';'
    st.enter()
    d = []
    if st.matches(Symbol.OPENPAREN):
        st.drop()
    else: return st.fail("A target should start with '('")
    if st.matches(Ident):
        d.append(st.take())
    else: return st.fail("A target should have a name")
    if st.matches(Symbol.CLOSEPAREN):
        st.drop()
    else: return st.fail("A target should end with ')'")
    if st.matches(Symbol.SEMI):
        st.drop()
    else: return st.fail("Missing ';' terminator")
    return st.accept(Target, d)

def parse_item_list(st):
    # Either
    #   '{' Item ',' ... '}'
    #   Item
    st.enter()
    d = []
    if st.matches(Symbol.OPENBRACE):
        st.drop()
        while True:
            if st.matches(Symbol.CLOSEBRACE):
                st.drop()
                break
            ok, res = parse_item(st)
            if ok:
                d.append(res)
            else: return st.fail("Error trying to read an item", res)
            if st.matches(Symbol.COMMA):
                st.drop()
            elif st.matches(Symbol.CLOSEBRACE):
                st.drop()
                break
            else: return st.fail("Unexpected token in list")
    else:
        ok, res = parse_item(st)
        if ok: d.append(res)
        else: return st.fail("Parsing error in item", res)
    return st.accept(ItemList, d)

class Def:
    def __init__(self, *args):
        print('Def', *args)

class ItemList:
    def __init__(self, *args):
        print('ItemList', *args)

class Item:
    def __init__(self, *args):
        print('Item', *args)

class Expand:
    def __init__(self, *args):
        print('Expand', *args)

def parse_item(st):
    # Either
    #   Entry
    #   Entry '::' ItemList
    st.enter()
    d = []
    if st.matches(Symbol.DECLARE):
        st.drop()
        if st.matches(Ident):
            d.append(st.take())
            return st.accept(Expand, d)
        else: return st.fail("Expansion applies to an identifier")
    ok, res = parse_entry(st)
    if ok:
        d.append(res)
    else: return st.fail("Error while parsing entry", res)
    if st.matches(Symbol.SCOPE):
        st.drop()
        ok, res = parse_item_list(st)
        if ok:
            d.append(res)
        else: return st.fail("Error while parsing tail", res)
    return st.accept(Item, d)

def parse_entry(st):
    #   Ident
    # Followed by 0 or more Tag
    st.enter()
    d = []
    if st.matches(Ident):
        d.append(st.take())
    else: return st.fail("Item should have a name")
    while True:
        ok, res = parse_tag(st)
        if ok:
            d.append(res)
        elif ok is None:
            break
        else:
            return st.forward(ok, res)
    return st.accept(Entry, d)

class Tag:
    def __init__(self, *args):
        print('Tag', *args)

class Entry:
    def __init__(self, *args):
        print('Entry', *args)

class Label:
    def __init__(self, *args):
        print('Label', *args)

class Induce:
    def __init__(self, *args):
        print('Induce', *args)

class Depend:
    def __init__(self, *args):
        print('Depend', *args)

def parse_tag(st):
    # Either
    #   ':'
    #   '->'
    #   '<-'
    # Followed by
    #   Ident
    # Optionally followed by
    #   '(' Ident ',' ... ')'
    st.enter()
    d = []
    if st.matches(Symbol.COLON):
        sym = Label
    elif st.matches(Symbol.LEFT):
        sym = Induce
    elif st.matches(Symbol.RIGHT):
        sym = Depend
    else: return st.abort("Not a valid tag")
    if st.matches(Ident):
        d.append(st.take())
    else: return st.fail("Tag should have a name")
    ok, res = parse_params(st)
    if ok:
        d.append(res)
    else:
        return st.forward(ok, res)
    st.drop()
    return st.accept(sym, d)

class Params:
    def __init__(self, *args):
        print('Params', *args)

def parse_params(st):
    st.enter()
    d = []
    if st.matches(Symbol.OPENPAREN):
        st.drop()
        while True:
            if st.matches(Symbol.CLOSEPAREN):
                st.drop()
                break
            if st.matches(Ident):
                d.append(st.take())
            else: return st.fail("Expected an identifier")
            if st.matches(Symbol.COMMA):
                st.drop()
            elif st.matches(Symbol.CLOSEPAREN):
                st.drop()
                break
            else: return st.fail("Unexpected token in parameters")
    return st.accept(Params, d)

with open("new-lang", 'r') as f:
    print(tree_of_tokens(tokens_of_chars(chars_of_text(f.read()))))

