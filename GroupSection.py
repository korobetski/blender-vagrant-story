bl_info = {
    "name": "Vagrant Story file formats Add-on",
    "description": "Import-Export Vagrant Story file formats (WEP, SHP, SEQ, ZUD, MPD, ZND, P, FBT, FBC).",
    "author": "Sigfrid Korobetski (LunaticChimera)",
    "version": (2, 12),
    "blender": (3, 2, 0),
    "location": "File > Import-Export",
    "category": "Import-Export",
}

# used in WEP, SHP and ZUD to weight the mesh with bones
# also in MPD in a different way

import struct

from . import FaceSection


def parse(file, numGroups, bones):
    #print("parsing "+repr(numGroups)+" groups...")
    groups = []
    for i in range(0, numGroups):
        group = Group()
        group.feed(file, i)
        group.bone = bones[group.boneIndex]
        group.bone.group = group  # double reference
        #print(group)
        groups.append(group)
    return groups

class Group:
    def __init__(self):
        self.index = 0
        self.bone = None
        self.boneIndex = -1
        self.numVertices = 0

    def __repr__(self):
        return "(GROUP : " + " boneIndex = " + repr(self.boneIndex)+ " numVertices = "+ repr(self.numVertices)+ ")"

    def feed(self, file, i):
        self.index = i
        self.boneIndex, self.numVertices = struct.unpack("hH", file.read(4))

    def tobin(self):
        return struct.pack("hH", self.boneIndex, self.numVertices)

    def binsize(self):
        return 4

class MDPGroup:
    def __init__(self):
        self.name = "MDPGroup"
        self.scale = 8  # default scaling
        self.header = []
        self.numTri = 0
        self.numQuad = 0
        self.numFaces = 0
        self.faces = []
        self.materialRefs = []
        self.materialSided = []
        self.materialTrans =  []

    def __repr__(self):
        return("Grp:"+" T: "+repr(self.numTri)+", Q: "+repr(self.numQuad)+", "+repr(self.header))


    def feed(self, file):
        self.header = []
        #                                                             W  S  E N       W  S  E N
        # a  = bitwise visibility angles, FF = all time visible, C7 = 1100 0111, 7C = 0111 1100
        # sc = scale
        # over = texture overlapping
        # a sc over decX      decZ      decY
        # FF40 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0409 0000 0010 0000 0000 0000 0010 0000 0000 0000 0010 0000 0000 0000 0000 0000 0000 0000
        # FF42 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 3409 0000 0010 0000 0000 0000 0010 0000 0000 0000 0010 0000 0000 0000 0000 0000 0000 0000
        # FF40 0000 0F00 0000 40FF FFFF 7701 0000 0000 0000 0000 0000 0000 0000 BC0B 0000 0010 0000 0000 0000 0010 0000 0000 0000 0010 0000 0000 0000 0000 0000 0000 0000
        self.header = struct.unpack("4B6h48B", file.read(64))

        self.displayAngles = self.header[0]
        self.overlapping = self.header[3]*256 + self.header[2]
        if (self.header[1] & 0x08) > 0:
            self.scale = 1

    def feedFaces(self, file):
        self.faces = []
        self.materialRefs = []
        self.materialSided = []
        self.materialTrans =  []
        self.numTri, self.numQuad = struct.unpack("2I", file.read(8))
        self.numFaces = self.numTri + self.numQuad

        for j in range(0, self.numTri):
            f = FaceSection.MPDFace()
            f.feed(file, self, False)
            #print(f)
            self.faces.append(f)
        for j in range(0, self.numQuad):
            f = FaceSection.MPDFace()
            f.feed(file, self, True)
            #print(f)
            self.faces.append(f)
