from os import path

from libparse import Error, Head, Loc, Maybe, Result, Span, Spanned, SpanResult, Stream, Text
from typing import Callable, TypeVar
from sylex_ast import *

Chars = Stream[str]


def chars_of_raw(raw: str) -> Chars:
    text = Text(raw)
    loc = Loc(0, 0)
    chars: Chars = Stream.empty()
    for c in raw:
        chars.append(Span.unit(loc, text).with_data(c))
        if c == "\n":
            loc = loc.newline()
        else:
            loc = loc.newcol()
    return chars


class Blank:
    pass


Token = Symbol | Ident
Tokens = Stream[Token]
HToken = Head[Token]


def next_token(hd: Head[str]) -> Result[Token | Blank | None]:
    # About the return type
    #   Error -> something wrong happened
    #   None -> no more tokens
    #   Blank -> this is whitespace
    start = hd.span()
    read = hd.take()
    if read is None:
        return None

    if read == "<":
        # Left arrow
        # '<' '-'
        hd.bump()
        read = hd.peek()
        if read == "-":
            _ = hd.take()
            return Symbol.LEFT
        return hd.err("Unknown token", "'<' unterminated, expected '-' after", start)

    if read == "#":
        # Line comment
        # '#' [^'\n']* '\n'
        while True:
            hd.bump()
            read = hd.take()
            if read is None:
                return None
            if read == "\n":
                return Blank()

    if read in [" ", "\n", "\t"]:
        # Whitespace
        return Blank()

    if read == ":":
        # ':' ':'
        read1 = hd.peek(1)
        if read1 == ":":
            _ = hd.take(1)
            hd.bump()
            return Symbol.SCOPE
        # Else is a fallthrough: will be handled by 1-char symbols

    if read == "-":
        # '-' '>'
        read1 = hd.peek(1)
        if read1 == ">":
            _ = hd.take(1)
            hd.bump()
            return Symbol.RIGHT
        # Else is a fallthrough so that an identifier can still be caught

    # The following loop takes care of all 1-char symbols
    for sym in Symbol:
        if read == sym.value:
            return sym

    # Identifier contains 'a-z' or 'A-Z' or '-' '.' '_'
    # Can also take the form `'` ... `'` with escaped characters
    if isname(read):
        ident_chars = [read]
        while True:
            read = hd.peek(1)
            if read is None:
                break
            if not isname(read):
                break
            _ = hd.take(1)
            hd.bump()
            ident_chars.append(read)
        return Ident.concat(ident_chars)

    if read != "'":
        return hd.err(
            "Unknown token", "character does not begin any valid token", start
        )

    ident_chars = []
    while True:
        read = hd.peek(1)
        if read is None:
            # premature EOF
            return hd.err(
                "Unterminated literal",
                "`'` opened but unclosed before end of file",
                start,
            )
        if read == "\\":
            # escape next character
            hd.bump()
            read = hd.peek(1)
            if read is None:
                return hd.err("Unterminated escape", "'\\' at end of file", start)
            ident_chars.append(read)
        elif read == "'":
            # end literal
            hd.bump()
            break
        else:
            # default is a single normal character
            hd.bump()
            ident_chars.append(read)

    return Ident.concat(ident_chars)


def tokens_of_chars(chars: Chars) -> Result[Tokens]:
    # Call next_token repeatedly until the whole stream is consumed
    toks: Tokens = Stream.empty()
    hd = Head.start(chars)

    while True:
        fwd = hd.clone()
        print(f"Enter: {fwd.peek()}")
        res = next_token(fwd)
        print(f"Exit: {fwd.peek()}")
        print(f"With: {res}")
        print()

        if isinstance(res, Error):
            inner = res
            if inner.extra is None:
                inner.extra = hd.until(fwd)
                print(hd.span(), fwd.span(), hd.until(fwd))
            return inner

        if res is None:
            break

        elif isinstance(res, Blank):
            fwd.bump()
            hd.commit(fwd)
            continue

        else:
            spanned = hd.until(fwd).with_data(res)
            toks.append(spanned)
            fwd.bump()
            hd.commit(fwd)

    return toks


U = TypeVar("U")
def ast_of_tokens(tokens: Tokens, target: Callable[[HToken], Result[U]]) -> SpanResult[U]:
    hd = Head.start(tokens)
    start = hd.span()
    res: SpanResult[DefList] = hd.sub(target)
    read = hd.peek()
    if read is None:
        return res
    else:
        return Error("Extra text", f"expected end of file, found {read}", hd.until(start))
    return res


def parse_deflist(hd: HToken) -> Result[DefList]:
    # DefList := Def *
    start = hd.span()
    defs: list[Spanned[Def] | Spanned[Target]] = []
    while True:
        read = hd.peek()
        if read is None:
            break
        elif read == Symbol.DECLARE:
            item_def: SpanResult[Def] = hd.sub(parse_def)
            if isinstance(item_def, Error):
                return item_def
            print(item_def)
            defs.append(item_def)
        elif read == Symbol.OPENBRACK:
            item_target: SpanResult[Target] = hd.sub(parse_target)
            if isinstance(item_target, Error):
                return item_target
            print(item_target)
            defs.append(item_target)
        else:
            return hd.err("Unknown token", "expected '$' or '['", start)
    return DefList(defs)


def parse_def(hd: HToken) -> Result[Def]:
    # Def := '$' Ident '=' ItemList ';'
    start = hd.span()

    # '$'
    read = hd.take()
    if read != Symbol.DECLARE:
        return hd.err("Invalid Def", "expect a Def to start with a '$'", start)
    hd.bump()

    # Ident
    read = hd.take()
    if not isinstance(read, Ident):
        return hd.err("Invalid Def", "'$' should be followed by a name", start)

    # TODO: Waiting mypy 0.940
    name: Spanned[Ident] = hd.span().with_data(read)
    hd.bump()

    # '='
    read = hd.take()
    if read != Symbol.EQUAL:
        return hd.err("Invalid Def", "expected an '=' sign", start)
    hd.bump()

    # ItemList
    val: SpanResult[ItemList] = hd.sub(parse_itemlist)
    if isinstance(val, Error):
        return val
    value = val

    # ';'
    read = hd.take()
    if read != Symbol.SEMI:
        return hd.err("Invalid Def", "expected ';' at the end", start)
    hd.bump()

    return Def(name, value)


def parse_itemlist(hd: HToken) -> Result[ItemList]:
    # ItemList := '{' Item ','* '}'
    #           | Item
    start = hd.span()
    read = hd.peek()
    if read is None:
        return hd.err(
            "Invalid ItemList", "EOF reached while trying to read a list", start
        )

    if read != Symbol.OPENBRACE:
        # did not start with a '{' so it should be a single Item
        obj: SpanResult[Expand | Maybe[Item]] = hd.sub(parse_item)
        if isinstance(obj, Error):
            return obj

        # TODO: Waiting mypy 0.940
        if isinstance(obj.data, Expand):
            return ItemList([obj.span.with_data(obj.data)])
        else:
            return ItemList([obj.span.with_data(obj.data.data)])

    # Case of '{' Item ','* '}'
    _ = hd.take()
    hd.bump()
    # TODO: list[Spanned[Item|Expand]]
    lst: list[Spanned[Item | Expand]] = []
    latest_error = None
    while True:
        read = hd.peek()
        if read is None:
            return hd.err(
                "Invalid ItemList", "EOF reached while trying to read a list", start
            )
        if read == Symbol.CLOSEBRACE:
            # Reached the closing '}'
            _ = hd.take()
            hd.bump()
            return ItemList(lst)
        # otherwise read an Item then maybe a ','
        # if no ',' then it has to stop afterwards
        item: SpanResult[Expand | Maybe[Item]] = hd.sub(parse_item)
        if isinstance(item, Error):
            return item

        # TODO: Waiting mypy 0.940
        if isinstance(item.data, Expand):
            data: Expand | Item = item.data
        else:
            data = item.data.data
        lst.append(item.span.with_data(data))

        read = hd.peek()
        if read is None:
            if latest_error is not None:
                return latest_error
            return hd.err("Invalid ItemList", "unclosed '{' before EOF", start)
        if read == Symbol.COMMA:
            _ = hd.take()
            hd.bump()
        else:
            # No trailing comma, it should be the end
            if read != Symbol.CLOSEBRACE:
                if latest_error is not None:
                    return latest_error
                return hd.err(
                    "Invalid ItemList",
                    "expected '}' after no trailing comma",
                    start,
                )
            # (next iteration will take care of actually returning)


def parse_item(hd: HToken) -> Result[Expand | Maybe[Item]]:
    # Item := '$' Ident
    #       | Entry
    #       | Entry '::' ItemList
    start = hd.span()
    # if it starts with a '$' then it's an expansion
    read = hd.peek()
    if read == Symbol.DECLARE:
        _ = hd.take()
        hd.bump()
        read = hd.take()
        if not isinstance(read, Ident):
            return hd.err("Invalid expansion", "expected identifier after '$'", start)

        # TODO: Waiting mypy 0.940
        ident: Spanned[Ident] = hd.span().with_data(read)
        hd.bump()
        return Expand(ident)

    # otherwise it should be an Entry
    entry: SpanResult[Maybe[Entry]] = hd.sub(parse_entry)
    if isinstance(entry, Error):
        return entry
    # optionally '::' then ItemList
    read = hd.peek()
    if read != Symbol.SCOPE:
        return Maybe(Item(entry.map(lambda x: x.data), None), entry.data.diagnostic)
    _ = hd.take()
    hd.bump()
    tail: SpanResult[ItemList] = hd.sub(parse_itemlist)
    if isinstance(tail, Error):
        return tail
    return Maybe(Item(entry.map(lambda x: x.data), tail), entry.data.diagnostic)


def parse_entry(hd: HToken) -> Result[Maybe[Entry]]:
    # Entry := Ident Tag*
    start = hd.span()
    # Ident
    read = hd.take()
    if not isinstance(read, Ident):
        return hd.err("Invalid Entry", "should start with an Ident", start)

    # TODO: Waiting mypy 0.940
    name: Spanned[Ident] = hd.span().with_data(read)
    hd.bump()

    entry = Entry.from_name(name)
    # list of Tag
    while True:
        print(f"next: {hd.peek()}")
        read = hd.peek()
        if read not in [Symbol.LEFT, Symbol.RIGHT, Symbol.COLON]:
            err = hd.err(
                "Expected tag marker",
                f"tags should begin with '<-' or '->' or ':', not '{hd.peek()}'",
                start,
            )
            return Maybe(entry, err)
        tag: SpanResult[Tag] = hd.sub(parse_tag)
        if isinstance(tag, Error):
            return tag
        entry.push(tag)


def parse_tag(hd: HToken) -> Result[Tag]:
    start = hd.span()
    # '<-' or ':' or '->'
    read = hd.take()
    if read not in [Symbol.LEFT, Symbol.RIGHT, Symbol.COLON]:
        return hd.err(
            "Invalid Tag", "should start with either ':', '<-' or '->'", start
        )
    symbol = read
    hd.bump()

    # Ident
    read = hd.take()
    if not isinstance(read, Ident):
        return hd.err("Invalid Tag", "should have a name", start)

    # TODO: Waiting mypy 0.940
    name: Spanned[Ident] = hd.span().with_data(read)
    hd.bump()

    # If there are params they start with '('
    read = hd.peek()
    if read != Symbol.OPENPAREN:
        params = hd.span().with_data(Params([]))
    else:
        read_params: SpanResult[Params] = hd.sub(parse_params)
        if isinstance(read_params, Error):
            return read_params
        else:
            params = read_params
    # decide type of return value depending on value of symbol
    if symbol == Symbol.COLON:
        return Label(name, params)
    elif symbol == Symbol.LEFT:
        return Induce(name, params)
    else:
        return Depend(name, params)


def parse_params(hd: HToken) -> Result[Params]:
    start = hd.span()
    # Start with '('
    read = hd.take()
    if read != Symbol.OPENPAREN:
        return hd.err("Invalid Params", "should start with '('", start)
    hd.bump()
    inner: list[Spanned[Ident]] = []
    # Comma-separated list of Idents
    while True:
        read = hd.take()
        if read is None:
            return hd.err("Invalid Params", "unclosed '(' at end of file", start)

        if read == Symbol.CLOSEPAREN:
            hd.bump()
            return Params(inner)

        if isinstance(read, Ident):
            # TODO: Waiting mypy 0.940
            inner.append(hd.span().with_data(read))
            hd.bump()

            read = hd.peek()
            if read is None:
                return hd.err("Invalid Params", "unclosed '(' at end of file", start)
            if read == Symbol.COMMA:
                _ = hd.take()
                hd.bump()
            elif read != Symbol.CLOSEPAREN:
                return hd.err("Invalid Params", "expected ',' or ')'", start)

        # (next iteration will return)


def parse_target(hd: HToken) -> Result[Target]:
    # Target := '[' Ident ']' ';'
    start = hd.span()
    # '['
    read = hd.take()
    if read != Symbol.OPENBRACK:
        return hd.err("Invalid Target", "should begin with '['", start)
    hd.bump()

    # Ident
    read = hd.take()
    if not isinstance(read, Ident):
        return hd.err("Invalid Target", "should have a name", start)

    # TODO: Waiting mypy 0.940
    name = hd.span().with_data(read)
    hd.bump()

    # ']'
    read = hd.take()
    if read != Symbol.CLOSEBRACK:
        return hd.err("Invalid Target", "target name should be followed by ']'", start)
    hd.bump()

    # ';'
    read = hd.take()
    if read != Symbol.SEMI:
        return hd.err("Invalid Target", "should be ended by ';'", start)
    hd.bump()

    return Target(name)

def main(raw: str, target: Callable[[HToken], Result[U]]) -> SpanResult[U]:
    chars = chars_of_raw(raw)
    toks = tokens_of_chars(chars)
    if isinstance(toks, Error):
        return toks
    ast = ast_of_tokens(toks, target)
    if isinstance(ast, Error):
        return ast
    return ast


if __name__ == "__main__":
    with open("sylex.conf") as f:
        raw = f.read()
    print(main(raw, parse_deflist))
