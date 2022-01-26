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

def next_token(hd: lib.Head[str]) -> ty.Union[lib.Error, Token, EOF, None]:
    read = hd.peek()
    if read is None:
        return EOF()
    if read.data == '<':
        hd.bump()
        read = hd.peek()
        if read is None:
            return hd.err("Unknown token", "'<' unterminated, expected '-' after")
        if read.data == '-':
            return ast.Symbol.LEFT
        else:
            return hd.err("Unknown token", "'<' should be followed by '-'")
    if read.data == '#':
        while True:
            read = hd.peek()
            if read is None:
                return EOF()
            if read.data == '\n':
                return None
            hd.bump()
    if read.data in [' ', '\n', '\t']:
        return None
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
            if ast.isname(read.data):
                hd.bump()
                ident_chars.append(read)
            else:
                break
        return ast.Ident.concat(ident_chars)
    raise NotImplementedError(hd.peek())


def tokens_of_chars(chars: Chars) -> lib.Result[Tokens]:
    toks: Tokens = lib.Stream.empty()
    hd = lib.Head.start(chars)
    while True:
        fwd = hd.clone()
        print(f"Enter: {fwd.peek()}")
        res = next_token(fwd)
        print(f"Exit: {fwd.peek()}")
        print(f"With: {res}")
        print()
        if isinstance(res, EOF):
            break
        elif isinstance(res, lib.Error):
            return res
        else:
            if res is not None:
                spanned = hd.until(fwd).with_data(res)
                toks.append(spanned)
            fwd.bump()
            hd.commit(fwd)
    return toks


if __name__ == "__main__":
    with open("../new-lang") as f:
        text = f.read()
    chars = chars_of_text(text)
    print(chars)
    toks = tokens_of_chars(chars)
    print('\n'.join(map(str, toks)))

