from typing import Union
import os

from libparse import (
    Error,
    Head,
    Loc,
    Maybe,
    Result,
    Span,
    Spanned,
    SpanResult,
    Stream,
)
from sylex_ast import *


class Unreachable(Exception):
    pass


Chars = Stream[str]


def chars_of_text(text: str) -> Chars:
    loc = Loc(0, 0)
    chars: Chars = Stream.empty()
    for c in text:
        chars.append(Span.unit(loc).with_data(c))
        if c == "\n":
            loc = loc.newline()
        else:
            loc = loc.newcol()
    return chars


Token = Union[Symbol, Ident]
Tokens = Stream[Token]
HToken = Head[Token]


class EOF:
    pass


def next_token(hd: Head[str]) -> Result[Union[Token, EOF, None]]:
    # About the return type
    #   Error -> something wrong happened
    #   EOF -> no more tokens
    #   None -> this is not a token, but next call may yield something again
    # None is used to simplify skipping over whitespace
    start = hd.span()
    read = hd.peek()
    if read is None:
        return EOF()
    if read.data == "<":
        # Left arrow
        # '<' '-'
        hd.bump()
        read = hd.peek()
        if read is not None and read.data == "-":
            return Symbol.LEFT
        else:
            return hd.err(
                "Unknown token", "'<' unterminated, expected '-' after", start
            )
    if read.data == "#":
        # Line comment
        # '#' [^'\n']* '\n'
        while True:
            read = hd.peek()
            if read is None:
                return EOF()
            if read.data == "\n":
                return None
            hd.bump()
        raise Unreachable()
    if read.data in [" ", "\n", "\t"]:
        # Whitespace
        return None
    if read.data == ":":
        # ':' ':'
        read1 = hd.peek(1)
        if read1 is not None and read1.data == ":":
            hd.bump()
            return Symbol.SCOPE
        # Else is a fallthrough: will be handled by 1-char symbols
    if read.data == "-":
        # '-' '>'
        read1 = hd.peek(1)
        if read1 is not None and read1.data == ">":
            hd.bump()
            return Symbol.RIGHT
        # Else is a fallthrough so that an identifier can still be caught
    # The following loop takes care of all 1-char symbols
    for sym in Symbol:
        if read.data == sym.value:
            return sym
    # Identifier contains 'a-z' or 'A-Z' or '-' '.' '_'
    # Can also take the form `'` ... `'` with escaped characters
    if isname(read.data):
        ident_chars = [read]
        while True:
            read = hd.peek(1)
            if read is None:
                break
            elif isname(read.data):
                hd.bump()
                ident_chars.append(read)
            else:
                break
        return Ident.concat(ident_chars)
    if read.data == "'":
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
            elif read.data == "\\":
                # escape next character
                hd.bump()
                read = hd.peek(1)
                if read is None:
                    return hd.err("Unterminated escape", "'\\' at end of file", start)
                ident_chars.append(read)
            elif read.data == "'":
                # end literal
                hd.bump()
                break
            else:
                # default is a single normal character
                hd.bump()
                ident_chars.append(read)
        return Ident.concat(ident_chars)
    else:
        return hd.err(
            "Unknown token", "character does not begin any valid token", start
        )


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
        if isinstance(res, EOF):
            break
        elif res is None:
            fwd.bump()
            hd.commit(fwd)
            continue
        elif isinstance(res, Error):
            inner = res
            if inner.extra is None:
                inner.extra = hd.until(fwd)
                print(hd.span(), fwd.span(), hd.until(fwd))
            return inner
        else:
            spanned = hd.until(fwd).with_data(res)
            toks.append(spanned)
            fwd.bump()
            hd.commit(fwd)
    return toks


# Convention: a parser should leave the head on the first character it can't parse


def ast_of_tokens(tokens: Tokens) -> SpanResult[DefList]:
    hd = Head.start(tokens)
    res: SpanResult[Maybe[DefList]] = hd.sub(parse_deflist)
    if isinstance(res, Error):
        return res
    else:
        if hd.peek() is None:  # reached EOF as expected
            return res.map(lambda x: x.data)
        else:
            return res.data.diagnostic


def parse_deflist(hd: HToken) -> Result[Maybe[DefList]]:
    # DefList := Def *
    start = hd.span()
    defs: list[Spanned[Def] | Spanned[Target]] = []
    err = Error("None", "nothing", None)
    while True:
        read = hd.peek()
        if read is None:
            break
        elif read.data == Symbol.DECLARE:
            item_def: SpanResult[Def] = hd.sub(parse_def)
            if isinstance(item_def, Error):
                return item_def
            print(item_def)
            defs.append(item_def)
        elif read.data == Symbol.OPENBRACK:
            item_target: SpanResult[Target] = hd.sub(parse_target)
            if isinstance(item_target, Error):
                return item_target
            print(item_target)
            defs.append(item_target)
        else:
            return hd.err("Unknown token", "expected '$' or '['", start)
    return Maybe(DefList(defs), err)


def parse_def(hd: HToken) -> Result[Def]:
    # Def := '$' Ident '=' ItemList ';'
    start = hd.span()
    # '$'
    read = hd.peek()
    if read is None or read.data != Symbol.DECLARE:
        return hd.err("Invalid Def", "expect a Def to start with a '$'", start)
    hd.bump()
    # Ident
    read = hd.peek()
    if read is None or not isinstance(read.data, Ident):
        return hd.err("Invalid Def", "'$' should be followed by a name", start)
    name: Spanned[Ident] = read.span.with_data(read.data)
    hd.bump()
    # '='
    read = hd.peek()
    if read is None or read.data != Symbol.EQUAL:
        return hd.err("Invalid Def", "expected an '=' sign", start)
    hd.bump()
    # ItemList
    val: SpanResult[ItemList] = hd.sub(parse_itemlist)
    if isinstance(val, Error):
        return val
    value = val
    # ';'
    read = hd.peek()
    if read is None or read.data != Symbol.SEMI:
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
    if read.data == Symbol.OPENBRACE:
        # Case of '{' Item ','* '}'
        hd.bump()
        # TODO: list[Spanned[Item|Expand]]
        lst: list[Spanned[Item] | Spanned[Expand]] = []
        latest_error = None
        while True:
            read = hd.peek()
            if read is None:
                return hd.err(
                    "Invalid ItemList", "EOF reached while trying to read a list", start
                )
            if read.data == Symbol.CLOSEBRACE:
                # Reached the closing '}'
                hd.bump()
                return ItemList(lst)
            # otherwise read an Item then maybe a ','
            # if no ',' then it has to stop afterwards
            item: SpanResult[Expand | Maybe[Item]] = hd.sub(parse_item)
            if isinstance(item, Error):
                return item
            # TODO: coercion
            if isinstance(item.data, Expand):
                lst.append(item.span.with_data(item.data))
            else:
                lst.append(item.span.with_data(item.data.data))
            read = hd.peek()
            if read is None:
                if latest_error is not None:
                    return latest_error
                return hd.err("Invalid ItemList", "unclosed '{' before EOF", start)
            if read.data == Symbol.COMMA:
                hd.bump()
            else:
                # No trailing comma, it should be the end
                read = hd.peek()
                if read is None or read.data != Symbol.CLOSEBRACE:
                    if latest_error is not None:
                        return latest_error
                    return hd.err(
                        "Invalid ItemList",
                        "expected '}' after no trailing comma",
                        start,
                    )
                # (next iteration will take care of actually returning)
    else:
        # did not start with a '{' so it should be a single Item
        obj: SpanResult[Expand | Maybe[Item]] = hd.sub(parse_item)
        if isinstance(obj, Error):
            return obj
        # TODO: coercion
        elif isinstance(obj.data, Expand):
            return ItemList([obj.span.with_data(obj.data)])
        else:
            return ItemList([obj.span.with_data(obj.data.data)])


def parse_item(hd: HToken) -> Result[Expand | Maybe[Item]]:
    # Item := '$' Ident
    #       | Entry
    #       | Entry '::' ItemList
    start = hd.span()
    # if it starts with a '$' then it's an expansion
    read = hd.peek()
    if read is not None and read.data == Symbol.DECLARE:
        hd.bump()
        read = hd.peek()
        if read is None or not isinstance(read.data, Ident):
            return hd.err("Invalid expansion", "expected identifier after '$'", start)
        hd.bump()
        ident: Spanned[Ident] = read.span.with_data(read.data)
        return Expand(ident)
    # otherwise it should be an Entry
    entry: SpanResult[Maybe[Entry]] = hd.sub(parse_entry)
    if isinstance(entry, Error):
        return entry
    # optionally '::' then ItemList
    read = hd.peek()
    if read is None or read.data != Symbol.SCOPE:
        return Maybe(Item(entry.map(lambda x: x.data), None), entry.data.diagnostic)
    hd.bump()
    tail: SpanResult[ItemList] = hd.sub(parse_itemlist)
    if isinstance(tail, Error):
        return tail
    return Maybe(Item(entry.map(lambda x: x.data), tail), entry.data.diagnostic)


def parse_entry(hd: HToken) -> Result[Maybe[Entry]]:
    # Entry := Ident Tag*
    start = hd.span()
    # Ident
    read = hd.peek()
    if read is None or not isinstance(read.data, Ident):
        return hd.err("Invalid Entry", "should start with an Ident", start)
    hd.bump()
    name: Spanned[Ident] = read.span.with_data(read.data)
    entry = Entry.from_name(name)
    # list of Tag
    while True:
        read = hd.peek()
        if read is None or read.data not in [Symbol.LEFT, Symbol.RIGHT, Symbol.COLON]:
            err = hd.err(
                "Expected tag marker",
                "tags should begin with '<-' or '->' or ':'",
                start,
            )
            return Maybe(entry, err)
        tag: SpanResult[Tag] = hd.sub(parse_tag)
        if isinstance(tag, Error):
            return tag
        entry.push(tag.span.with_data(tag.data))


def parse_tag(hd: HToken) -> Result[Tag]:
    start = hd.span()
    # '<-' or ':' or '->'
    read = hd.peek()
    if read is None or read.data not in [Symbol.LEFT, Symbol.RIGHT, Symbol.COLON]:
        return hd.err(
            "Invalid Tag", "should start with either ':', '<-' or '->'", start
        )
    hd.bump()
    symbol = read
    # Ident
    read = hd.peek()
    if read is None or not isinstance(read.data, Ident):
        return hd.err("Invalid Tag", "should have a name", start)
    name: Spanned[Ident] = read.span.with_data(read.data)
    hd.bump()
    # If there are params they start with '('
    read = hd.peek()
    if read is None or read.data != Symbol.OPENPAREN:
        params = hd.span().with_data(Params([]))
    else:
        read_params: SpanResult[Params] = hd.sub(parse_params)
        if isinstance(read_params, Error):
            return read_params
        else:
            params = read_params
    # decide type of return value depending on value of symbol
    if symbol.data == Symbol.COLON:
        return Label(name, params)
    elif symbol.data == Symbol.LEFT:
        return Induce(name, params)
    else:
        return Depend(name, params)


def parse_params(hd: HToken) -> Result[Params]:
    start = hd.span()
    # Start with '('
    read = hd.peek()
    if read is None or read.data != Symbol.OPENPAREN:
        return hd.err("Invalid Params", "should start with '('", start)
    hd.bump()
    inner: list[Spanned[Ident]] = []
    # Comma-separated list of Idents
    while True:
        read = hd.peek()
        if read is None:
            return hd.err("Invalid Params", "unclosed '(' at end of file", start)
        elif read.data == Symbol.CLOSEPAREN:
            hd.bump()
            return Params(inner)
        elif isinstance(read.data, Ident):
            hd.bump()
            inner.append(read.span.with_data(read.data))
            read = hd.peek()
            if read is None:
                return hd.err("Invalid Params", "unclosed '(' at end of file", start)
            if read.data == Symbol.COMMA:
                hd.bump()
            elif read.data != Symbol.CLOSEPAREN:
                return hd.err("Invalid Params", "expected ',' or ')'", start)
            # (next iteration will return)


def parse_target(hd: HToken) -> Result[Target]:
    # Target := '[' Ident ']' ';'
    start = hd.span()
    # '['
    read = hd.peek()
    if read is None or read.data != Symbol.OPENBRACK:
        return hd.err("Invalid Target", "should begin with '['", start)
    hd.bump()
    # Ident
    read = hd.peek()
    if read is None or not isinstance(read.data, Ident):
        return hd.err("Invalid Target", "should have a name", start)
    hd.bump()
    name = read.span.with_data(read.data)
    # ']'
    read = hd.peek()
    if read is None or read.data != Symbol.CLOSEBRACK:
        return hd.err("Invalid Target", "target name should be followed by ']'", start)
    hd.bump()
    # ';'
    read = hd.peek()
    if read is None or read.data != Symbol.SEMI:
        return hd.err("Invalid Target", "should be ended by ';'", start)
    hd.bump()
    return Target(name)


def main(fname: str) -> SpanResult[DefList]:
    if not os.path.exists(fname):
        return Error(
            "File not found", f"configuration file '{fname}' does not exist", None
        )
    with open(fname, "r") as f:
        text = f.read()
    chars = chars_of_text(text)
    toks = tokens_of_chars(chars)
    if isinstance(toks, Error):
        return toks
    ast = ast_of_tokens(toks)
    if isinstance(ast, Error):
        return ast
    return ast


if __name__ == "__main__":
    print(main("sylex.conf"))
