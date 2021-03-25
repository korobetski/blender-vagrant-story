bl_info = {
    "name": "Vagrant Story file formats Add-on",
    "description": "Import-Export Vagrant Story file formats (WEP, SHP, SEQ, ZUD, MPD, ZND).",
    "author": "Sigfrid Korobetski (LunaticChimera)",
    "version": (2, 0),
    "blender": (2, 92, 0),
    "location": "File > Import-Export",
    "category": "Import-Export",
}


# https://docs.blender.org/api/current/bpy.types.Bone.html

# used in WEP, SHP and ZUD

import struct

def parse(file, numBones):
    print("parsing "+repr(numBones)+" bones...")
    bones = []
    for i in range(0, numBones):
        bone = Bone()
        bone.feed(file, i)
        # in theory parent bone are defined before
        if bone.parentIndex < numBones:
            bone.parent = bones[bone.parentIndex]
        print(bone)
        bones.append(bone)
    return bones


class Bone:
    def __init__(self):
        self.index = 0
        self.name = "bone"
        self.length = 0
        self.parent = None
        self.parentIndex = -1
        self.parentName = None
        self.group = None
        self.groupId = 0
        self.mountId = 0
        self.bodyPartId = 0
        self.mode = 0
        self.unk = (0, 0, 0)

    def __repr__(self):
        return ("(BONE : "+ " index = "+ repr(self.index)+ " length = "+ repr(self.length)+ " parentIndex = "+ repr(self.parentIndex)
            + " groupId :"+ repr(self.groupId)+ " mountId :"+ repr(self.mountId)+ " bodyPartId :"+ repr(self.bodyPartId)
            + "  mode = "+ repr(self.mode)+ "  unk = "+ repr(self.unk)+ ")"
        )

    # for creating a root bone
    def defaultBones(self):
        self.index = 0
        self.length = 0
        self.parentIndex = 47
        self.groupId = 255
        self.mountId = 0
        self.bodyPartId = 0
        self.mode = 0
        self.unk = (0, 0, 0)

    def feed(self, file, i):
        self.index = i
        self.name = "bone_" + str(i)
        self.length, self.parentIndex, self.groupId, self.mountId, self.bodyPartId, self.mode = struct.unpack("i 5b", file.read(9))
        self.unk = struct.unpack("3B", file.read(3))
        file.seek(4, 1) # padding
        #self.length = -self.length  # positive length

    def decalage(self):
        if self.parent != None:
            return self.parent.length + self.parent.decalage()
        else:
            return 0
    # repacking for export
    def tobin(self):
        return struct.pack(
            "i 12B",
            self.length,
            self.parentIndex,
            self.groupId,
            self.mountId,
            self.bodyPartId,
            self.mode,
            self.unk[0], self.unk[1], self.unk[2],
            0, 0, 0, 0,
        )

    def binsize(self):
        return 16