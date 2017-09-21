import string

from pyparsing import (
    Literal, White, Word, CharsNotIn, Forward, Group, SkipTo, Optional,
    ZeroOrMore, pythonStyleComment, QuotedString, Keyword,
    alphanums, alphas)


class NginxParser(object):
    """
    A class that parses nginx configuration with pyparsing
    """
    sq_string = QuotedString("'", multiline=True, unquoteResults=False)
    dq_string = QuotedString('"', multiline=True, unquoteResults=False)
    qstring = sq_string | dq_string
    key = Word(alphas, alphanums+"\_/")
    space = White().suppress()
    value = CharsNotIn(string.whitespace + ";{")
    semi = Literal(';').suppress()
    left_bracket = Literal("{").suppress()
    right_bracket = Literal("}").suppress()

    modifier = Literal("=") | Literal("~*") | Literal("~") | Literal("^~")

    doc = Forward()
    if_block = Forward()
    location_block = Forward()

    block = left_bracket + Group(doc) + right_bracket

    assignment = (
            Optional(space) + key + ZeroOrMore(space + (qstring | value)) +
            (semi | block))

    if_block << (
        Keyword("if") + SkipTo('{')
        + left_bracket
        + Group(doc)
        + right_bracket)

    location_block << (
        Keyword("location") + Optional(space + modifier) + SkipTo('{')
        + left_bracket
        + Group(doc)
        + right_bracket)

    command = Group(if_block | location_block | assignment)

    doc << ZeroOrMore(command).ignore(pythonStyleComment)
    script = doc

    def __init__(self, source):
        self.source = source

    def parse(self):
        """
        Returns the parsed tree.
        """
        return self.script.parseString(self.source)

    def as_list(self):
        """
        Returns the list of tree.
        """
        return self.parse().asList()


class NginxDumper(object):
    """
    A class that dumps nginx configuration from the provided tree.
    """
    def __init__(self, blocks, indentation=4):
        self.blocks = blocks
        self.indentation = indentation

    def dumpstr(self, blocks=None, indent=0, spacer=' '):
        blocks = blocks or self.blocks
        assert(isinstance(blocks, list))

        parts = []
        indent_str = indent * self.indentation * spacer
        for cmd in blocks:
            last = cmd[-1]
            if isinstance(last, list):
                # current cmd is a block cmd
                block_str = '\n'.join([
                    '{',
                    self.dumpstr(last, indent=indent+1),
                    indent_str + '}'])
                part = indent_str + spacer.join(cmd[:-1]) + block_str
                parts.append(part)
            else:
                # simple cmd
                parts.append(indent_str + spacer.join(cmd) + ';')
        return '\n'.join(parts)

    def as_string(self):
        return self.dumpstr()

    def to_file(self, out):
        lines = self.dumpstr()
        out.write(lines)
        out.close()
        return out


# Shortcut functions to respect Python's serialization interface
# (like pyyaml, picker or json)

def loads(source):
    return NginxParser(source).as_list()


def load(_file):
    return loads(_file.read())


def dumps(blocks, indentation=4):
    return NginxDumper(blocks, indentation).as_string()


def dump(blocks, _file, indentation=4):
    return NginxDumper(blocks, indentation).to_file(_file)
