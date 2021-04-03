bl_info = {
    "name": "Vagrant Story file formats Add-on",
    "description": "Import-Export Vagrant Story file formats (WEP, SHP, SEQ, ZUD, MPD, ZND, P, FBT, FBC).",
    "author": "Sigfrid Korobetski (LunaticChimera)",
    "version": (2, 1),
    "blender": (2, 92, 0),
    "location": "File > Import-Export",
    "category": "Import-Export",
}


# http://datacrystal.romhacking.net/wiki/Vagrant_Story:SEQ_files
# https://github.com/morris/vstools/blob/master/src/SEQAnimation.js

import os
import math
import struct

import bpy
import mathutils
from bpy.props import BoolProperty, EnumProperty, FloatProperty, StringProperty
from bpy_extras.io_utils import ExportHelper, ImportHelper
from . import VS


# CALLED BY BLENDER
class Import(bpy.types.Operator, ImportHelper):
    """Load a SEQ file"""

    bl_idname = "import_anim.seq"
    bl_label = "Import SEQ"
    filename_ext = ".SEQ"

    filepath: bpy.props.StringProperty(default="", subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.SEQ", options={"HIDDEN"})

    def execute(self, context):
        keywords = self.as_keywords(ignore=("axis_forward","axis_up","filter_glob"))
        BlenderImport(self, context, **keywords)

        return {"FINISHED"}

def BlenderImport(operator, context, filepath):
    seq = SEQ()
    # we read datas from a file
    seq.loadFromFile(filepath)

def rot13toRad(angle):
    return angle * (math.pi / 4096)

class SEQ:
    def __init__(self):
        self.name = "SEQ"
        self.header = SEQHeader()
        self.animations = []
        self.slots = []
    def loadFromFile(self, filepath):
        # Open a SEQ file and parse it
        file = open(filepath, "rb")
        self.name = bpy.path.display_name(filepath)
        self.parse(file)
        file.close()
    def parse(self, file):
        self.header.feed(file)

        self.animations = []
        for i in range(0, self.header.numAnimations):
            a = Anim()
            a.feed(file, i, self.header.numBones)
            self.animations.append(a)

        self.slots = []
        for i in range(0, self.header.numSlots):
            self.slots.append(struct.unpack("b", file.read(1))[0])

        for i in range(0, self.header.numAnimations):
            self.animations[i].getData(file, self)
    def buildAnimations(self, shpObj, bool_anim_trans = False):
        for anim in self.animations:
            anim.build(shpObj, self.name + "_Animation_" + repr(anim.index), bool_anim_trans)

class SEQHeader:
    def __init__(self):
        self.numSlots = 0
        self.numBones = 0
        self.size = 0
        self.dataOffset = 0
        self.slotOffset = 0
        self.headerOffset = 0
        self.baseOffset = 0
        self.numAnimations = 0
    def __repr__(self):
        return "(--SEQ--"+ " numSlots : "+ repr(self.numSlots)+ " numBones : "+ repr(self.numBones)+ " size : "+ repr(self.size)+ " dataOffset : "+ repr(self.dataOffset)+ " slotOffset : "+ repr(self.slotOffset)+ " headerOffset : "+ repr(self.headerOffset)+ ")"
    def feed(self, file):
        self.baseOffset = file.tell()  # base ptr needed because SEQ may be embedded
        self.numSlots, self.numBones, self.size, self.dataOffset, self.slotOffset = struct.unpack("2H3I", file.read(16))
        self.dataOffset += 8  # offset to animation data
        self.slotOffset += 8  # offset to slots
        # offset to rotation and keyframe data
        self.headerOffset = self.slotOffset + self.numSlots
        self.numAnimations = int((self.dataOffset - self.numSlots - 16) / (self.numBones * 4 + 10))
    def ptrData(self, i):
        return i + self.headerOffset + self.baseOffset



ACTIONS = {
    0x01: ["loop", 0], # verified
    0x02: ["0x02", 0], # often at end, used for attack animations
    0x04: ["0x04", 1], # verified in 00_COM (no other options, 0x00 x00 follows)
    0x0A: ["0x0a", 1], # pretty sure, used with walk/run, followed by 0x17/left, 0x18/right
    0x0B: ["0x0b", 0],
    0x0C: ["0x0c", 1],
    0x0D: ["0x0d", 0],
    0x0F: ["0x0f", 1], # first
    0x13: ["unlockBone", 1],  # verified in emulation
    0x14: ["0x14", 1],  # often at end of non-looping
    0x15: ["0x15", 1],  # verified 00_COM (no other options, 0x00 0x00 follows)
    0x16: ["0x16", 2],  # first, verified 00_BT3
    0x17: ["0x17", 0],  # + often at end
    0x18: ["0x18", 0],  # + often at end
    # first, verified 00_COM (no other options, 0x00 0x00 follows)
    0x19: ["0x19", 0],
    0x1A: ["0x1a", 1],  # first, verified 00_BT1 (0x00 0x00 follows)
    0x1B: ["0x1b", 1],  # first, verified 00_BT1 (0x00 0x00 follows)
    0x1C: ["0x1c", 1],
    0x1D: ["paralyze?", 0],  # first, verified 1C_BT1
    0x24: ["0x24", 2],  # first
    0x27: ["0x27", 4],  # first, verified see 00_COM
    0x34: ["0x34", 3],  # first
    0x35: ["0x35", 5],  # first
    0x36: ["0x36", 3],
    0x37: ["0x37", 1],  # pretty sure
    0x38: ["0x38", 1],
    0x39: ["0x39", 1],
    0x3A: ["disappear", 0],  # used in death animations
    0x3B: ["land", 0],
    0x3C: ["adjustShadow", 1],  # verified
    0x3F: ["0x3f", 0],  # first, pretty sure, often followed by 0x16
    0x40: ["0x40", 0],  # often preceded by 0x1a, 0x1b, often at end
}

class Anim:
    def __init__(self):
        self.index = 0
        self.length = 0
        self.idOtherAnimation = -1
        self.scaleFlags = 0
        self.ptrActions = 0
        self.ptrTranslation = 0
        self.ptrMove = 0
        self.ptrBones = []
        self.ptrBonesScale = []
        self.numBones = 0
        self.pose = []
        self.keyframes = []
        self.trans = []
        self.base = None
        self.localPtr = 0
        self.lastTime = 0
        self.rotationPerBone = []
        self.rotationKeysPerBone = []
        self.scalePerBone = []
        self.scaleKeysPerBone = []

    def __repr__(self):
        return "(--ANIM--)"

    def feed(self, file, i, numBones):
        self.index = i
        self.numBones = numBones
        self.length,self.idOtherAnimation,self.scaleFlags,self.ptrActions,self.ptrTranslation,self.ptrMove = struct.unpack("HbB3H", file.read(10))

        for i in range(0, self.numBones):
            self.ptrBones.append(int(struct.unpack("H", file.read(2))[0]))

        for i in range(0, self.numBones):
            self.ptrBonesScale.append(int(struct.unpack("H", file.read(2))[0]))

    def tobin(self):
        bin = bytes()
        return bin

    def readXYZ(self, file):
        return struct.unpack(">3h", file.read(6))

    def readActions(self, file):
        actions = []
        while True:
            # frame number or 0xff
            f = int(struct.unpack("B", file.read(1))[0])
            # TODO probably wrong to break here
            if f == 0xFF:
                break
            if f > self.length:
                print("Unexpected frame number")
            a = int(struct.unpack("B", file.read(1))[0])  # action
            if a == 0x00:
                return
            action = ACTIONS[a]

            if action is None:
                print("Unknown SEQ action")
            params = []
            for i in range(0, action[1]):
                params.append(int(struct.unpack("B", file.read(1))[0]))
            actions.append([f, action[0], params])

    def readKeys(self, file):
        keys = [[0, 0, 0, 0]]
        f = 0

        while True:
            key = self.readKey(file)
            if key is None:
                break

            keys.append(key)
            f += key[3]

            if f >= (self.length - 1):
                break

        return keys

    def readKey(self, file):
        code = struct.unpack("B", file.read(1))[0]

        if code == 0x00:
            return None

        f = 0
        x = 0
        y = 0
        z = 0

        if (code & 0xE0) > 0:
            # number of frames, byte case
            f = code & 0x1F
            if f == 0x1F:
                f = 0x20 + struct.unpack("B", file.read(1))[0]
            else:
                f = 1 + f
        else:
            # number of frames, half word case
            f = code & 0x3
            if f == 0x3:
                f = 4 + struct.unpack("B", file.read(1))[0]
            else:
                f = 1 + f

            # half word values
            code = code << 3
            h = struct.unpack(">h", file.read(2))[0]

            if (h & 0x4) > 0:
                x = h >> 3
                code = code & 0x60

                if (h & 0x2) > 0:
                    y = struct.unpack(">h", file.read(2))[0]
                    code = code & 0xA0

                if (h & 0x1) > 0:
                    z = struct.unpack(">h", file.read(2))[0]
                    code = code & 0xC0
            elif (h & 0x2) > 0:
                y = h >> 3
                code = code & 0xA0

                if (h & 0x1) > 0:
                    z = struct.unpack(">h", file.read(2))[0]
                    code = code & 0xC0
            elif (h & 0x1) > 0:
                z = h >> 3
                code = code & 0xC0
        # byte values (fallthrough)
        if (code & 0x80) > 0:
            x = struct.unpack("b", file.read(1))[0]
        if (code & 0x40) > 0:
            y = struct.unpack("b", file.read(1))[0]
        if (code & 0x20) > 0:
            z = struct.unpack("b", file.read(1))[0]
        return [x, y, z, f]

    def getData(self, file, seq):
        self.localPtr = self.ptrTranslation + seq.header.baseOffset + seq.header.dataOffset
        file.seek(self.localPtr)
        # read translation
        self.trans.append(struct.unpack(">3h", file.read(6)))  # BIG_ENDIAN
        self.translationKeys = self.readKeys(file)

        if self.ptrActions > 0:
            file.seek(seq.header.ptrData(self.ptrActions))
            self.readActions(file)

        self.rotationPerBone = []
        self.rotationKeysPerBone = []
        self.scalePerBone = []
        self.scaleKeysPerBone = []

        # read bone animation data
        for i in range(0, seq.header.numBones):
            # default values
            self.rotationPerBone.append([0, 0, 0])
            self.rotationKeysPerBone.append([0, 0, 0, 0])
            self.scalePerBone.append([1, 1, 1])
            self.scaleKeysPerBone.append([1, 1, 1, 0])

            file.seek(seq.header.ptrData(self.ptrBones[i]))

            if self.idOtherAnimation == -1:
                self.rotationPerBone[i] = self.readXYZ(file)
            else:
                file.seek(seq.header.ptrData(seq.animations[self.idOtherAnimation].ptrBones[i]))
                self.rotationPerBone[i] = self.readXYZ(file)

            self.rotationKeysPerBone[i] = self.readKeys(file)

            file.seek(seq.header.ptrData(self.ptrBonesScale[i]))

            if self.scaleFlags & 0x1:
                self.scalePerBone[i] = struct.unpack("3B", file.read(3))

            if self.scaleFlags & 0x2:
                self.scaleKeysPerBone[i] = self.readKeys(file)

    def build(self, blender_obj, anim_name, bool_anim_trans = False):
        arm_obj = blender_obj.parent
        arm_obj.animation_data_create()
        arm_obj.animation_data.action = bpy.data.actions.new(name=anim_name)

        if (bool_anim_trans == True):
            # we do translation first
            # this is not perfect yet
            tkl = len(self.translationKeys)
            tx = 0
            ty = 0
            tz = 0
            t = 0
            for j in range(0, tkl):
                keyframe = self.translationKeys[j]
                f = keyframe[3]
                t += f
                if keyframe[0] == None:
                    keyframe[0] = self.translationKeys[j - 1][0]

                if keyframe[1] == None:
                    keyframe[1] = self.translationKeys[j - 1][1]

                if keyframe[2] == None:
                    keyframe[2] = self.translationKeys[j - 1][2]

                tx += keyframe[0]/VS.VERTEX_RATIO * f
                ty += keyframe[1]/VS.VERTEX_RATIO * f
                tz += keyframe[2]/VS.VERTEX_RATIO * f
                arm_obj.location = (tx, tz, -ty)
                arm_obj.keyframe_insert(data_path="location", frame=t)


        for i in range(0, self.numBones):
            bone = arm_obj.pose.bones["bone_" + repr(i)]
            if i < len(self.rotationKeysPerBone):
                keyframes = self.rotationKeysPerBone[i]
                pose = self.rotationPerBone[i]

                rx = pose[0] * 2
                ry = pose[1] * 2
                rz = pose[2] * 2
                t = 0
                kfl = len(keyframes)

                for j in range(0, kfl):
                    keyframe = keyframes[j]
                    f = keyframe[3]
                    t += f
                    if keyframe[0] == None:
                        keyframe[0] = keyframes[j - 1][0]

                    if keyframe[1] == None:
                        keyframe[1] = keyframes[j - 1][1]

                    if keyframe[2] == None:
                        keyframe[2] = keyframes[j - 1][2]

                    rx = rx + (keyframe[0] * f)
                    ry = ry + (keyframe[1] * f)
                    rz = rz + (keyframe[2] * f)
                    bone_rotation = (rot13toRad(rx), rot13toRad(ry), rot13toRad(rz))

                    # euler rotations isn't good enough for animations interpolations so we build Quaternions
                    # bone.rotation_mode = 'XYZ'
                    # bone.rotation_euler = bone_rotation
                    # bone.keyframe_insert(data_path='rotation_euler', frame=t)

                    qu = mathutils.Quaternion((1.0, 0.0, 0.0), bone_rotation[0])
                    qv = mathutils.Quaternion((0.0, 1.0, 0.0), bone_rotation[1])
                    qw = mathutils.Quaternion((0.0, 0.0, 1.0), bone_rotation[2])
                    q = qw @ qv @ qu

                    bone.rotation_mode = "QUATERNION"
                    bone.rotation_quaternion = q
                    bone.keyframe_insert(data_path="rotation_quaternion", frame=t)