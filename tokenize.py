import tokstream as toks

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

def idem(x):
    return x

def tokens_of_chars(chars):
    st = toks.Stream(chars)
    l = []
    while True:
        if st.matches('#'):
            while st.matches(lambda c: c != '\n'):
                pass
            st.drop()
        elif st.matches('\n') or st.matches('\t') or st.matches(' '):
            st.drop()
        elif any(st.matches(*[c for c in s])
            for s in [
                '$', '=', '{', '}', ',', ';',
                '::', ':', '->', '<-', '(', ')',
            ]):
                l.append(st.take(concat))
        elif st.matches(isname):
            while st.matches(isname):
                pass
            l.append(st.take(concat))
        elif st.matches(toks.EOS):
            l.append(st.take(idem))
            break
        else:
            raise NotImplementedError(",".join(f"{t}" for t in st.toks[st.head:]))
            print(f"head: {st.head}")
    return l


with open("new-lang", 'r') as f:
    print(tokens_of_chars(chars_of_text(f.read())))

