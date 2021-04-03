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


from . import TIM


class ImportZND(bpy.types.Operator, ImportHelper):
    """Load a ZND file"""

    bl_idname = "import_zone_datas.znd"
    bl_label = "Import ZND"
    filename_ext = ".ZND"

    filepath: bpy.props.StringProperty(default="", subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.ZND", options={"HIDDEN"})

    def execute(self, context):
        keywords = self.as_keywords(ignore=("axis_forward","axis_up","filter_glob",))
        BlenderImport(self, context, **keywords)

        return {"FINISHED"}

def BlenderImport(operator, context, filepath):
    znd = ZND()
    # we read datas from a file
    znd.loadFromFile(filepath)



class ZND:
    def __init__(self):
        self.name = "ZND"
        self.header = ZNDHeader()
        self.tims = []
    def loadFromFile(self, filepath):
        # Open a ZND file and parse it
        file = open(filepath, "rb")
        self.name = bpy.path.display_name(filepath)
        self.parse(file)
        file.close()
    def parse(self, file):
        print("parsing ZND...")

        self.header.feed(file)

        # we skip MPD section
        # and we go to TIM Section

        file.seek(self.header.ptrTIM)  
        timSectionLen, uk1, uk2, uk3, numTims = struct.unpack("5I", file.read(20))
        self.tims = []
        #self.buffer = TIM.FrameBuffer()
        for i in range(0, numTims):
            tlen = struct.unpack("I", file.read(4))[0]
            timptr = file.tell()
            tim = TIM.TIM16BPP()
            tim.parse(i, file, timptr, tlen)
            #print(tim)
            self.tims.append(tim)
            file.seek(timptr+tlen)
        
        #self.buffer.buildTexture()

    def getTIM(self, idx):
        x = ( idx * 64 ) % 1024
        # y = math.floor( ( idx * 64 ) / 1024 )
        for tim in self.tims:
            if ( tim.fx == x ):
                return tim
        return self.tims[0]

    def getCLUT(self, clutId):

        x = ( int(clutId) * 16 ) % 1024
        y = math.floor( ( int(clutId) * 16 ) / 1024 )

        clut = None
        for tim in self.tims:
            if ( tim.fx <= x and tim.fx + tim.width > x and tim.fy <= y and tim.fy + tim.height > y ):
                clut = tim.buildCLUT( x, y )
                break
        return clut

    def getPixels(self, ref):
        textureId, clutId = ref.split("@")
        textureTIM = self.getTIM( int(textureId) )
        clut = self.getCLUT( int(clutId) )
        return textureTIM.build( clut )

class ZNDHeader:
    def __init__(self):
        self.ptrMPD = 0
        self.lenMPD = 0
        self.ptrEnemies = 0
        self.lenEnemies = 0
        self.ptrTIM = 0
        self.lenTIM = 0
        self.WAVEindex = 0
        self.unk = 0
    def feed(self, file):
        self.ptrMPD, self.lenMPD, self.ptrEnemies, self.lenEnemies, self.ptrTIM, self.lenTIM, self.WAVEindex = struct.unpack("6IB", file.read(25))

