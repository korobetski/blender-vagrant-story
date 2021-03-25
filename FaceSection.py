bl_info = {
    "name": "Vagrant Story file formats Add-on",
    "description": "Import-Export Vagrant Story file formats (WEP, SHP, SEQ, ZUD, MPD, ZND).",
    "author": "Sigfrid Korobetski (LunaticChimera)",
    "version": (2, 0),
    "blender": (2, 92, 0),
    "location": "File > Import-Export",
    "category": "Import-Export",
}

import struct
from . import color, VertexSection

def parse(file, numFaces):
    print("parsing "+repr(numFaces)+" faces...")
    faces = []
    coloredVertices = False
    for i in range(0, numFaces):
        face = Face()
        face.default()
        face.feed(file, i, coloredVertices)
        # if a face use vertex color so the next will do the same
        if face.isColored == True:
            coloredVertices = True
        print(face)
        faces.append(face)
    return faces

def hasColoredVertex(faces):
    for face in faces:
        if face.isColored == True:
            return True
    return False

class Face:
    def __init__(self):
        self.index = 0
        self.type = 0
        self.size = 0
        self.side = 0
        self.flag = 0
        self.verticesCount = 0
        self.vertices = []
        self.uv = []
        self.colors = []
        self.isColored = False

    def default(self):
        self.index = 0
        self.type = 0
        self.size = 0
        # one of these unknown flag is maybe the vertice order
        self.side = 0  # 4 = normal, 5 double sided ?
        self.flag = 0  # unknown
        self.verticesCount = 3
        self.vertices = []
        self.uv = []
        self.colors = []
        self.isColored = False

    def __repr__(self):
        return "(FACE : "+" index = "+ repr(self.index)+ " type = "+ repr(self.type)+ " size = "+ repr(self.size)+ " side = "+ repr(self.side)+ " flag = "+repr(self.flag)+ " vertices = "+repr(self.vertices)+ ")"

    def feed(self, file, i, vc=False):
        self.index = i
        self.type, self.size, self.side, self.flag = struct.unpack("4B", file.read(4))
        if vc == False and (self.type == 0x24 or self.type == 0x2C):
            if self.type == 0x24:  # 0x34 is v colored tri
                self.verticesCount = 3
            elif self.type == 0x2C:  # 0x3C is v colored quad
                self.verticesCount = 4
            for i in range(0, self.verticesCount):
                vidx = struct.unpack("H", file.read(2))[0]
                vidx = int(vidx / 4)
                self.vertices.append(vidx)
            for i in range(0, self.verticesCount):
                self.uv.append(struct.unpack("2B", file.read(2)))
                self.colors.append(color.White)
        else:
            # handle v colored faces for special SHP so we need to back in the file
            self.isColored = True
            file.seek(file.tell() - 4)
            # Triangle vt1  vt2  vt3  u1-v1 col1  t  col2   sz col3   sd u2-v2  u3-v3
            # Quad     vt1  vt2  vt3  vt4   col1  t  col2   sz col3   sd col4   pa u1-v1 u2-v2 u3-v3 u4-v4
            self.colors = []
            vIdx = struct.unpack("4H", file.read(8))
            self.colors.append(color.RGB(struct.unpack("3B", file.read(3))))
            self.type = struct.unpack("B", file.read(1))[0]
            self.colors.append(color.RGB(struct.unpack("3B", file.read(3))))
            self.size = struct.unpack("B", file.read(1))[0]
            self.colors.append(color.RGB(struct.unpack("3B", file.read(3))))
            self.side = struct.unpack("B", file.read(1))[0]
            if self.type == 0x34:
                self.verticesCount = 3
                for i in range(0, 3):
                    self.vertices.append(int(vIdx[i] / 4))
                # uv1 at the same place of vt4 for quads
                self.uv.append((vIdx[3]).to_bytes(2, "little"))
                self.uv.append(struct.unpack("2B", file.read(2)))
                self.uv.append(struct.unpack("2B", file.read(2)))
            elif self.type == 0x3C:
                self.verticesCount = 4
                self.colors.append(color.RGB(struct.unpack("3B", file.read(3))))
                self.flag = struct.unpack("B", file.read(1))[0]  # padding
                for i in range(0, 4):
                    self.vertices.append(int(vIdx[i] / 4))
                    self.uv.append(struct.unpack("2B", file.read(2)))

    def tobin(self):
        bin = bytes()
        bin += struct.pack("4B", self.type, self.size, self.side, self.flag)
        for i in range(0, self.verticesCount):
            # v index should be multiply by 4 for the WEP format
            bin += struct.pack("H", int(self.vertices[i] * 4))
        for i in range(0, self.verticesCount):
            bin += struct.pack("2B", self.uv[i][0], self.uv[i][1])
        # TODO : handle vertex colored faces
        return bin

    def binsize(self):
        return self.size

class MPDFace:
    def __init__(self):
        self.group = None # parent MPDGroup
        self.quad = False
        self.type = 0
        self.clutId = 0
        self.textureId = 0
        self.materialRef = "0@0"
        self.vertices = []
        self.colors = []
        self.uv = []
    def __repr__(self):
        return("MPDFace : "+" type : "+repr(self.type)+", clutId : "+repr(self.clutId)+", textureId : "+repr(self.textureId))
    def feed(self, file, group, isQuad = False):
        self.quad = isQuad
        # fuck that mess
        # Triangle vt1  vt2  vt3  col1  col2  u1 col3  v1 u2-v2  clt  u3-v3  tex
        # Quad     vt1  vt2  vt3  col1  col2  u1 col3  v1 u2-v2  clt  u3-v3  tex  vt4  u4 col4  v4
        p1x, p1y, p1z = struct.unpack("3h", file.read(6))
        p2x, p2y, p2z = struct.unpack("3b", file.read(3))
        p3x, p3y, p3z = struct.unpack("3b", file.read(3))
        r1, g1, b1, self.type = struct.unpack("4B", file.read(4))
        r2, g2, b2, u1, r3, g3, b3, v1, u2, v2 = struct.unpack("10B", file.read(10))
        self.clutId, u3, v3, self.textureId = struct.unpack("H2BH", file.read(6))
        self.materialRef = repr(self.textureId)+"@"+repr(self.clutId)
        if group.materialRefs.__contains__(self.materialRef) == False:
            group.materialRefs.append(self.materialRef)
        if self.quad == True:
            p4x, p4y, p4z, u4, r4, g4, b4, v4 = struct.unpack("3b5B", file.read(8))

        self.vertices = []
        vertex = VertexSection.Vertex()
        self.vertices.append(vertex.setGXYZ(group, p1x, p1y, p1z))
        vertex = VertexSection.Vertex()
        self.vertices.append(vertex.setGXYZ(group, p2x * group.scale + p1x, p2y * group.scale + p1y, p2z * group.scale + p1z))
        vertex = VertexSection.Vertex()
        self.vertices.append(vertex.setGXYZ(group, p3x * group.scale + p1x, p3y * group.scale + p1y, p3z * group.scale + p1z))
        self.uv.append([u1, v1])
        self.uv.append([u2, v2])
        self.uv.append([u3, v3])
        self.colors.append(color.RGB([r1, g1, b1]))
        self.colors.append(color.RGB([r2, g2, b2]))
        self.colors.append(color.RGB([r3, g3, b3]))

        if self.quad == True:
            vertex = VertexSection.Vertex()
            self.vertices.append(vertex.setGXYZ(group, p4x * group.scale + p1x, p4y * group.scale + p1y, p4z * group.scale + p1z))
            self.uv.append([u4, v4])
            self.colors.append(color.RGB([r4, g4, b4]))