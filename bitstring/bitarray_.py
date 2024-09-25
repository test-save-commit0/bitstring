from __future__ import annotations
import copy
import numbers
import re
from collections import abc
from typing import Union, List, Iterable, Any, Optional
from bitstring import utils
from bitstring.exceptions import CreationError, Error
from bitstring.bits import Bits, BitsType, TBits
import bitstring.dtypes


class BitArray(Bits):
    """A container holding a mutable sequence of bits.

    Subclass of the immutable Bits class. Inherits all of its
    methods (except __hash__) and adds mutating methods.

    Mutating methods:

    append() -- Append a bitstring.
    byteswap() -- Change byte endianness in-place.
    clear() -- Remove all bits from the bitstring.
    insert() -- Insert a bitstring.
    invert() -- Flip bit(s) between one and zero.
    overwrite() -- Overwrite a section with a new bitstring.
    prepend() -- Prepend a bitstring.
    replace() -- Replace occurrences of one bitstring with another.
    reverse() -- Reverse bits in-place.
    rol() -- Rotate bits to the left.
    ror() -- Rotate bits to the right.
    set() -- Set bit(s) to 1 or 0.

    Methods inherited from Bits:

    all() -- Check if all specified bits are set to 1 or 0.
    any() -- Check if any of specified bits are set to 1 or 0.
    copy() -- Return a copy of the bitstring.
    count() -- Count the number of bits set to 1 or 0.
    cut() -- Create generator of constant sized chunks.
    endswith() -- Return whether the bitstring ends with a sub-string.
    find() -- Find a sub-bitstring in the current bitstring.
    findall() -- Find all occurrences of a sub-bitstring in the current bitstring.
    fromstring() -- Create a bitstring from a formatted string.
    join() -- Join bitstrings together using current bitstring.
    pp() -- Pretty print the bitstring.
    rfind() -- Seek backwards to find a sub-bitstring.
    split() -- Create generator of chunks split by a delimiter.
    startswith() -- Return whether the bitstring starts with a sub-bitstring.
    tobitarray() -- Return bitstring as a bitarray from the bitarray package.
    tobytes() -- Return bitstring as bytes, padding if needed.
    tofile() -- Write bitstring to file, padding if needed.
    unpack() -- Interpret bits using format string.

    Special methods:

    Mutating operators are available: [], <<=, >>=, +=, *=, &=, |= and ^=
    in addition to the inherited [], ==, !=, +, *, ~, <<, >>, &, | and ^.

    Properties:

    [GENERATED_PROPERTY_DESCRIPTIONS]

    len -- Length of the bitstring in bits.

    """
    __slots__ = ()
    __hash__: None = None

    def __init__(self, auto: Optional[Union[BitsType, int]]=None, /, length:
        Optional[int]=None, offset: Optional[int]=None, **kwargs) ->None:
        """Either specify an 'auto' initialiser:
        A string of comma separated tokens, an integer, a file object,
        a bytearray, a boolean iterable or another bitstring.

        Or initialise via **kwargs with one (and only one) of:
        bin -- binary string representation, e.g. '0b001010'.
        hex -- hexadecimal string representation, e.g. '0x2ef'
        oct -- octal string representation, e.g. '0o777'.
        bytes -- raw data as a bytes object, for example read from a binary file.
        int -- a signed integer.
        uint -- an unsigned integer.
        float / floatbe -- a big-endian floating point number.
        bool -- a boolean (True or False).
        se -- a signed exponential-Golomb code.
        ue -- an unsigned exponential-Golomb code.
        sie -- a signed interleaved exponential-Golomb code.
        uie -- an unsigned interleaved exponential-Golomb code.
        floatle -- a little-endian floating point number.
        floatne -- a native-endian floating point number.
        bfloat / bfloatbe - a big-endian bfloat format 16-bit floating point number.
        bfloatle -- a little-endian bfloat format 16-bit floating point number.
        bfloatne -- a native-endian bfloat format 16-bit floating point number.
        intbe -- a signed big-endian whole byte integer.
        intle -- a signed little-endian whole byte integer.
        intne -- a signed native-endian whole byte integer.
        uintbe -- an unsigned big-endian whole byte integer.
        uintle -- an unsigned little-endian whole byte integer.
        uintne -- an unsigned native-endian whole byte integer.
        filename -- the path of a file which will be opened in binary read-only mode.

        Other keyword arguments:
        length -- length of the bitstring in bits, if needed and appropriate.
                  It must be supplied for all integer and float initialisers.
        offset -- bit offset to the data. These offset bits are
                  ignored and this is intended for use when
                  initialising using 'bytes' or 'filename'.

        """
        if self._bitstore.immutable:
            self._bitstore = self._bitstore._copy()
            self._bitstore.immutable = False

    def copy(self: TBits) ->TBits:
        """Return a copy of the bitstring."""
        return BitArray(self)

    def __setattr__(self, attribute, value) ->None:
        try:
            super().__setattr__(attribute, value)
        except AttributeError:
            dtype = bitstring.dtypes.Dtype(attribute)
            x = object.__new__(Bits)
            if (set_fn := dtype.set_fn) is None:
                raise AttributeError(
                    f"Cannot set attribute '{attribute}' as it does not have a set_fn."
                    )
            set_fn(x, value)
            if len(x) != dtype.bitlength:
                raise CreationError(
                    f"Can't initialise with value of length {len(x)} bits, as attribute has length of {dtype.bitlength} bits."
                    )
            self._bitstore = x._bitstore
            return

    def __iadd__(self, bs: BitsType) ->BitArray:
        """Append bs to current bitstring. Return self.

        bs -- the bitstring to append.

        """
        self._append(bs)
        return self

    def __copy__(self) ->BitArray:
        """Return a new copy of the BitArray."""
        s_copy = BitArray()
        s_copy._bitstore = self._bitstore._copy()
        assert s_copy._bitstore.immutable is False
        return s_copy

    def __setitem__(self, key: Union[slice, int], value: BitsType) ->None:
        if isinstance(key, numbers.Integral):
            self._setitem_int(int(key), value)
        else:
            self._setitem_slice(key, value)

    def __delitem__(self, key: Union[slice, int]) ->None:
        """Delete item or range.

        >>> a = BitArray('0x001122')
        >>> del a[8:16]
        >>> print a
        0x0022

        """
        self._bitstore.__delitem__(key)
        return

    def __ilshift__(self: TBits, n: int) ->TBits:
        """Shift bits by n to the left in place. Return self.

        n -- the number of bits to shift. Must be >= 0.

        """
        if n < 0:
            raise ValueError('Cannot shift by a negative amount.')
        if not len(self):
            raise ValueError('Cannot shift an empty bitstring.')
        if not n:
            return self
        n = min(n, len(self))
        return self._ilshift(n)

    def __irshift__(self: TBits, n: int) ->TBits:
        """Shift bits by n to the right in place. Return self.

        n -- the number of bits to shift. Must be >= 0.

        """
        if n < 0:
            raise ValueError('Cannot shift by a negative amount.')
        if not len(self):
            raise ValueError('Cannot shift an empty bitstring.')
        if not n:
            return self
        n = min(n, len(self))
        return self._irshift(n)

    def __imul__(self: TBits, n: int) ->TBits:
        """Concatenate n copies of self in place. Return self.

        Called for expressions of the form 'a *= 3'.
        n -- The number of concatenations. Must be >= 0.

        """
        if n < 0:
            raise ValueError('Cannot multiply by a negative integer.')
        return self._imul(n)

    def __ior__(self: TBits, bs: BitsType) ->TBits:
        bs = self._create_from_bitstype(bs)
        self._bitstore |= bs._bitstore
        return self

    def __iand__(self: TBits, bs: BitsType) ->TBits:
        bs = self._create_from_bitstype(bs)
        self._bitstore &= bs._bitstore
        return self

    def __ixor__(self: TBits, bs: BitsType) ->TBits:
        bs = self._create_from_bitstype(bs)
        self._bitstore ^= bs._bitstore
        return self

    def replace(self, old: BitsType, new: BitsType, start: Optional[int]=
        None, end: Optional[int]=None, count: Optional[int]=None,
        bytealigned: Optional[bool]=None) ->int:
        """Replace all occurrences of old with new in place.

        Returns number of replacements made.

        old -- The bitstring to replace.
        new -- The replacement bitstring.
        start -- Any occurrences that start before this will not be replaced.
                 Defaults to 0.
        end -- Any occurrences that finish after this will not be replaced.
               Defaults to len(self).
        count -- The maximum number of replacements to make. Defaults to
                 replace all occurrences.
        bytealigned -- If True replacements will only be made on byte
                       boundaries.

        Raises ValueError if old is empty or if start or end are
        out of range.

        """
        if not old:
            raise ValueError("Empty bitstring to replace")
        
        start = 0 if start is None else start
        end = len(self) if end is None else end
        count = -1 if count is None else count

        if start < 0 or end > len(self) or start > end:
            raise ValueError("Invalid start or end values")

        old_bits = Bits(old)
        new_bits = Bits(new)
        replacements = 0
        pos = start

        while pos <= end - len(old_bits) and replacements != count:
            if bytealigned and pos % 8 != 0:
                pos += 1
                continue
            
            if self[pos:pos+len(old_bits)] == old_bits:
                self[pos:pos+len(old_bits)] = new_bits
                pos += len(new_bits)
                replacements += 1
            else:
                pos += 1

        return replacements

    def insert(self, bs: BitsType, pos: int) ->None:
        """Insert bs at bit position pos.

        bs -- The bitstring to insert.
        pos -- The bit position to insert at.

        Raises ValueError if pos < 0 or pos > len(self).

        """
        if pos < 0 or pos > len(self):
            raise ValueError("Invalid insertion position")
        
        bs_to_insert = Bits(bs)
        self._bitstore = self._bitstore[:pos] + bs_to_insert._bitstore + self._bitstore[pos:]

    def overwrite(self, bs: BitsType, pos: int) ->None:
        """Overwrite with bs at bit position pos.

        bs -- The bitstring to overwrite with.
        pos -- The bit position to begin overwriting from.

        Raises ValueError if pos < 0 or pos > len(self).

        """
        if pos < 0 or pos > len(self):
            raise ValueError("Invalid overwrite position")
        
        bs_to_write = Bits(bs)
        end = pos + len(bs_to_write)
        if end > len(self):
            self._bitstore = self._bitstore[:pos] + bs_to_write._bitstore
        else:
            self._bitstore = self._bitstore[:pos] + bs_to_write._bitstore + self._bitstore[end:]

    def append(self, bs: BitsType) ->None:
        """Append a bitstring to the current bitstring.

        bs -- The bitstring to append.

        """
        bs_to_append = Bits(bs)
        self._bitstore += bs_to_append._bitstore

    def prepend(self, bs: BitsType) ->None:
        """Prepend a bitstring to the current bitstring.

        bs -- The bitstring to prepend.

        """
        bs_to_prepend = Bits(bs)
        self._bitstore = bs_to_prepend._bitstore + self._bitstore

    def reverse(self, start: Optional[int]=None, end: Optional[int]=None
        ) ->None:
        """Reverse bits in-place.

        start -- Position of first bit to reverse. Defaults to 0.
        end -- One past the position of the last bit to reverse.
               Defaults to len(self).

        Using on an empty bitstring will have no effect.

        Raises ValueError if start < 0, end > len(self) or end < start.

        """
        if not self:
            return

        start = 0 if start is None else start
        end = len(self) if end is None else end

        if start < 0 or end > len(self) or end < start:
            raise ValueError("Invalid start or end values")

        reversed_section = self._bitstore[start:end][::-1]
        self._bitstore = self._bitstore[:start] + reversed_section + self._bitstore[end:]

    def set(self, value: Any, pos: Optional[Union[int, Iterable[int]]]=None
        ) ->None:
        """Set one or many bits to 1 or 0.

        value -- If bool(value) is True bits are set to 1, otherwise they are set to 0.
        pos -- Either a single bit position or an iterable of bit positions.
               Negative numbers are treated in the same way as slice indices.
               Defaults to the entire bitstring.

        Raises IndexError if pos < -len(self) or pos >= len(self).

        """
        bit_value = 1 if bool(value) else 0

        if pos is None:
            self._bitstore = BitArray([bit_value] * len(self))._bitstore
        elif isinstance(pos, int):
            if pos < -len(self) or pos >= len(self):
                raise IndexError("Bit position out of range")
            if pos < 0:
                pos = len(self) + pos
            self._bitstore[pos] = bit_value
        else:
            for p in pos:
                if p < -len(self) or p >= len(self):
                    raise IndexError("Bit position out of range")
                if p < 0:
                    p = len(self) + p
                self._bitstore[p] = bit_value

    def invert(self, pos: Optional[Union[Iterable[int], int]]=None) ->None:
        """Invert one or many bits from 0 to 1 or vice versa.

        pos -- Either a single bit position or an iterable of bit positions.
               Negative numbers are treated in the same way as slice indices.

        Raises IndexError if pos < -len(self) or pos >= len(self).

        """
        if pos is None:
            self._bitstore = ~self._bitstore
        elif isinstance(pos, int):
            if pos < -len(self) or pos >= len(self):
                raise IndexError("Bit position out of range")
            if pos < 0:
                pos = len(self) + pos
            self._bitstore[pos] = not self._bitstore[pos]
        else:
            for p in pos:
                if p < -len(self) or p >= len(self):
                    raise IndexError("Bit position out of range")
                if p < 0:
                    p = len(self) + p
                self._bitstore[p] = not self._bitstore[p]

    def ror(self, bits: int, start: Optional[int]=None, end: Optional[int]=None
        ) ->None:
        """Rotate bits to the right in-place.

        bits -- The number of bits to rotate by.
        start -- Start of slice to rotate. Defaults to 0.
        end -- End of slice to rotate. Defaults to len(self).

        Raises ValueError if bits < 0.

        """
        if bits < 0:
            raise ValueError("Cannot rotate by a negative amount")

        start = 0 if start is None else start
        end = len(self) if end is None else end

        if start < 0 or end > len(self) or start >= end:
            raise ValueError("Invalid start or end values")

        if bits == 0 or start == end:
            return

        slice_len = end - start
        bits = bits % slice_len  # Normalize rotation amount

        if bits == 0:
            return

        rotated = self._bitstore[end-bits:end] + self._bitstore[start:end-bits]
        self._bitstore = self._bitstore[:start] + rotated + self._bitstore[end:]

    def rol(self, bits: int, start: Optional[int]=None, end: Optional[int]=None
        ) ->None:
        """Rotate bits to the left in-place.

        bits -- The number of bits to rotate by.
        start -- Start of slice to rotate. Defaults to 0.
        end -- End of slice to rotate. Defaults to len(self).

        Raises ValueError if bits < 0.

        """
        if bits < 0:
            raise ValueError("Cannot rotate by a negative amount")

        start = 0 if start is None else start
        end = len(self) if end is None else end

        if start < 0 or end > len(self) or start >= end:
            raise ValueError("Invalid start or end values")

        if bits == 0 or start == end:
            return

        slice_len = end - start
        bits = bits % slice_len  # Normalize rotation amount

        if bits == 0:
            return

        rotated = self._bitstore[start+bits:end] + self._bitstore[start:start+bits]
        self._bitstore = self._bitstore[:start] + rotated + self._bitstore[end:]

    def byteswap(self, fmt: Optional[Union[int, Iterable[int], str]]=None,
        start: Optional[int]=None, end: Optional[int]=None, repeat: bool=True
        ) ->int:
        """Change the endianness in-place. Return number of repeats of fmt done.

        fmt -- A compact structure string, an integer number of bytes or
               an iterable of integers. Defaults to 0, which byte reverses the
               whole bitstring.
        start -- Start bit position, defaults to 0.
        end -- End bit position, defaults to len(self).
        repeat -- If True (the default) the byte swapping pattern is repeated
                  as much as possible.

        """
        start = 0 if start is None else start
        end = len(self) if end is None else end

        if start < 0 or end > len(self) or start > end:
            raise ValueError("Invalid start or end values")

        if fmt is None or fmt == 0:
            fmt = [8] * ((end - start) // 8)
        elif isinstance(fmt, int):
            fmt = [8] * fmt
        elif isinstance(fmt, str):
            fmt = [int(x) * 8 for x in fmt.split(',') if x]
        
        fmt = [f for f in fmt if f % 8 == 0]  # Ensure all chunks are byte-aligned
        if not fmt:
            return 0

        chunk_size = sum(fmt)
        if chunk_size == 0:
            return 0

        repeats = 0
        pos = start
        while pos + chunk_size <= end:
            for size in fmt:
                byte_size = size // 8
                byte_data = self._bitstore[pos:pos+size].tobytes()
                swapped_data = byte_data[::-1]
                self._bitstore[pos:pos+size] = BitArray(bytes=swapped_data)
                pos += size
            repeats += 1
            if not repeat:
                break

        return repeats

    def clear(self) ->None:
        """Remove all bits, reset to zero length."""
        self._bitstore = BitArray()
