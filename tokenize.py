import tokstream as toks
from tokstream import Phantom
from enum import Enum
import ast

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

def tokens_of_chars(chars):
    st = toks.Stream(chars)
    l = []
    while True:
        for s in ast.Symbol:
            if st.matches(*[c for c in s.value]):
                l.append(st.take().replace(s))
        if st.matches('#'):
            while st.matches(lambda c: c != '\n'):
                pass
            st.drop()
        elif st.matches('\n') or st.matches('\t') or st.matches(' '):
            st.drop()
        elif st.matches(ast.isname):
            while st.matches(ast.isname):
                pass
            l.append(st.take(ast.Ident.concat))
        elif st.matches(Phantom("'")):
            while True:
                if st.matches(Phantom('\\'), str):
                    pass
                elif st.matches(Phantom("'")):
                    l.append(st.take(ast.Ident.concat))
                    break
                elif st.matches(str):
                    pass
                else: # reached EOF
                    raise NotImplementedError("Reached EOF during string literal")
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

@toks.Stream.subproc_exc
def parse_def_list(st):
    latest = None
    while True:
        print("AAAAAAAAAA", latest)
        try:
            res = parse_target(st)
            st.register(res)
            continue
        except toks.ParsingFailure as e:
            latest = e
        try:
            res = parse_def(st)
            st.register(res)
            continue
        except toks.ParsingFailure as e:
            latest = e
        break
    if st.matches(toks.EOS):
        return st.accept(ast.DefList)
    else:
        return st.fail("Expected EOF", latest)

@toks.Stream.subproc_exc
def parse_def(st):
    #   '$' Ident '=' ItemList ';'
    st.assert_matches(Phantom(ast.Symbol.DECLARE), failure="A definition should begin with a '$'")
    st.take_register()
    st.assert_matches(ast.Ident, failure="No name given for definition")
    st.take_register()
    st.assert_matches(Phantom(ast.Symbol.EQUAL), failure="Expected an '=' sign following Def name")
    st.take_register()
    res = st.sub(parse_item_list, failure="Parsing error in value")
    st.register(res)
    st.assert_matches(Phantom(ast.Symbol.SEMI), failure="Expected ';' at end of definition")
    st.take_register()
    return st.accept(ast.Def)

@toks.Stream.subproc_exc
def parse_target(st):
    #   '(' Ident ')' ';'
    if st.matches(Phantom(ast.Symbol.OPENPAREN)):
        st.take_register()
    else: return st.fail("A target should start with '('")
    if st.matches(ast.Ident):
        st.take_register()
    else: return st.fail("A target should have a name")
    if st.matches(Phantom(ast.Symbol.CLOSEPAREN)):
        st.take_register()
    else: return st.fail("A target should end with ')'")
    if st.matches(Phantom(ast.Symbol.SEMI)):
        st.take_register()
    else: return st.fail("Missing ';' terminator")
    return st.accept(ast.Target)

@toks.Stream.subproc_exc
def parse_item_list(st):
    # Either
    #   '{' Item ',' ... '}'
    #   Item
    if st.matches(Phantom(ast.Symbol.OPENBRACE)):
        st.take_register()
        while True:
            if st.matches(Phantom(ast.Symbol.CLOSEBRACE)):
                st.take_register()
                break
            ok, res = parse_item(st)
            if ok:
                st.register(res)
            else: return st.fail("Error trying to read an item", res)
            if st.matches(Phantom(ast.Symbol.COMMA)):
                st.take_register()
            elif st.matches(Phantom(ast.Symbol.CLOSEBRACE)):
                st.take_register()
                break
            else: return st.fail("Unexpected token in list")
    else:
        ok, res = parse_item(st)
        if ok:
            st.register(res)
        else: return st.fail("Parsing error in item", res)
    return st.accept(ast.ItemList)

@toks.Stream.subproc
def parse_item(st):
    # Either
    #   Entry
    #   Entry '::' ItemList
    if st.matches(Phantom(ast.Symbol.DECLARE)):
        st.take_register()
        if st.matches(ast.Ident):
            st.take_register()
            return st.accept(ast.Expand)
        else: return st.fail("Expansion applies to an identifier")
    ok, res = parse_entry(st)
    if ok:
        st.register(res)
    else: return st.fail("Error while parsing entry", res)
    if st.matches(Phantom(ast.Symbol.SCOPE)):
        st.take_register()
        try:
            res = parse_item_list(st)
            st.register(res)
        except ParsingFailure as res:
            return st.fail(res.msg, res.peek, res.child)
    return st.accept(ast.Item)

@toks.Stream.subproc
def parse_entry(st):
    #   Ident
    # Followed by 0 or more Tag
    d = []
    if st.matches(ast.Ident):
        st.take_register()
    else: return st.fail("Item should have a name")
    while True:
        ok, res = parse_tag(st)
        if ok:
            st.register(res)
        else:
            break
    return st.accept(ast.Entry)

@toks.Stream.subproc
def parse_tag(st):
    # Either
    #   ':'
    #   '->'
    #   '<-'
    # Followed by
    #   Ident
    # Optionally followed by
    #   '(' Ident ',' ... ')'
    if st.matches(Phantom(ast.Symbol.COLON)):
        sym = ast.Label
    elif st.matches(Phantom(ast.Symbol.LEFT)):
        sym = ast.Induce
    elif st.matches(Phantom(ast.Symbol.RIGHT)):
        sym = ast.Depend
    else: return st.fail("Not a valid tag")
    st.take_register()
    if st.matches(ast.Ident):
        st.take_register()
    else: return st.fail("Tag should have a name")
    ok, res = parse_params(st)
    if ok:
        st.register(res)
    else:
        return st.fail(res.msg, res.peek, res.child)
    #st.take_register()
    return st.accept(sym)

@toks.Stream.subproc
def parse_params(st):
    if st.matches(Phantom(ast.Symbol.OPENPAREN)):
        st.take_register()
        while True:
            if st.matches(Phantom(ast.Symbol.CLOSEPAREN)):
                st.take_register()
                break
            if st.matches(ast.Ident):
                st.take_register()
            else: return st.fail("Expected an identifier")
            if st.matches(Phantom(ast.Symbol.COMMA)):
                st.take_register()
            elif st.matches(Phantom(ast.Symbol.CLOSEPAREN)):
                st.take_register()
                break
            else: return st.fail("Unexpected token in parameters")
    return st.accept(ast.Params)

