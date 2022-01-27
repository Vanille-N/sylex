import libparse as lib
import sylex_ast as ast
import typing as ty

Chars = lib.Stream[str]

def chars_of_text(text: str) -> Chars:
    loc = lib.Loc(0, 0)
    chars: Chars = lib.Stream.empty()
    for c in text:
        chars.append(lib.Span.unit(loc).with_data(c))
        if c == '\n':
            loc = loc.newline()
        else:
            loc = loc.newcol()
    return chars

Token = ty.Union[ast.Symbol, ast.Ident]
Tokens = lib.Stream[Token]

class EOF:
    pass

def next_token(hd: lib.Head[str]) -> lib.Result[Token, ty.Union[lib.Error, EOF, None]]:
    read = hd.peek()
    if read is None:
        return lib.Wrong(EOF())
    if read.data == '<':
        hd.bump()
        read = hd.peek()
        if read is not None and read.data == '-':
            return ast.Symbol.LEFT
        else:
            return hd.err("Unknown token", "'<' unterminated, expected '-' after")
    if read.data == '#':
        while True:
            read = hd.peek()
            if read is None:
                return lib.Wrong(EOF())
            if read.data == '\n':
                return lib.Wrong(None)
            hd.bump()
    if read.data in [' ', '\n', '\t']:
        return lib.Wrong(None)
    if read.data == ':':
        read = hd.peek(1)
        print("Colon ? ", hd.peek(), hd.peek(1))
        if read is not None and read.data == ':':
            hd.bump()
            return ast.Symbol.SCOPE
        # Else is a fallthrough: will be handled by 1-char symbols
    if read.data == "-":
        read = hd.peek(1)
        if read is not None and read.data == '>':
            hd.bump()
            return ast.Symbol.RIGHT
        # Else is a fallthrough so that an identifier can still be caught
    # The following loop takes care of all 1-char symbols
    for sym in ast.Symbol:
        if read.data == sym.value:
            return sym
    if ast.isname(read.data):
        ident_chars = [read]
        while True:
            read = hd.peek(1)
            if read is None:
                break
            elif ast.isname(read.data):
                hd.bump()
                ident_chars.append(read)
            else:
                break
        return ast.Ident.concat(ident_chars)
    if read.data == "'":
        ident_chars = []
        while True:
            read = hd.peek(1)
            if read is None:
                return hd.err("Unterminated literal", "`'` opened but unclosed before end of file")
            elif read.data == "'":
                hd.bump()
                break
            else:
                hd.bump()
                ident_chars.append(read)
        return ast.Ident.concat(ident_chars)
    else:
        return hd.err("Unknown token", "character does not begin any valid token")
    raise NotImplementedError(hd.peek())


def tokens_of_chars(chars: Chars) -> lib.Result[Tokens, lib.Error]:
    toks: Tokens = lib.Stream.empty()
    hd = lib.Head.start(chars)
    while True:
        fwd = hd.clone()
        print(f"Enter: {fwd.peek()}")
        res: lib.Result[Token, lib.Error|EOF|None] = next_token(fwd)
        print(f"Exit: {fwd.peek()}")
        print(f"With: {res}")
        print()
        if isinstance(res, lib.Wrong):
            if isinstance(res.inner, EOF):
                break
            elif res.inner is None:
                fwd.bump()
                hd.commit(fwd)
                continue
            else:
                inner = res.inner
                assert isinstance(inner, lib.Error)
                if inner.span is None:
                    inner.span = hd.until(fwd)
                    print(hd.span(), fwd.span(), hd.until(fwd))
                return lib.Wrong(inner)
        else:
            spanned = hd.until(fwd).with_data(res)
            toks.append(spanned)
            fwd.bump()
            hd.commit(fwd)
    return toks

def ast_of_tokens(tokens: Tokens) -> lib.Result[lib.Spanned[ast.DefList], lib.Error]:
    hd = lib.Head.start(tokens)
    res: lib.Result[lib.Spanned[lib.Maybe[ast.DefList]], lib.Error] = hd.sub(parse_deflist)
    if isinstance(res, lib.Wrong):
        return res
    else:
        assert isinstance(res.data, lib.Maybe)
        if hd.peek() is None: # reached EOF as expected
            return res.map(lambda x: x.data)
        else:
            return lib.Wrong(res.data.diagnostic)

def parse_deflist(hd: lib.Head[Token]) -> lib.Result[lib.Maybe[ast.DefList], lib.Error]:
    defs: list[ast.Spanned[ast.Def|ast.Target]] = []
    err = lib.Error("None", "nothing", None)
    while True:
        read = hd.peek()
        if read is None:
            break
        elif read.data == ast.Symbol.DECLARE:
            item_def: lib.Result[lib.Spanned[ast.Def], lib.Error] = hd.sub(parse_def)
            raise NotImplementedError("Handle Def")
        elif read.data == ast.Symbol.OPENPAREN:
            item_target: lib.Result[lib.Spanned[ast.Target], lib.Error] = hd.sub(parse_target)
            raise NotImplementedError("Handle Target")
    return lib.Maybe(ast.DefList(defs), err)

def parse_def(hd: lib.Head[Token]) -> lib.Result[ast.Def, lib.Error]:
    pass

def parse_target(hd: lib.Head[Token]) -> lib.Result[ast.Target, lib.Error]:
    pass

def main():
    with open("../new-lang") as f:
        text = f.read()
    chars = chars_of_text(text)
    print(chars)
    toks = tokens_of_chars(chars)
    if isinstance(toks, lib.Error):
        print(toks)
        return
    print('\n'.join(map(str, toks)))
    print("="*15)
    ast = ast_of_tokens(toks)
    if isinstance(ast, lib.Error):
        print(ast)
        return
    print(ast)

if __name__ == "__main__":
    main()
