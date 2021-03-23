import struct
from . import VS

def parse(file, numVertices, groups):
    print("parsing "+repr(numVertices)+" vertices...")
    vertices = []
    g = 0
    for i in range(0, numVertices):
        if i >= groups[g].numVertices:
            g = g + 1

        vertex = Vertex()
        vertex.group = groups[g]
        vertex.bone = vertex.group.bone
        vertex.feed(file, i)
        vertex.x -= vertex.bone.decalage() # hack for translating bones
        #print(vertex)
        vertices.append(vertex)
    return vertices

class Vertex:
    def __init__(self):
        self.group = None
        self.bone = None
        self.x = 0
        self.y = 0
        self.z = 0
        self.w = 0  # always 00
        self.index = -1

    def __repr__(self):
        return "(VERTEX : " + " index = "+ repr(self.index)+ " [x:"+ repr(self.x)+ ", y:"+ repr(self.y)+ ", z:"+ repr(self.z)+ ", w:"+ repr(self.w)+ "] )"

    def feed(self, file, i):
        self.index = i
        self.x, self.y, self.z, self.w = struct.unpack("4h", file.read(8))

    def tobin(self):
        return struct.pack("4h", self.x, self.y, self.z, self.w)

    def binsize(self):
        return 8

    def setGXYZ(self, _g, _x, _y, _z):
        self.group = _g
        self.x = _x
        self.y = _y
        self.z = _z
        return self

    def reverse(self):
        self.x = -self.x
        self.y = -self.y
        self.z = -self.z

    def swapYnZ(self):
        _y = self.y
        _z = -self.z
        self.y = _z
        self.z = _y

    def vector(self):
        return (self.x / VS.VERTEX_RATIO, self.y / VS.VERTEX_RATIO, self.z / VS.VERTEX_RATIO)
    def blenderSwaped(self):
        return (self.x / VS.VERTEX_RATIO, self.z / VS.VERTEX_RATIO, -self.y / VS.VERTEX_RATIO)