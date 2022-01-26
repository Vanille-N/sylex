from enum import Enum

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

def indent(text):
    return '\n'.join('    ' + line for line in text.split('\n'))

class Ident:
    def __init__(self, name):
        self.name = name

    def concat(*s):
        print(s)
        return Ident(''.join(c.data for c in s))

    def __str__(self):
        return f"'{self.name}'"

class DefList:
    def __init__(self, *defs):
        self.defs = defs

    def __str__(self):
        return "DefList {\n" + '\n'.join(indent(d.__str__()) for d in self.defs) + "\n}"

class Target:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return f"Target {self.name}"

class Def:
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __str__(self):
        return f"Def {self.name} := " + self.value.__str__()

class ItemList:
    def __init__(self, *items):
        self.items = items

    def __str__(self):
        return "ItemList {\n" + '\n'.join(indent(i.__str__()) for i in self.items) + "\n}"

class Item:
    def __init__(self, entry, tail=None):
        self.entry = entry
        self.tail = tail

    def __str__(self):
        if self.tail is None:
            return f"Leaf ({self.entry})"
        else:
            return f"Branch ({self.entry}) :: \n" + indent(self.tail.__str__())

class Expand:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return f"Expand({self.name})"

class Tag:
    def __init__(self, name, params):
        self.name = name
        self.params = params

    def __str__(self):
        return f"Tag({self.name}:{','.join(p.__str__() for p in self.params)})"

class Entry:
    def __init__(self, name, *markers):
        self.name = name
        self.label = []
        self.induce = []
        self.depend = []
        for mk in markers:
            if type(mk.data) == Induce: self.induce.append(mk)
            elif type(mk.data) == Label: self.label.append(mk)
            elif type(mk.data) == Depend: self.depend.append(mk)
            else: raise TypeError(f"{mk} of type {type(mk)} is not a valid entry marker")
        print(self.__str__())

    def __str__(self):
        s = f"Entry({self.name})"
        for m in self.label + self.induce + self.depend:
            s += '\n' + indent(f"{m}")
        return s

class Label:
    def __init__(self, name, params):
        self.name = name
        self.params = params

    def __str__(self):
        return f"Label({self.name})\n  {self.params}"

class Induce:
    def __init__(self, name, params):
        self.name = name
        self.params = params

    def __str__(self):
        return f"Induce({self.name})\n  {self.params}"


class Depend:
    def __init__(self, name, params):
        self.name = name
        self.params = params

    def __str__(self):
        return f"Depend({self.name})\n  {self.params}"

class Params:
    def __init__(self, *vals):
        self.vals = vals

    def __str__(self):
        return "Params(" + ",".join(f"{v}" for v in self.vals) + ")"

