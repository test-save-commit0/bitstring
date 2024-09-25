from __future__ import annotations
import bitstring
from bitstring.bitstream import BitStream
from bitstring.utils import tokenparser
from bitstring.exceptions import CreationError
from typing import Union, List
from bitstring.bitstore import BitStore
from bitstring.bitstore_helpers import bitstore_from_token


def pack(fmt: Union[str, List[str]], *values, **kwargs) ->BitStream:
    """Pack the values according to the format string and return a new BitStream.

    fmt -- A single string or a list of strings with comma separated tokens
           describing how to create the BitStream.
    values -- Zero or more values to pack according to the format.
    kwargs -- A dictionary or keyword-value pairs - the keywords used in the
              format string will be replaced with their given value.

    Token examples: 'int:12'    : 12 bits as a signed integer
                    'uint:8'    : 8 bits as an unsigned integer
                    'float:64'  : 8 bytes as a big-endian float
                    'intbe:16'  : 2 bytes as a big-endian signed integer
                    'uintbe:16' : 2 bytes as a big-endian unsigned integer
                    'intle:32'  : 4 bytes as a little-endian signed integer
                    'uintle:32' : 4 bytes as a little-endian unsigned integer
                    'floatle:64': 8 bytes as a little-endian float
                    'intne:24'  : 3 bytes as a native-endian signed integer
                    'uintne:24' : 3 bytes as a native-endian unsigned integer
                    'floatne:32': 4 bytes as a native-endian float
                    'hex:80'    : 80 bits as a hex string
                    'oct:9'     : 9 bits as an octal string
                    'bin:1'     : single bit binary string
                    'ue' / 'uie': next bits as unsigned exp-Golomb code
                    'se' / 'sie': next bits as signed exp-Golomb code
                    'bits:5'    : 5 bits as a bitstring object
                    'bytes:10'  : 10 bytes as a bytes object
                    'bool'      : 1 bit as a bool
                    'pad:3'     : 3 zero bits as padding

    >>> s = pack('uint:12, bits', 100, '0xffe')
    >>> t = pack(['bits', 'bin:3'], s, '111')
    >>> u = pack('uint:8=a, uint:8=b, uint:55=a', a=6, b=44)

    """
    if isinstance(fmt, list):
        fmt = ','.join(fmt)

    tokens, _ = tokenparser(fmt)
    bitstring_list = []
    value_index = 0

    for token in tokens:
        if '=' in token[1]:
            name, token_str = token[1].split('=')
            value = kwargs.get(name.strip())
            if value is None:
                raise CreationError(f"Keyword '{name.strip()}' not provided")
        else:
            if value_index >= len(values):
                raise CreationError("Not enough values provided")
            value = values[value_index]
            value_index += 1
            token_str = token[1]

        try:
            bs = bitstore_from_token(token_str, value)
            bitstring_list.append(bs)
        except ValueError as e:
            raise CreationError(str(e))

    if value_index < len(values):
        raise CreationError("Too many values provided")

    result = BitStream()
    for bs in bitstring_list:
        result.append(bs)

    return result
