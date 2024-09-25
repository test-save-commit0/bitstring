import array
import math
import struct
import bitarray
from bitstring.luts import mxfp_luts_compressed
import zlib
from typing import Optional


class MXFPFormat:
    """Defining an MXFP micro-scaling floating point format"""

    def __init__(self, exp_bits: int, mantissa_bits: int, bias: int,
        mxfp_overflow: str):
        self.exp_bits = exp_bits
        self.mantissa_bits = mantissa_bits
        self.bias = bias
        self.mxfp_overflow = mxfp_overflow
        self.pos_clamp_value = (1 << self.exp_bits + self.mantissa_bits) - 1
        self.neg_clamp_value = (1 << 1 + self.exp_bits + self.mantissa_bits
            ) - 1
        if self.exp_bits == 4 and self.mantissa_bits == 3:
            if self.mxfp_overflow == 'saturate':
                self.pos_clamp_value = 126
                self.neg_clamp_value = 254
            else:
                self.pos_clamp_value = self.neg_clamp_value = 255
        if self.exp_bits == 5 and self.mantissa_bits == 2:
            if self.mxfp_overflow == 'saturate':
                self.pos_clamp_value = 123
                self.neg_clamp_value = 251
            else:
                self.pos_clamp_value = 124
                self.neg_clamp_value = 252
        self.lut_float16_to_mxfp = None
        self.lut_int_to_float = None

    def __str__(self):
        return (
            f"MXFPFormat(exp_bits={self.exp_bits}, mantissa_bits={self.mantissa_bits}, bias={self.bias}, mxfp_overflow='{self.mxfp_overflow}')"
            )

    def float_to_int(self, f: float) ->int:
        """Given a Python float convert to the best mxfp float (expressed as an int) that represents it."""
        if math.isnan(f):
            return (1 << (self.exp_bits + self.mantissa_bits + 1)) - 1  # All ones for NaN
        
        if f == 0:
            return 0  # Zero is represented as all zeros
        
        sign = 1 if f < 0 else 0
        f = abs(f)
        
        # Handle infinity and large numbers
        if math.isinf(f) or f >= 2 ** (2 ** self.exp_bits - self.bias):
            if self.mxfp_overflow == 'saturate':
                return self.neg_clamp_value if sign else self.pos_clamp_value
            else:  # overflow
                return self.neg_clamp_value if sign else self.pos_clamp_value
        
        # Find the exponent
        exp = math.floor(math.log2(f))
        exp = max(exp, 1 - self.bias)  # Handle subnormals
        
        # Calculate mantissa
        mantissa = int(round((f / (2 ** exp) - 1) * (2 ** self.mantissa_bits)))
        
        # Adjust for bias
        exp += self.bias
        
        # Combine sign, exponent, and mantissa
        result = (sign << (self.exp_bits + self.mantissa_bits)) | (exp << self.mantissa_bits) | mantissa
        
        return result

    def createLUT_for_int_to_float(self) ->array.array:
        """Create a LUT to convert an int in representing a MXFP float into a Python float"""
        lut = array.array('f')
        for i in range(1 << (self.exp_bits + self.mantissa_bits + 1)):
            sign = -1 if i & (1 << (self.exp_bits + self.mantissa_bits)) else 1
            exp = (i >> self.mantissa_bits) & ((1 << self.exp_bits) - 1)
            mantissa = i & ((1 << self.mantissa_bits) - 1)
            
            if exp == 0 and mantissa == 0:
                lut.append(0.0)
            elif exp == (1 << self.exp_bits) - 1:
                if mantissa == 0:
                    lut.append(float('inf') if sign > 0 else float('-inf'))
                else:
                    lut.append(float('nan'))
            else:
                value = sign * (1 + mantissa / (2 ** self.mantissa_bits)) * (2 ** (exp - self.bias))
                lut.append(value)
        
        return lut

    def createLUT_for_float16_to_mxfp(self) ->bytes:
        """Create a LUT to convert a float16 into a MXFP format"""
        lut = bytearray(65536)
        for i in range(65536):
            f16 = struct.unpack('!e', struct.pack('!H', i))[0]
            mxfp = self.float_to_int(f16)
            lut[i] = mxfp
        return bytes(lut)


e2m1mxfp_fmt = MXFPFormat(exp_bits=2, mantissa_bits=1, bias=1,
    mxfp_overflow='saturate')
e2m3mxfp_fmt = MXFPFormat(exp_bits=2, mantissa_bits=3, bias=1,
    mxfp_overflow='saturate')
e3m2mxfp_fmt = MXFPFormat(exp_bits=3, mantissa_bits=2, bias=3,
    mxfp_overflow='saturate')
e4m3mxfp_saturate_fmt = MXFPFormat(exp_bits=4, mantissa_bits=3, bias=7,
    mxfp_overflow='saturate')
e5m2mxfp_saturate_fmt = MXFPFormat(exp_bits=5, mantissa_bits=2, bias=15,
    mxfp_overflow='saturate')
e4m3mxfp_overflow_fmt = MXFPFormat(exp_bits=4, mantissa_bits=3, bias=7,
    mxfp_overflow='overflow')
e5m2mxfp_overflow_fmt = MXFPFormat(exp_bits=5, mantissa_bits=2, bias=15,
    mxfp_overflow='overflow')
