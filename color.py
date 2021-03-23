import bpy
from bpy.props import FloatVectorProperty, FloatProperty

def RGB(rgb):
    c = Color()
    c.setRGB(rgb)
    return c

def from16bits(H):
    c = Color()
    c.from16bits(H)
    return c


class Color:
    def White(self):
        self.setRGBA(255, 255, 255, 255)
        return self
    def Black(self):
        self.setRGBA(0, 0, 0, 255)
        return self

    def __init__(self):
        self.R = 0
        self.G = 0
        self.B = 0
        self.A = 0
        self.L = 0  # Light value, 0 is the darkest, 255 the lightest
        self.code = "00000000"

    def __repr__(self):
        return "(COLOR : " + repr(self.code) + ")"

    def setRGB(self, rgb):
        self.R = rgb[0]
        self.G = rgb[1]
        self.B = rgb[2]
        self.A = 255
        self.update()
        return self

    def setRGBA(self, r, g, b, a):
        self.R = r
        self.G = g
        self.B = b
        self.A = a
        self.update()
        return self

    def from16bits(self, H):
        # H must be 2bytes long
        b = (H & 0x7C00) >> 10
        g = (H & 0x03E0) >> 5
        r = H & 0x001F
        self.R = int(r * 8)
        self.G = int(g * 8)
        self.B = int(b * 8)
        if H == 0:
            self.A = 0  # transparent
        else:
            self.A = 255  # opaque
        self.update()
        return self

    def fromFloat(self, r, g, b, a):
        self.R = r * 255
        self.G = g * 255
        self.B = b * 255
        self.A = a * 255
        self.update()
        return self

    def toBytearray(self):
        return bytearray([self.R, self.G, self.B, self.A])

    def toRGBA(self):
        return [self.R, self.G, self.B, self.A]

    def toFloat(self):
        return [self.R / 255, self.G / 255, self.B / 255, self.A / 255]

    def to32bits(self):
        return "{:02X}{:02X}{:02X}{:02X}".format(
            round(self.R), round(self.G), round(self.B), round(self.A)
        )

    def to16bits(self):
        # here we compress the color from 4bytes value into 2bytes (16bits : 1bit for alpha + 5bits * R, G and B channels)
        a = 0
        if self.A > 0:
            a = 1
        binstr = "{:01b}{:05b}{:05b}{:05b}".format(
            a, round(self.B / 8), round(self.G / 8), round(self.R / 8)
        )
        # for a certain reason i'm always 0x0080 bytes more than original, maybe a matter of round
        hexv = int(binstr, 2)
        # hexv -= 0x0080
        hexstr = "{:04X}".format(hexv)
        # print("binstr : "+repr(binstr)+"   ---   "+"hexstr : "+repr(hexstr))
        return hexstr

    def update(self):
        self.code = self.to32bits()
        self.L = self.R + self.G + self.B + self.A
        
White = Color().White()
Black = Color().Black()

def Grey(inc):
    c = Color()
    inc = inc*17
    c.setRGBA(inc, inc, inc, 255)
    return c


GreyCLUT = [Black, Grey(1), Grey(2), Grey(3), Grey(4), Grey(5), Grey(6), Grey(7), Grey(8), Grey(9), Grey(10), Grey(11), Grey(12), Grey(13), Grey(14), White]