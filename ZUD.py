bl_info = {
    "name": "Vagrant Story file formats Add-on",
    "description": "Import-Export Vagrant Story file formats (WEP, SHP, SEQ, ZUD, MPD, ZND, P, FBT, FBC).",
    "author": "Sigfrid Korobetski (LunaticChimera)",
    "version": (2, 1),
    "blender": (2, 92, 0),
    "location": "File > Import-Export",
    "category": "Import-Export",
}

import struct
import math

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, StringProperty
from bpy_extras.io_utils import ExportHelper, ImportHelper

from . import WEP, SHP, SEQ


class Import(bpy.types.Operator, ImportHelper):
    """Load a ZUD file"""

    bl_idname = "import_mesh.zud"
    bl_label = "Import ZUD"
    filename_ext = ".ZUD"

    filepath: bpy.props.StringProperty(default="", subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.ZUD", options={"HIDDEN"})

    def execute(self, context):
        keywords = self.as_keywords(ignore=("axis_forward","axis_up","filter_glob",))
        BlenderImport(self, context, **keywords)

        return {"FINISHED"}


def BlenderImport(operator, context, filepath):
    zud = ZUD()
    # we read datas from a file
    zud.loadFromFile(filepath)
    
    # Creating Geometry and Meshes for Blender
    zud.buildGeometry()

class ZUD:
    def __init__(self):
        self.name = "ZUD"
        self.header = ZUDHeader()
        self.shp = None
        self.weapon = None
        self.shield = None
        self.commonSeq = None
        self.battleSeq = None
    def __repr__(self):
        return("(--"+repr(self.name)+".ZUD-- | "+repr(self.header)+")")
    def loadFromFile(self, filepath):
        # Open a ZUD file and parse it
        file = open(filepath, "rb")
        self.name = bpy.path.display_name(filepath)
        self.parse(file)
        file.close()
    def parse(self, file):
        self.header.feed(file)
        print(self)

        # SHP SECTION
        file.seek(self.header.ptrSHP)
        self.shp = SHP.SHP()
        self.shp.name = "{:02X}".format(self.header.idSHP)+".ZSHP"
        self.shp.parse(file)

        # WEAPON SECTION
        if self.header.idWEP != 0:
            file.seek(self.header.ptrWEP)
            self.weapon = WEP.WEP()
            self.weapon.name = "{:02X}".format(self.header.idWEP)+".ZWEP"
            self.weapon.parse(file)

        # SHIELD SECTION
        if self.header.idWEP2 != 0:
            file.seek(self.header.ptrWEP2)
            self.shield = WEP.WEP()
            self.shield.name = "{:02X}".format(self.header.idWEP2)+".ZWEP"
            self.shield.parse(file)

        # COMMON SEQ SECTION
        if self.header.lenCSEQ > 0:
            file.seek(self.header.ptrCSEQ)
            self.commonSeq = SEQ.SEQ()
            self.commonSeq.name = self.name+"_COM"
            self.commonSeq.parse(file)

        # BATTLE SEQ SECTION
        if self.header.lenBSEQ > 0:
            file.seek(self.header.ptrBSEQ)
            self.battleSeq = SEQ.SEQ()
            self.battleSeq.name = self.name+"_BAT"
            self.battleSeq.parse(file)

    def buildGeometry(self):
        print("ZUD Building...")

        shpObj = self.shp.buildGeometry()
        if self.header.idWEP != 0:
            wepObj = self.weapon.buildGeometry(self.header.idWEPMat)
            chiof = wepObj.constraints.new(type="CHILD_OF")
            chiof.target = shpObj.parent  # Armature
            chiof.subtarget = self.shp.getWeaponBoneName()
            bpy.ops.constraint.childof_clear_inverse(constraint=chiof.name, owner="OBJECT")
            if self.header.idWEPType == 6:
                # if its a staff
                wepObj.location = (2.8, 0, 0)  # arbitrary value but seems not bad

        if self.header.idWEP2 != 0:
            shieldObj = self.shield.buildGeometry(self.header.idWEP2Mat)
            chiof = shieldObj.constraints.new(type="CHILD_OF")
            chiof.target = shpObj.parent  # Armature
            chiof.subtarget = self.shp.getShieldBoneName()
            bpy.ops.constraint.childof_clear_inverse(constraint=chiof.name, owner="OBJECT")

        if self.header.lenCSEQ > 0:
            self.commonSeq.buildAnimations(shpObj)
        if self.header.lenBSEQ > 0:
            self.battleSeq.buildAnimations(shpObj)

        # selecting armature
        shpObj.parent.name = self.name
        shpObj.parent.select_set(True)
        bpy.context.view_layer.objects.active = shpObj.parent

        if self.header.lenCSEQ > 0:
            shpObj.parent.animation_data.action = bpy.data.actions[self.commonSeq.name + "_Animation_0"]
        if self.header.lenBSEQ > 0:
            shpObj.parent.animation_data.action = bpy.data.actions[self.battleSeq.name + "_Animation_0"]

class ZUDHeader:
    def __init__(self):
        self.idSHP = 0
        self.idWEP = 0
        self.idWEPType = 0
        self.idWEPMat = 0
        self.idWEP2 = 0
        self.idWEP2Mat = 0
        self.uk = 0
        self.pad = 0
        self.ptrSHP = 0
        self.lenSHP = 0
        self.ptrWEP = 0
        self.lenWEP = 0
        self.ptrWEP2 = 0
        self.lenWEP2 = 0
        self.ptrCSEQ = 0
        self.lenCSEQ = 0
        self.ptrBSEQ = 0
        self.lenBSEQ = 0

    def __repr__(self):
        return (" idSHP : "+ repr(self.idSHP)+ " idWEP : "+ repr(self.idWEP)+ " idWEPType : "+ repr(self.idWEPType)+ " idWEPMat : "+ repr(self.idWEPMat)+ " idWEP2 : "
            + repr(self.idWEP2)+ " idWEP2Mat : "+ repr(self.idWEP2Mat)+ " uk : "+ repr(self.uk)+ " pad : "+ repr(self.pad)
        )

    def feed(self, file):
        self.idSHP,self.idWEP,self.idWEPType,self.idWEPMat,self.idWEP2,self.idWEP2Mat,self.uk,self.pad = struct.unpack("8B", file.read(8))
        self.ptrSHP,self.lenSHP,self.ptrWEP,self.lenWEP,self.ptrWEP2,self.lenWEP2,self.ptrCSEQ,self.lenCSEQ,self.ptrBSEQ,self.lenBSEQ = struct.unpack("10I", file.read(40))