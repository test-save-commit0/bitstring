from __future__ import annotations
import functools
import re
from typing import Tuple, List, Optional, Pattern, Dict, Union, Match
NAME_INT_RE: Pattern[str] = re.compile('^([a-zA-Z][a-zA-Z0-9_]*?):?(\\d*)$')
NAME_KWARG_RE: Pattern[str] = re.compile(
    '^([a-zA-Z][a-zA-Z0-9_]*?):?([a-zA-Z0-9_]+)$')
CACHE_SIZE = 256
DEFAULT_BITS: Pattern[str] = re.compile('^(?P<len>[^=]+)?(=(?P<value>.*))?$',
    re.IGNORECASE)
MULTIPLICATIVE_RE: Pattern[str] = re.compile('^(?P<factor>.*)\\*(?P<token>.+)')
LITERAL_RE: Pattern[str] = re.compile('^(?P<name>0([xob]))(?P<value>.+)',
    re.IGNORECASE)
STRUCT_PACK_RE: Pattern[str] = re.compile(
    '^(?P<endian>[<>@=])(?P<fmt>(?:\\d*[bBhHlLqQefd])+)$')
BYTESWAP_STRUCT_PACK_RE: Pattern[str] = re.compile(
    '^(?P<endian>[<>@=])?(?P<fmt>(?:\\d*[bBhHlLqQefd])+)$')
SINGLE_STRUCT_PACK_RE: Pattern[str] = re.compile(
    '^(?P<endian>[<>@=])(?P<fmt>[bBhHlLqQefd])$')
STRUCT_SPLIT_RE: Pattern[str] = re.compile('\\d*[bBhHlLqQefd]')
REPLACEMENTS_BE: Dict[str, str] = {'b': 'int8', 'B': 'uint8', 'h':
    'intbe16', 'H': 'uintbe16', 'l': 'intbe32', 'L': 'uintbe32', 'q':
    'intbe64', 'Q': 'uintbe64', 'e': 'floatbe16', 'f': 'floatbe32', 'd':
    'floatbe64'}
REPLACEMENTS_LE: Dict[str, str] = {'b': 'int8', 'B': 'uint8', 'h':
    'intle16', 'H': 'uintle16', 'l': 'intle32', 'L': 'uintle32', 'q':
    'intle64', 'Q': 'uintle64', 'e': 'floatle16', 'f': 'floatle32', 'd':
    'floatle64'}
REPLACEMENTS_NE: Dict[str, str] = {'b': 'int8', 'B': 'uint8', 'h':
    'intne16', 'H': 'uintne16', 'l': 'intne32', 'L': 'uintne32', 'q':
    'intne64', 'Q': 'uintne64', 'e': 'floatne16', 'f': 'floatne32', 'd':
    'floatne64'}
PACK_CODE_SIZE: Dict[str, int] = {'b': 1, 'B': 1, 'h': 2, 'H': 2, 'l': 4,
    'L': 4, 'q': 8, 'Q': 8, 'e': 2, 'f': 4, 'd': 8}


def structparser(m: Match[str]) ->List[str]:
    """Parse struct-like format string token into sub-token list."""
    endian = m.group('endian')
    fmt = m.group('fmt')
    tokens = []
    
    if endian == '>':
        replacements = REPLACEMENTS_BE
    elif endian == '<':
        replacements = REPLACEMENTS_LE
    else:
        replacements = REPLACEMENTS_NE
    
    for match in STRUCT_SPLIT_RE.finditer(fmt):
        code = match.group()
        if code[0] in '0123456789':
            count = int(code[:-1])
            token = replacements[code[-1]]
            tokens.extend([token] * count)
        else:
            tokens.append(replacements[code])
    
    return tokens


@functools.lru_cache(CACHE_SIZE)
def tokenparser(fmt: str, keys: Tuple[str, ...]=()) ->Tuple[bool, List[
    Tuple[str, Union[int, str, None], Optional[str]]]]:
    """Divide the format string into tokens and parse them.

    Return stretchy token and list of [initialiser, length, value]
    initialiser is one of: hex, oct, bin, uint, int, se, ue, 0x, 0o, 0b etc.
    length is None if not known, as is value.

    If the token is in the keyword dictionary (keys) then it counts as a
    special case and isn't messed with.

    tokens must be of the form: [factor*][initialiser][:][length][=value]

    """
    tokens = []
    stretchy_token = False
    fmt = expand_brackets(fmt)
    
    for token in fmt.split(','):
        token = token.strip()
        if token in keys:
            tokens.append((token, None, None))
            continue
        
        mobj = MULTIPLICATIVE_RE.match(token)
        if mobj:
            factor = int(mobj.group('factor'))
            token = mobj.group('token')
        else:
            factor = 1
        
        mobj = NAME_INT_RE.match(token)
        if mobj:
            name, length = mobj.group(1), mobj.group(2)
            if length:
                length = int(length)
            else:
                length = None
            if name == 'pad':
                if length is None:
                    stretchy_token = True
            tokens.extend([(name, length, None)] * factor)
            continue
        
        mobj = DEFAULT_BITS.match(token)
        if mobj:
            name = 'bits'
            length = mobj.group('len')
            if length:
                length = int(length)
            else:
                length = None
            value = mobj.group('value')
            if length is None and value is None:
                stretchy_token = True
            tokens.extend([(name, length, value)] * factor)
            continue
        
        mobj = LITERAL_RE.match(token)
        if mobj:
            name = mobj.group('name').lower()
            value = mobj.group('value')
            length = len(value) * {'0b': 1, '0o': 3, '0x': 4}[name]
            tokens.extend([(name, length, value)] * factor)
            continue
        
        raise ValueError(f"Don't understand token '{token}' in format string")
    
    return stretchy_token, tokens


BRACKET_RE = re.compile('(?P<factor>\\d+)\\*\\(')


def expand_brackets(s: str) ->str:
    """Expand all brackets."""
    while True:
        match = BRACKET_RE.search(s)
        if not match:
            break
        factor = int(match.group('factor'))
        start = match.start()
        end = s.index(')', start)
        sub = s[start + len(match.group()):end]
        s = s[:start] + ','.join([sub] * factor) + s[end + 1:]
    return s
