bl_info = {
    "name": "Vagrant Story file formats Add-on",
    "description": "Import-Export Vagrant Story file formats (WEP, SHP, SEQ, ZUD, MPD, ZND, P, FBT, FBC).",
    "author": "Sigfrid Korobetski (LunaticChimera)",
    "version": (2, 12),
    "blender": (3, 2, 0),
    "location": "File > Import-Export",
    "category": "Import-Export",
}

import os
import struct

import bpy
import math

from bpy.props import BoolProperty, EnumProperty, FloatProperty, StringProperty
from bpy_extras.io_utils import ExportHelper, ImportHelper

from . import color


class Import(bpy.types.Operator, ImportHelper):
    """Load a EFFECT.P file"""

    bl_idname = "import_effect.mpd"
    bl_label = "Import EFFECT"
    filename_ext = ".P"

    filepath: bpy.props.StringProperty(default="", subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.P", options={"HIDDEN"})

    def execute(self, context):
        keywords = self.as_keywords(ignore=("axis_forward","axis_up","filter_glob",))
        BlenderImport(self, context, **keywords)

        return {"FINISHED"}


def BlenderImport(operator, context, filepath):
    effect = Effect()

    #print("filepath : "+filepath)
    #print("bpy.path.abspath : "+bpy.path.abspath(filepath))
    #print("bpy.path.basename : "+bpy.path.basename(filepath))

    if (bpy.path.basename(filepath) == "E000.P"):
        # Special case, all other fx starts at 1, E000_0.FBC must be black and white
        fbcPath = filepath.replace(bpy.path.basename(filepath), "E000_0.FBC")
        fbc = FBC()
        fbc.loadFromFile(fbcPath)
        #print(fbc)

        fbtPath = filepath.replace(bpy.path.basename(filepath), "E000_0.FBT")
        fbt = FBT()
        fbt.loadFromFile(fbtPath, fbc.palettes)

        effect.FBC = fbc
        effect.FBTs.append(fbt)
    else:
        fbcPath = filepath.replace(".P", "_1.FBC")
        if(os.path.isfile(fbcPath)):
            fbc = FBC()
            fbc.loadFromFile(fbcPath)
            #print(fbc)
            effect.FBC = fbc
            # one effect can have up to 7 FBT and somtimes there is no FBC and FBT, maybe empty fx...
            for i in range(1,9):
                fbtPath = filepath.replace(".P", "_"+repr(i)+".FBT")
                if(os.path.isfile(fbtPath)):
                    fbt = FBT()
                    fbt.loadFromFile(fbtPath, fbc.palettes)
                    effect.FBTs.append(fbt)
                else:
                    break

    p = P()
    # we read datas from a file
    p.width = len(effect.FBTs)*128
    if effect.FBC != None:
        p.numPalettes = effect.FBC.numPalettes
    p.loadFromFile(filepath)
    #print(p)
    effect.P = p



    bpy.ops.mesh.primitive_plane_add()
    plane = bpy.context.active_object
    plane.name = bpy.path.basename(filepath)

    mat = bpy.data.materials.new(name=str(bpy.path.basename(filepath) + "_Mat"))
    mat.use_nodes = True
    mat.blend_method = "CLIP"  # to handle alpha cutout
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Specular"].default_value = 0
    bsdf.inputs["Metallic"].default_value = 0

    if effect.FBC != None:
        pixmap = []
        h = effect.FBTs[0].height * effect.FBC.numPalettes
        w = effect.FBTs[0].width

        for i in range(0, h):
            for t in range(0, len(effect.FBTs)):
                for j in range(0, w):
                    pixmap.extend(effect.FBTs[t].texture[i*w+j].toFloat())

        texImage = mat.node_tree.nodes.new("ShaderNodeTexImage")
        texImage.image = bpy.data.images.new(bpy.path.basename(filepath)+"_Sprite_Sheet", effect.FBTs[0].width * len(effect.FBTs), h)
        texImage.image.pixels = pixmap
        #texImage.interpolation = "Closest"  # texture filter
        mat.node_tree.links.new(bsdf.inputs["Base Color"], texImage.outputs["Color"])
        mat.node_tree.links.new(bsdf.inputs["Alpha"], texImage.outputs["Alpha"])
        plane.active_material = mat

        mesh = plane.data
        action = bpy.data.actions.new("MeshAnimation")

        mesh.animation_data_create()
        mesh.animation_data.action = action

        uvlayer = mesh.uv_layers.active

        data_path = "vertices[%d].co"
        uv_datas_path = "uv_layers.active.data[%d].uv"

        for t in range(0, len(p.frames)):
            frame = p.frames[t]
            xdec = frame.textureId * 128

            for v in mesh.vertices:
                fcurves = [action.fcurves.find(data_path % v.index, index= i) for i in range(3)]
                if fcurves == [None, None, None]:
                    fcurves = [action.fcurves.new(data_path % v.index, index =  i) for i in range(3)]
                co_rest = v.co
                sprite_co = (frame.v_co[v.index][0]/100, frame.v_co[v.index][1]/100, 0.0)
                insert_keyframe(fcurves, t, sprite_co)

            for face in mesh.polygons:
                for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
                    #uvlayer.data[loop_idx].uv = (xdec + frame.uvs[loop_idx][0], frame.uvs[loop_idx][1])
                    uv_curve = [action.fcurves.find(uv_datas_path % loop_idx, index= i) for i in range(2)]
                    if uv_curve == [None, None]:
                        uv_curve = [action.fcurves.new(uv_datas_path % loop_idx, index= i) for i in range(2)]
                    insert_keyframe(uv_curve, t, (xdec + frame.uvs[loop_idx][0], frame.uvs[loop_idx][1]))

def insert_keyframe(fcurves, frame, values):
    for fcu, val in zip(fcurves, values):
        fcu.keyframe_points.insert(frame, val, options={'FAST'})

class Effect:
    def __init__(self):
        self.P = None
        self.FBC = None
        self.FBTs = []

class P:
    def __init__(self):
        self.name = ""
        self.filesize = 0
        self.frames = []
        self.n1 = 0
        self.n2 = 0
        self.wid = 0
        self.width = 0 # this width variable is based on FBT length * 128
        self.hei = 0
        self.framePtr = 0
        self.n5 = 0
        self.n6 = 0
        self.p = 0 # padding ?
        self.numPalettes = 0
    def __repr__(self):
        return (
            "P : "+" name : "+repr(self.name)+" filesize : "+repr(self.filesize)+" Width : "+repr(self.wid)+", Height : "+repr(self.hei)+
            ", n1 : "+repr(self.n1)+", n2 : "+repr(self.n2)+", n5 : "+repr(self.n5)+", n6 : "+repr(self.n6)+", p : "+repr(self.p)
        )
    def loadFromFile(self, filepath):
        self.filesize = os.stat(filepath).st_size
        file = open(filepath, "rb")
        self.name = bpy.path.display_name(filepath)
        self.parse(file)
        file.close()
    def parse(self, file):
        self.n1, self.n2 = struct.unpack("2B", file.read(2))
        self.wid, self.hei = struct.unpack(">2H", file.read(4))
        self.framePtr, self.n5, self.n6, self.p =  struct.unpack("H2BH", file.read(6))

        ptr1 = self.framePtr + 4
        loop = round((ptr1 - file.tell()) / 4)

        self.frames = []
        for i in range(0, loop):
            if (file.tell() + 4 <= self.filesize):
                frame = EffectFrame()
                frame.parse(file)
                self.frames.append(frame)
            else:
                break

        for i in range(0, loop):
            frame = self.frames[i]
            if (file.tell() + 24 <= self.filesize):
                frame.feed(file, self.width, self.hei, self.numPalettes)
            else:
                break

class FBC:
    def __init__(self):
        self.name =""
        self.filesize = 0
        self.numPalettes = 0
        self.palettes = []
    def __repr__(self):
        return ("FBC : "+" name : "+repr(self.name)+" filesize : "+repr(self.filesize)+" numPalettes : "+repr(self.numPalettes))
    def loadFromFile(self, filepath):
        self.filesize = os.stat(filepath).st_size
        self.numPalettes = round(self.filesize / 512)
        self.name = bpy.path.display_name(filepath)
        file = open(filepath, "rb")
        self.parse(file)

        file.close()
    def parse(self, file):
        self.palettes = []
        for i in range(0, self.numPalettes):
            colors = []
            for j in range(0, 256):
                colors.append(color.from16bits( struct.unpack("H", file.read(2))[0] ))
            self.palettes.append(colors)

class FBT:
    def __init__(self):
        self.name = "FBT"
        self.filesize = 0
        self.texture = None
        self.width = 0
        self.height = 0
    def __repr__(self):
        return ("P : "+" name : "+repr(self.name)+" filesize : "+repr(self.filesize))
    def loadFromFile(self, filepath, palettes):
        self.name = bpy.path.display_name(filepath)
        self.filesize = os.stat(filepath).st_size
        file = open(filepath, "rb")
        self.parse(file, palettes)
        file.close()
    def parse(self, file, palettes):
        self.width = 128
        self.height = 128
        size = self.width * self.height
        pad = math.floor(self.filesize / size)
        self.height *= pad
        size = self.width * self.height

        #print("FBT parse : "+" height : "+repr(self.height))
        self.texture = []
        clutPtr = file.tell()
        for i in range(0, len(palettes)):
            cluts = []
            for x in range(0, self.height):
                cl2 = []
                for y in range(0, self.width):
                    c = palettes[i][struct.unpack("B", file.read(1))[0]]
                    c.A = 255
                    if (c.R + c.G + c.B) < 64:
                        c.A = round((c.R + c.G + c.B) / 3) # make alpha with grey scale
                    cl2.append(c)
                cl2.reverse()
                cluts.extend(cl2)
            cluts.reverse()
            self.texture.extend(cluts)
            file.seek(clutPtr)
        #texImage = bpy.data.textures.new(self.name, 'IMAGE')
        #texImage.image = bpy.data.images.new(self.name, self.width, self.height)
        #texImage.image.pixels = cluts

class EffectFrame:
    def __init__(self):
        self.tex = 0 # unknown but often 1, but could be 2, 4, 5, 9 in 137.P
        self.id = 0
        self.head = []
        self.rect = []
        self.textureId = 0
        self.paletteId = 0
        self.v_co = []
        self.uvs = []
    def __repr__(self):
        return ("EffectFrame : "+" (1)? : "+repr(self.tex)+" id : "+repr(self.id)+" textureId : "+repr(self.textureId)+" paletteId : "+repr(self.paletteId)+" head : "+"{:01X} {:01X} {:01X}".format(self.head[0] , self.head[1] , self.head[2] )+" rect : "+repr(self.rect)+" v_co : "+repr(self.v_co))
    def parse(self, file):
        self.tex, self.id = struct.unpack("2H", file.read(4))
    def feed(self, file, texture_width, texture_height, numPalettes):
        self.head = []
        self.rect = []
        self.v_co = []
        self.uvs = []
        self.head = struct.unpack("4B", file.read(4))
        # nibble based ?
        # self.head[0] control palette
        # self.head[1] ? often 0xBC can be 0xBD or 0x3C
        # self.head[2] control texture, we join FBT textures so it result an x decalage
        # self.head[3] always 0 ?
        self.rect = struct.unpack("4B", file.read(4)) # X - Y - Width - Height
        self.v_co.append(struct.unpack("2h", file.read(4)))
        self.v_co.append(struct.unpack("2h", file.read(4)))
        self.v_co.append(struct.unpack("2h", file.read(4)))
        self.v_co.append(struct.unpack("2h", file.read(4)))


        if (self.head[0] == 0x70):
            self.paletteId = 0
        elif (self.head[0] == 0xB0):
            self.paletteId = 1
        elif (self.head[0] == 0xF0):
            self.paletteId = 2
        elif (self.head[0] == 0x30):
            self.paletteId = 3

        if (self.head[2] == 0xB9 or self.head[2] == 0xD9):
            self.textureId = 0
        elif (self.head[2] == 0xBA or self.head[2] == 0xDA):
            self.textureId = 1
        elif (self.head[2] == 0xBB or self.head[2] == 0xDB):
            self.textureId = 2
        elif (self.head[2] == 0xBC or self.head[2] == 0xDC):
            self.textureId = 3
        elif (self.head[2] == 0xBD or self.head[2] == 0xDD):
            self.textureId = 4
        elif (self.head[2] == 0xBE or self.head[2] == 0xDE):
            self.textureId = 5
        elif (self.head[2] == 0xBF or self.head[2] == 0xDF):
            self.textureId = 6

        dx = self.textureId * 128
        dy = self.paletteId * texture_height

        u1 = (dx+self.rect[0]) / texture_width
        u2 = (dx+self.rect[0]+self.rect[2]) / texture_width
        v1 = (texture_height + dy - (self.rect[1])) / (texture_height * numPalettes)
        v2 = (texture_height + dy - (self.rect[1] + self.rect[3])) / (texture_height * numPalettes)

        self.uvs.append((u1, v1))
        self.uvs.append((u2, v1))
        self.uvs.append((u2, v2))
        self.uvs.append((u1, v2))


        #print(self)
        #print(" u1 : "+repr(u1)+" ,  u2 : "+repr(u2)+" ,  v1 : "+repr(v1)+" ,  v2 : "+repr(v2))
