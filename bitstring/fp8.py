"""
The 8-bit float formats used here are from a proposal supported by Graphcore, AMD and Qualcomm.
See https://arxiv.org/abs/2206.02915

"""
import struct
import zlib
import array
import bitarray
from bitstring.luts import binary8_luts_compressed
import math


class Binary8Format:
    """8-bit floating point formats based on draft IEEE binary8"""

    def __init__(self, exp_bits: int, bias: int):
        self.exp_bits = exp_bits
        self.bias = bias
        self.pos_clamp_value = 127
        self.neg_clamp_value = 255

    def __str__(self):
        return f'Binary8Format(exp_bits={self.exp_bits}, bias={self.bias})'

    def float_to_int8(self, f: float) ->int:
        """Given a Python float convert to the best float8 (expressed as an integer in 0-255 range)."""
        if math.isnan(f):
            return 0  # NaN is represented as 0 in this format
        
        if f == 0:
            return 0 if math.copysign(1, f) == 1 else 128  # Handle +0 and -0
        
        if f > 0 and f >= 2 ** (self.pos_clamp_value - self.bias):
            return self.pos_clamp_value  # Positive infinity or too large positive number
        
        if f < 0 and f <= -2 ** (self.neg_clamp_value - 128 - self.bias):
            return self.neg_clamp_value  # Negative infinity or too large negative number
        
        sign = 0 if f > 0 else 128
        f = abs(f)
        
        exponent = math.floor(math.log2(f)) + self.bias
        mantissa = round((f / (2 ** (exponent - self.bias)) - 1) * (2 ** (8 - self.exp_bits)))
        
        if mantissa == 2 ** (8 - self.exp_bits):
            exponent += 1
            mantissa = 0
        
        if exponent < 0:
            exponent = 0
            mantissa = 1
        elif exponent >= 2 ** self.exp_bits - 1:
            exponent = 2 ** self.exp_bits - 1
            mantissa = 0
        
        return sign | (exponent << (8 - self.exp_bits)) | mantissa

    def createLUT_for_binary8_to_float(self):
        """Create a LUT to convert an int in range 0-255 representing a float8 into a Python float"""
        lut = []
        for i in range(256):
            sign = -1 if i & 128 else 1
            exponent = (i >> (8 - self.exp_bits)) & ((1 << self.exp_bits) - 1)
            mantissa = i & ((1 << (8 - self.exp_bits)) - 1)
            
            if exponent == 0:
                if mantissa == 0:
                    value = 0.0
                else:
                    value = sign * (mantissa / (2 ** (8 - self.exp_bits))) * (2 ** (1 - self.bias))
            elif exponent == (2 ** self.exp_bits) - 1:
                if mantissa == 0:
                    value = float('inf') if sign == 1 else float('-inf')
                else:
                    value = float('nan')
            else:
                value = sign * (1 + mantissa / (2 ** (8 - self.exp_bits))) * (2 ** (exponent - self.bias))
            
            lut.append(value)
        
        return lut


p4binary_fmt = Binary8Format(exp_bits=4, bias=8)
p3binary_fmt = Binary8Format(exp_bits=5, bias=16)
