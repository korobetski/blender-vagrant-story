bl_info = {
    "name": "Vagrant Story file formats Add-on",
    "description": "Import-Export Vagrant Story file formats (WEP, SHP, SEQ, ZUD, MPD, ZND, P, FBT, FBC).",
    "author": "Sigfrid Korobetski (LunaticChimera)",
    "version": (2, 12),
    "blender": (3, 2, 0),
    "location": "File > Import-Export",
    "category": "Import-Export",
}

#http://datacrystal.romhacking.net/wiki/Vagrant_Story:MPD_files

import struct
from enum import Enum

import bpy
import math

import bmesh
from bpy.props import BoolProperty, EnumProperty, FloatProperty, StringProperty
from bpy_extras.io_utils import ExportHelper, ImportHelper

from . import GroupSection, ZND, VS, ARM


class Import(bpy.types.Operator, ImportHelper):
    """Load a MPD file"""

    bl_idname = "import_map_mesh.mpd"
    bl_label = "Import MPD"
    filename_ext = ".MPD"

    filepath: bpy.props.StringProperty(default="", subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.MPD", options={"HIDDEN"})
    bool_build_collision: bpy.props.BoolProperty(
        name="Build Collision Mesh",
        description="Also build the collision mesh ?",
        default=False
    )

    def execute(self, context):
        keywords = self.as_keywords(ignore=("axis_forward","axis_up","filter_glob",))
        BlenderImport(self, context, **keywords)

        return {"FINISHED"}


def BlenderImport(operator, context, filepath, bool_build_collision = False):
    mpd = MPD()
    # we read datas from a file
    mpd.loadFromFile(filepath)

    #print("filepath : "+filepath)
    #print("bpy.path.abspath : "+bpy.path.abspath(filepath))
    #print("bpy.path.basename : "+bpy.path.basename(filepath))

    zndFileName = VS.MDPToZND(bpy.path.basename(filepath))
    #print("Corresponding ZND : "+zndFileName)
    zndfilepath = filepath.replace(bpy.path.basename(filepath), zndFileName)
    #print("zndfilepath : "+zndfilepath)

    znd = ZND.ZND()
    znd.loadFromFile(zndfilepath)

    # Creating Geometry and Meshes for Blender
    mpd.buildGeometry(znd, bool_build_collision)


class MPD:
    def __init__(self):
        self.name = "MPD"
        self.header = MPDHeader()
        self.room = Room()
    def loadFromFile(self, filepath):
        # Open a MPD file and parse it
        file = open(filepath, "rb")
        self.name = bpy.path.display_name(filepath)
        self.parse(file)
        file.close()
    def parse(self, file):
        self.header.feed(file)

        #print("Room Section         len("+repr(self.header.lenRoomSection)+")           at : "+repr("{0:8X}".format(self.header.ptrRoomSection)))

        # RoomSection
        if self.header.lenRoomSection > 96:
            self.room.feed(file)

        #print("Cleared Section          len("+repr(self.header.lenClearedSection)+")            at : "+repr("{0:8X}".format(self.header.ptrClearedSection)))
        #print("Script Section           len("+repr(self.header.lenScriptSection)+")         at : "+repr("{0:8X}".format(self.header.ptrScriptSection)))
        #print("Door Section             len("+repr(self.header.lenDoorSection)+")           at : "+repr("{0:8X}".format(self.header.ptrDoorSection)))
        #print("Enemy Section            len("+repr(self.header.lenEnemySection)+")          at : "+repr("{0:8X}".format(self.header.ptrEnemySection)))
        #print("Treasure Section         len("+repr(self.header.lenTreasureSection)+")           at : "+repr("{0:8X}".format(self.header.ptrTreasureSection)))


    def buildGeometry(self, znd = None, bool_build_collision = False):
        #print("MPD Building...")
        # Creating Geometry and Mesh for Blender
        self.room.blenderize()
        view_layer = bpy.context.view_layer
        blender_mesh = bpy.data.meshes.new(name=self.name + "_MESH")
        blender_mesh.from_pydata(self.room.blender.vertices, [], self.room.blender.faces)
        blender_obj = bpy.data.objects.new(self.name, object_data=blender_mesh)

        # building all needed materials
        for ref in self.room.materialRefs:
            # building texture and material from ZND and texture ID + clut ID
            mat = bpy.data.materials.new(name=str(ref+"_MAT"))
            mat.use_nodes = True
            mat.blend_method = "HASHED"  # to handle alpha cutout enum in [‘OPAQUE’, ‘CLIP’, ‘HASHED’, ‘BLEND’], default ‘OPAQUE’
            translucent = False # define alpha with the color grey scale

            for i in range(0, len(self.room.groups)):
                if self.room.groups[i].materialRefs.__contains__(ref):
                    if self.room.groups[i].materialSided[self.room.groups[i].materialRefs.index(ref)] == True:
                        # to handle double sided faces
                        mat.use_backface_culling = False
                    else:
                        mat.use_backface_culling = True
                    if self.room.groups[i].materialTrans[self.room.groups[i].materialRefs.index(ref)] == True:
                        translucent = True
                    else:
                        translucent = False

            # maybe i should consider using a simpler material... VS doesn't need a PBR Material :D
            bsdf = mat.node_tree.nodes["Principled BSDF"]
            bsdf.inputs["Specular"].default_value = 0
            bsdf.inputs["Metallic"].default_value = 0
            texImage = mat.node_tree.nodes.new("ShaderNodeTexImage")
            texImage.image = bpy.data.images.new(str(ref+"_TEX"), 256, 256)
            texImage.image.pixels = znd.getPixels(ref, translucent)
            texImage.interpolation = "Closest"  # texture filter
            vc = mat.node_tree.nodes.new("ShaderNodeVertexColor")
            # https://docs.blender.org/manual/fr/2.91/render/shader_nodes/color/mix.html
            mix = mat.node_tree.nodes.new("ShaderNodeMixRGB")
            # ('MIX', 'DARKEN', 'MULTIPLY', 'BURN', 'LIGHTEN', 'SCREEN', 'DODGE', 'ADD', 'OVERLAY', 'SOFT_LIGHT', 'LINEAR_LIGHT', 'DIFFERENCE', 'SUBTRACT', 'DIVIDE', 'HUE', 'SATURATION', 'COLOR', 'VALUE')
            mix.blend_type = "MULTIPLY"
            mix.inputs[0].default_value = 1
            mat.node_tree.links.new(mix.inputs[1], vc.outputs["Color"])
            mat.node_tree.links.new(mix.inputs[2], texImage.outputs["Color"])
            mat.node_tree.links.new(bsdf.inputs["Base Color"], mix.outputs["Color"])
            # to handle alpha cutout
            mat.node_tree.links.new(bsdf.inputs["Alpha"], texImage.outputs["Alpha"])
            blender_mesh.materials.append(mat)


        # Creating vertices groups
        # https://docs.blender.org/api/current/bpy.types.VertexGroup.html
        lastv = 0
        for group in self.room.groups:
            blender_group = blender_obj.vertex_groups.new(name=group.name)
            indexes = []
            for face in group.faces:
                if face.quad == True:
                    indexes.extend([lastv, lastv+1, lastv+2, lastv+3])
                    lastv += 4
                else:
                    indexes.extend([lastv, lastv+1, lastv+2])
                    lastv += 3
            # type (enum in ['REPLACE', 'ADD', 'SUBTRACT'])
            blender_group.add(indexes, 1, "REPLACE")
            #blender_group.lock_weight = True

        view_layer.active_layer_collection.collection.objects.link(blender_obj)
        blender_obj.select_set(True)
        view_layer.objects.active = blender_obj
        # Creating UVs and Vertex colors for Blender
        uvlayer = blender_mesh.uv_layers.new()
        vcol_layer = blender_mesh.vertex_colors.new()
        colors = self.room.blender.colors
        face_uvs = self.room.blender.uvs
        for face in blender_mesh.polygons:
            face.material_index = self.room.materialRefs.index(self.room.blender.matrefs[face.index])   # multi material support
            for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
                # uvs needs to be scaled from texture W&H
                uvlayer.data[loop_idx].uv = (
                    face_uvs[loop_idx][0] / 256,
                    face_uvs[loop_idx][1] / 256,
                )
                vcol_layer.data[loop_idx].color = colors[loop_idx].toFloat()

        blender_mesh.validate(verbose=True)
        blender_mesh.update()

        # self.room.arm.buildGeometry()

        # WIP reversing collisions
        if bool_build_collision:
            collivertex = []
            collifaces = []
            for y in range(0, self.room.roomY):
                for x in range(0, self.room.roomX):
                    k = y*self.room.roomX + x
                    tile = self.room.collisions[k]
                    #print(tile)
                    z = tile.floor / 16
                    l = len(collivertex)
                    vert0 = (x, y, z)
                    vert1 = (x + 1, y, z)
                    vert2 = (x, y + 1, z)
                    vert3 = (x + 1, y + 1, z)
                    if self.room.tileModes[tile.floorMode] == TileMode.RAMP1Xp:
                        # one unit x+ ramp
                        vert1 = (x + 1, y, z + 1)
                        vert3 = (x + 1, y + 1, z + 1)
                    elif self.room.tileModes[tile.floorMode] == TileMode.RAMP1Xn:
                        # one unit x- ramp
                        vert0 = (x, y, z + 1)
                        vert2 = (x, y + 1, z + 1)
                    elif self.room.tileModes[tile.floorMode] == TileMode.RAMP1Yp:
                        # one unit y+ ramp
                        vert0 = (x, y, z + 1)
                        vert1 = (x + 1, y, z + 1)
                    elif self.room.tileModes[tile.floorMode] == TileMode.RAMP1Yn:
                        # one unit y- ramp
                        vert2 = (x, y + 1, z + 1)
                        vert3 = (x + 1, y + 1, z + 1)

                    elif self.room.tileModes[tile.floorMode] == TileMode.RAMP2Xp:
                        # double unit x+ ramp
                        vert1 = (x + 1, y, z + 1)
                        vert3 = (x + 1, y + 1, z + 1)
                    elif self.room.tileModes[tile.floorMode] == TileMode.RAMP2Xn:
                        # double unit x- ramp
                        vert0 = (x, y, z + 1)
                        vert2 = (x, y + 1, z + 1)
                    elif self.room.tileModes[tile.floorMode] == TileMode.RAMP2Yp:
                        # double unit y+ ramp
                        vert0 = (x, y, z + 1)
                        vert1 = (x + 1, y, z + 1)
                    elif self.room.tileModes[tile.floorMode] == TileMode.RAMP2Yn:
                        # double unit y- ramp
                        vert2 = (x, y + 1, z + 1)
                        vert3 = (x + 1, y + 1, z + 1)
                    elif self.room.tileModes[tile.floorMode] == (TileMode.CHEST or TileMode.HALF):
                        vert2 = (x, y + 1, z + 0.5)
                        vert3 = (x + 1, y + 1, z + 0.5)


                    collivertex.append(vert0)
                    collivertex.append(vert1)
                    collivertex.append(vert2)
                    collivertex.append(vert3)
                    collifaces.append((l+0, l+1, l+3, l+2))
            for y in range(0, self.room.roomY):
                for x in range(0, self.room.roomX):
                    k = y*self.room.roomX + x
                    z = self.room.collisions[k].floor / 16
                    if z > 0:
                        # we add "pillar faces"
                        l = k*4
                        l2 = len(collivertex)

                        if self.room.tileModes[tile.floorMode] == (TileMode.DIAGX):
                            collivertex.append((x, y, 0))
                            collivertex.append((x + 1, y, 0))
                            collivertex.append((x, y + 1, 0))
                            collivertex.append((x + 1, y, 255))
                            collivertex.append((x, y + 1, 255))
                            collivertex.append((x + 1, y + 1, 255))
                            collifaces.append((l+0, l+1, l2+1, l2+0))
                            collifaces.append((l+2, l+0, l2+0, l2+2))
                            collifaces.append((l+2, l+1, l2+1, l2+2)) # bot diag
                            collifaces.append((l+1, l+3, l2+5, l2+3))
                            collifaces.append((l+3, l+2, l2+4, l2+5))
                            collifaces.append((l+1, l+2, l2+4, l2+3)) # top diag
                        elif self.room.tileModes[tile.floorMode] == (TileMode.DIAGY):
                            collivertex.append((x, y, 0))
                            collivertex.append((x + 1, y, 0))
                            collivertex.append((x + 1, y + 1, 0))
                            collivertex.append((x, y, 255))
                            collivertex.append((x, y + 1, 255))
                            collivertex.append((x + 1, y + 1, 255))
                            collifaces.append((l+0, l+1, l2+1, l2+0))
                            collifaces.append((l+2, l+0, l2+0, l2+2))
                            collifaces.append((l+2, l+1, l2+1, l2+2)) # bot diag
                            collifaces.append((l+1, l+3, l2+5, l2+3))
                            collifaces.append((l+3, l+2, l2+4, l2+5))
                            collifaces.append((l+1, l+2, l2+4, l2+3)) # top diag
                        else:
                            collivertex.append((x, y, 0))
                            collivertex.append((x + 1, y, 0))
                            collivertex.append((x, y + 1, 0))
                            collivertex.append((x + 1, y + 1, 0))
                            collifaces.append((l+0, l+1, l2+1, l2+0))
                            collifaces.append((l+1, l+3, l2+3, l2+1))
                            collifaces.append((l+3, l+2, l2+2, l2+3))
                            collifaces.append((l+2, l+0, l2+0, l2+2))
                            #collifaces.append((l+6, l+7, l+5, l+4))
            for y in range(0, self.room.roomY):
                for x in range(0, self.room.roomX):
                    k = y*self.room.roomX + x
                    tile = self.room.collisions[k]
                    z = tile.ceil / 16
                    if self.room.tileModes[tile.ceilMode] != TileMode.VOID :
                        # we have a ceil collision
                        l = len(collivertex)
                        vert0 = (x, y, z)
                        vert1 = (x + 1, y, z)
                        vert2 = (x, y + 1, z)
                        vert3 = (x + 1, y + 1, z)

                        if self.room.tileModes[tile.ceilMode] == TileMode.RAMP1Xp:
                            # one unit x+ ramp
                            vert1 = (x + 1, y, z + 1)
                            vert3 = (x + 1, y + 1, z + 1)
                        elif self.room.tileModes[tile.ceilMode] == TileMode.RAMP1Xn:
                            # one unit x- ramp
                            vert0 = (x, y, z + 1)
                            vert2 = (x, y + 1, z + 1)
                        elif self.room.tileModes[tile.ceilMode] == TileMode.RAMP1Yp:
                            # one unit y+ ramp
                            vert0 = (x, y, z + 1)
                            vert1 = (x + 1, y, z + 1)
                        elif self.room.tileModes[tile.ceilMode] == TileMode.RAMP1Yn:
                            # one unit y- ramp
                            vert2 = (x, y + 1, z + 1)
                            vert3 = (x + 1, y + 1, z + 1)

                        elif self.room.tileModes[tile.ceilMode] == TileMode.RAMP2Xp:
                            # double unit x+ ramp
                            vert1 = (x + 1, y, z + 1)
                            vert3 = (x + 1, y + 1, z + 1)
                        elif self.room.tileModes[tile.ceilMode] == TileMode.RAMP2Xn:
                            # double unit x- ramp
                            vert0 = (x, y, z + 1)
                            vert2 = (x, y + 1, z + 1)
                        elif self.room.tileModes[tile.ceilMode] == TileMode.RAMP2Yp:
                            # double unit y+ ramp
                            vert0 = (x, y, z + 1)
                            vert1 = (x + 1, y, z + 1)
                        elif self.room.tileModes[tile.ceilMode] == TileMode.RAMP2Yn:
                            # double unit y- ramp
                            vert2 = (x, y + 1, z + 1)
                            vert3 = (x + 1, y + 1, z + 1)
                        elif self.room.tileModes[tile.ceilMode] == (TileMode.CHEST or TileMode.HALF):
                            vert2 = (x, y + 1, z + 0.5)
                            vert3 = (x + 1, y + 1, z + 0.5)

                        collivertex.append(vert0)
                        collivertex.append(vert1)
                        collivertex.append(vert2)
                        collivertex.append(vert3)
                        collifaces.append((l+0, l+1, l+3, l+2))

                        collivertex.append((x, y, 16))
                        collivertex.append((x + 1, y, 16))
                        collivertex.append((x, y + 1, 16))
                        collivertex.append((x + 1, y + 1, 16))
                        collifaces.append((l+0, l+1, l+5, l+4))
                        collifaces.append((l+1, l+3, l+7, l+5))
                        collifaces.append((l+3, l+2, l+6, l+7))
                        collifaces.append((l+2, l+0, l+4, l+6))

            mymesh = bpy.data.meshes.new("collision")
            myobject = bpy.data.objects.new("collision", mymesh)
            bpy.context.scene.collection.objects.link(myobject)
            mymesh.from_pydata(collivertex, [], collifaces)

        return blender_obj


class MPDHeader:
    def __init__(self):
        self.ptrRoomSection = 0
        self.lenRoomSection = 0
        self.ptrClearedSection = 0
        self.lenClearedSection = 0
        self.ptrScriptSection = 0
        self.lenScriptSection = 0
        self.ptrDoorSection = 0
        self.lenDoorSection = 0
        self.ptrEnemySection = 0
        self.lenEnemySection = 0
        self.ptrTreasureSection = 0
        self.lenTreasureSection = 0
    def __repr__(self):
        print("MPD Header")
    def feed(self, file):
        (
            self.ptrRoomSection,
            self.lenRoomSection,
            self.ptrClearedSection,
            self.lenClearedSection,
            self.ptrScriptSection,
            self.lenScriptSection,
            self.ptrDoorSection,
            self.lenDoorSection,
            self.ptrEnemySection,
            self.lenEnemySection,
            self.ptrTreasureSection,
            self.lenTreasureSection,
        ) = struct.unpack("12I", file.read(48))



class Room:
    def __init__(self):
        self.lenGeometrySection = 0
        self.lenCollisionSection = 0
        self.lenTilePropertiesSection = 0
        self.lenDoorSection = 0
        self.lenLightingSection = 0
        self.lenSubSection06 = 0
        self.lenSubSection07 = 0
        self.lenSubSection08 = 0
        self.lenTrapSection = 0
        self.lenSubSection0A = 0
        self.lenSubSection0B = 0
        self.lenTextureEffectsSection = 0
        self.lenSubSection0D = 0
        self.lenSubSection0E = 0
        self.lenMiniMapSection = 0
        self.lenSubSection10 = 0
        self.lenSubSection11 = 0
        self.lenFloatingStoneSection = 0
        self.lenChestInteractionSection = 0
        self.lenAKAOSubSection = 0
        self.lenSubSection15 = 0
        self.lenSubSection16 = 0
        self.lenSubSection17 = 0
        self.lenCameraAreaSection = 0
        self.numGroups = 0
        self.groups = []
        self.materialRefs = []
        self.materialSided = []
        self.blender = BlenderDatas()
        self.roomX = 0
        self.roomY = 0
        self.collisions = []
        self.tileModes = []
        self.arm = None
    def feed(self, file):
        (
            self.lenGeometrySection,
            self.lenCollisionSection,
            self.lenTilePropertiesSection,
            self.lenDoorSection,
            self.lenLightingSection,
            self.lenSubSection06,
            self.lenSubSection07,
            self.lenSubSection08,
            self.lenTrapSection,
            self.lenSubSection0A,
            self.lenSubSection0B,
            self.lenTextureEffectsSection,
        ) = struct.unpack("12I", file.read(48))
        (
            self.lenSubSection0D,
            self.lenSubSection0E,
            self.lenMiniMapSection,
            self.lenSubSection10,
            self.lenSubSection11,
            self.lenFloatingStoneSection,
            self.lenChestInteractionSection,
            self.lenAKAOSubSection,
            self.lenSubSection15,
            self.lenSubSection16,
            self.lenSubSection17,
            self.lenCameraAreaSection,
        ) = struct.unpack("12I", file.read(48))

        # Geometry Section
        #print("Geometry Section  len("+repr(self.lenGeometrySection)+") at : "+repr("{0:8X}".format(file.tell())))
        if self.lenGeometrySection > 4:
            # GeometrySection (Polygon groups)
            self.numGroups = struct.unpack("I", file.read(4))[0]
            self.groups = []
            self.materialRefs = []

            #print("Room Groups at : "+repr("{0:8X}".format(file.tell())))
            for i in range(0, self.numGroups):
                group = GroupSection.MDPGroup()
                group.name = "Group "+str(i)
                group.feed(file)
                self.groups.append(group)

            for i in range(0, self.numGroups):
                #print("Room Faces of Group "+repr(i)+" at : "+repr("{0:8X}".format(file.tell())))
                group = self.groups[i]
                group.feedFaces(file)
                #print(group)
                #    tris     quads   x1   y1   z1   x y  z x  y z  R G  B ty
                # 0000 0000 0100 0000 F8FF EEFF 0100 0200 0000 0400 4D4D 4D3E 4D4D 4DA0 9999 996E A060 B638 A660 2600 0204 00A6 9999 996E

                # 0000000001000000F8FFEEFF01000200000004004D4D4D3E4D4D4DA09999996EA060B638A6602600020400A69999996E
                # 0000000001000000F8FFEEFF01000200000004004D4D4D404D4D4DA09999996EA060B638A6602600020400A69999996E

                # we gather all needed material refs
                for ref in group.materialRefs:
                    if self.materialRefs.__contains__(ref) == False:
                        self.materialRefs.append(ref)

        # Collision Section
        #print("Collision Section  len("+repr(self.lenCollisionSection)+") at : "+repr("{0:8X}".format(file.tell())))
        ptrEndCollision = file.tell() + self.lenCollisionSection
        #file.seek(self.lenCollisionSection, 1)
        self.roomX, self.roomY, unk1, numTileModes = struct.unpack("4H", file.read(8))
        # unk1 seems to be always 0x00
        #print("roomX : "+repr(self.roomX)+", roomY : "+repr(self.roomY)+", unk1 : "+repr(unk1)+", numTileModes : "+repr(numTileModes))
        self.collisions = []
        for i in range(0, self.roomY * self.roomX):
            tile = CollisionTile()
            tile.index = i
            tile.floorMode, tile.floor = struct.unpack("2B", file.read(2))
            self.collisions.append(tile)
        for i in range(0, self.roomY * self.roomX):
            tile = self.collisions[i]
            tile.ceilMode, tile.ceil = struct.unpack("2B", file.read(2))

        self.tileModes = []
        for i in range(0, numTileModes):
            tileModesBytes = struct.unpack("16B", file.read(16))
            #self.tileModes.append(tileModesBytes)
            #print("tileModesBytes : "+repr(tileModesBytes))
            if tileModesBytes == (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0):
                self.tileModes.append(TileMode.FLAT)
            elif tileModesBytes == (2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2):
                self.tileModes.append(TileMode.CHEST)
            elif tileModesBytes == (3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3):
                self.tileModes.append(TileMode.FULL)
            elif tileModesBytes == (131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131):
                self.tileModes.append(TileMode.VOID)
            elif tileModesBytes == (0, 2, 4, 6, 0, 2, 4, 6, 0, 2, 4, 6, 0, 2, 4, 6):
                # one unit x+ ramp
                self.tileModes.append(TileMode.RAMP1Xp)
            elif tileModesBytes == (6, 4, 2, 0, 6, 4, 2, 0, 6, 4, 2, 0, 6, 4, 2, 0):
                # one unit x- ramp
                self.tileModes.append(TileMode.RAMP1Xn)
            elif tileModesBytes == (6, 6, 6, 6, 4, 4, 4, 4, 2, 2, 2, 2, 0, 0, 0, 0):
                # one unit y+ ramp
                self.tileModes.append(TileMode.RAMP1Yp)
            elif tileModesBytes == (0, 0, 0, 0, 2, 2, 2, 2, 4, 4, 4, 4, 6, 6, 6, 6):
                # one unit y- ramp
                self.tileModes.append(TileMode.RAMP1Yn)
            elif tileModesBytes == (0, 4, 8, 12, 0, 4, 8, 12, 0, 4, 8, 12, 0, 4, 8, 12):
                # double unit x+ ramp
                self.tileModes.append(TileMode.RAMP2Xp)
            elif tileModesBytes == (12, 8, 4, 0, 12, 8, 4, 0, 12, 8, 4, 0, 12, 8, 4, 0):
                # double unit x- ramp
                self.tileModes.append(TileMode.RAMP2Xn)
            elif tileModesBytes == (12, 12, 12, 12, 8, 8, 8, 8, 4, 4, 4, 4, 0, 0, 0, 0):
                # one unit y+ ramp
                self.tileModes.append(TileMode.RAMP2Yp)
            elif tileModesBytes == (0, 0, 0, 0, 4, 4, 4, 4, 8, 8, 8, 8, 12, 12, 12, 12):
                self.tileModes.append(TileMode.RAMP2Yn)
            elif tileModesBytes[0] == tileModesBytes[1] == tileModesBytes[2] == tileModesBytes[4] == tileModesBytes[5] == tileModesBytes[8]:
                self.tileModes.append(TileMode.DIAGX)
            elif tileModesBytes[7] == tileModesBytes[10] == tileModesBytes[11] == tileModesBytes[13] == tileModesBytes[14] == tileModesBytes[15]:
                self.tileModes.append(TileMode.DIAGY)
            else:
                self.tileModes.append(TileMode.FLAT)


        # Tile properties Section
        #print("TilePropertiesSection len("+repr(self.lenTilePropertiesSection)+") at : "+repr("{0:8X}".format(file.tell())))
        for i in range(0, self.roomY * self.roomX):
            unk = struct.unpack("4B", file.read(4))
            #print("id:"+repr(i)+" -> "+repr(unk))
            # often 00-14-00-D8 or 00-00-00-00
            # unk[0] is maybe a floor climb flag, 0 or 1
            # unk[1] is maybe a floor flag, 20 : not walkable, 0 walkable, 64 door, 212 : door (MAP010.MPD)
            # unk[2] is maybe a ceil flag, 0 : most of the time, 16 : related with doors, 128-129
            # unk[3] is maybe another ceil flag, 0 : no ceil, 216-248 : high ceil, 16 : ceil at 4 units, 32 : ceil at 8, 80 : ceil at 20 ?

        file.seek(ptrEndCollision+self.lenTilePropertiesSection)

        # Door section (maybe more a warp section)
        #print("Room Door Section  len("+repr(self.lenDoorSection)+") at : "+repr("{0:8X}".format(file.tell())))
        # 090003000003003C02000000090343010043000801000000
        # 090003000003004302000000090343010043000801000000
        numDoors = round(self.lenDoorSection /0x0C)
        if self.lenDoorSection >= 0x0C:
            for i in range(0, numDoors):
                destZone, destRoom = struct.unpack("2B", file.read(2))
                rawTileId = struct.unpack("H", file.read(2))[0]
                destination = struct.unpack("2H", file.read(4)) # Y-X
                doorId = struct.unpack("I", file.read(4))[0]
                # the door section seems to use a grid of 32x32
                # so we need to adapt tileId to the current MPD room grid to figure where the door must be
                tileId = round(rawTileId / 32) * self.roomX + (rawTileId % 32)
                #print("MPD door : "+" destZone : "+repr(destZone)+", destRoom : "+repr(destRoom)+" doorId : "+repr(doorId)+" rawTileId : "+repr(rawTileId)+" tileId : "+repr(tileId)+" destination : "+repr(destination))

        #print("LightingSection  len("+repr(self.lenLightingSection)+") at : "+repr("{0:8X}".format(file.tell())))
        endLight = file.tell() + self.lenLightingSection
        # 32 bytes blocks + 12 bytes
        # strange thing :
        # the first light is omited in the SLES-02755.BIN
        # so the light section in MAP009.MPD len(1068) will become len(1036) in the BIN
        # note that cols[4] in the first light in the .MPD gives us the lights number so its maybe not really a light
        numLights = math.floor(self.lenLightingSection / 32)
        for i in range(0, numLights):
            # http://www.psxdev.net/forum/viewtopic.php?f=51&t=3383
            cols = struct.unpack("12B", file.read(12))
            matrix = struct.unpack("10H", file.read(20))
        ambientColor = struct.unpack("12B", file.read(12))

        file.seek(endLight)

        #print("SubSection06  len("+repr(self.lenSubSection06)+") at : "+repr("{0:8X}".format(file.tell())))
        # often starts with lots of 00
        # ????
        # len -> 1328 in MAP009.MPD longer in the BIN -> 1632
        # 100000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000060A0000FFFFFFEFFFFFFFFFFFFFC6FFFFFFFFE70F828183E33FFA06000000E08F0302000000E00E0000000000E00E0000000020F01E0800000060EFFF3C182830F8FEFFFFFF6CFFFFFFFFFFFFFEFFFFFFFFFFFFFEFFFFFF
        # ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff
        #
        file.seek(self.lenSubSection06, 1)

        #print("SubSection07  len("+repr(self.lenSubSection07)+") at : "+repr("{0:8X}".format(file.tell())))
        # 256 * 0x00 in maps 10, 14, 19, 20,... 148
        # no noticable effect on change
        file.seek(self.lenSubSection07, 1)

        #print("SubSection08  len("+repr(self.lenSubSection08)+") at : "+repr("{0:8X}".format(file.tell())))
        file.seek(self.lenSubSection08, 1)

        #print("Trap Section  len("+repr(self.lenTrapSection)+") at : "+repr("{0:8X}".format(file.tell())))
        # 050003000000100001FF0100
        # 05000300000010000AFF0100
        # 0100 0800 0000 1000 01FF 0200 in MAP014.MPD
        # Xco  yco       Skill
        # http://datacrystal.romhacking.net/wiki/Vagrant_Story:skills_list
        numTraps = round(self.lenTrapSection / 0x0C)
        if self.lenTrapSection >= 0x0C:
            for i in range(0, numTraps):
                coords =  struct.unpack("2H", file.read(4))
                pad = struct.unpack("H", file.read(2))[0] # padding, always 0x0000
                skill = struct.unpack("H", file.read(2))[0]
                tunk = struct.unpack("4B", file.read(4))

        #file.seek(self.lenTrapSection, 1)

        #print("SubSection0A  len("+repr(self.lenSubSection0A)+") at : "+repr("{0:8X}".format(file.tell())))
        # 20 byte blocks
        # 0800 0D00 0000 0000 0000 E700 0000 0000 FFFF 0000 in MAP148.MPD

        # 0300 1000 0000 0000 0000 E700 0000 0000 FFFF 0000
        # 0300 0000 0000 0000 0005 E700 0000 0000 FFFF 0000  in MAP010.MPD
        file.seek(self.lenSubSection0A, 1)

        #print("SubSection0B  len("+repr(self.lenSubSection0B)+") at : "+repr("{0:8X}".format(file.tell())))
        # 0000 0000 0000 0000 0000 0000 0000 0000
        # 0000 0000 0000 0000 0000 0000 0000 0000
        # 0000 0000 0000 0000 0000 0000 0100 0000
        # 0000 0000 0000 0000 0000 0000 0000 0000
        # 0000 0000 0000 0000 0000 0000 0000 0000
        # 0100 FFFF FFFF 0900      in MAP014.MPD

        # B0E0 E400 7090 B400 0000 0000 0000 0000
        # 0000 0000 0000 0000 0000 0000 0000 0000
        # 0000 0000 0000 0000 0000 0000 0000 0000
        # 0000 0000 0000 0000 0000 0000 0000 0000
        # 0000 0000 0000 0000 0000 0000 0000 0000
        # 1C00 FFFF FFFF 0000      in MAP148.MPD

        # 00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000100FFFFFFFF0B00
        # FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF

        # no noticable effect on change

        file.seek(self.lenSubSection0B, 1)

        #print("TextureEffectsSection  len("+repr(self.lenTextureEffectsSection)+") at : "+repr("{0:8X}".format(file.tell())))

        # affect flame animations not position or color
        # type 01 is a sprite sheet animation
        # type 02 is a texture translation animation

        #                type
        # in MAP148.MPD
        # 0400 0000 0001 0601 FEFF FFFF 0200 0000 0200 0000 0004 0000 0004 0000 0000 0000 0000 0000
        # DC10 0000 0100 0201 A040 2020 A043 1F0F 0001 0000 000E 1E00 0E00 0E00 A000 4000
        # 0411 0000 0100 0201 A040 2020 A043 1F0F 0001 0000 000E 1E00 0E00 0E00 A000 4000
        # B410 0000 0100 0201 A040 2020 A043 1F0F 0001 0000 000E 1E00 0E00 0E00 A000 4000
        # 0012 1F08 0100 0100 0100 0000 4002 8000 2000 4000

        # in MAP009.MPD (must have 4 effects : 2 candles, 1 exit arrow, 1 fire)
        #  ?   ite  numsprites             x h  y    w
        # 0101 03   04 0100 0101 0000 0000 A801 6000 0200 1000  // candles
        # 0102 07   08 0100 0101 0000 0000 8001 A000 0400 2000  // fire
        #                type  speed   tex co  dest co   ?  transl
        # 3CC9 0000 0100 02    01       A040   2020    A041 1F0F    0001 0100 000E 1E00 0E00 0E00 A000 4000 // exit arrow
        # experiences :
        # 010103040100010100000000A8016000020010000102070801000101000000008001A000040020003CC9000001000201A0402020A0411F0F00010100000E1E000E000E00A0004000 // untouched
        # 010103040100010100000000A8016000020010000000070801000101000000008001A000040020003CC9000001000201A0402020A0411F0F00010100000E1E000E000E00A0004000


        # in MAP010.MPD
        # 8400 0000 0001 0601 0300 0000 FEFF FFFF 0200 0000 000C 0000 000C 0000 0000 0000 0000 0000
        # 0103 0304 0100 0101 0000 0000 A801 6000 0200 1000
        # 0104 0708 0100 0101 0000 0000 8001 A000 0400 2000
        # 8C09 0000 0100 0201 A040 2020 A04C 1F0F 0001 0100 000E 1E00 0E00 0E00 A000 4000
        # 2C77 0000 0100 0201 A040 2020 A04C 1F0F 0001 0100 000E 1E00 0E00 0E00 A000 4000
        # 4409 0000 0001 0601 FEFF FFFF 0200 0000 0200 0000 0004 0000 0004 0000 0000 0000 0000 0000

        # in MAP011.MPD
        # 0401 0000 0001 0601 0000 0000 FEFF FFFF 0200 0000 0000 0000 000C 0000 0000 0000 0000 0000
        # 4401 0000 0001 0601 0000 0000 0200 0000 0200 0000 0000 0000 0004 0000 0000 0000 0000 0000
        # 0002 0304 0100 0101 0000 0000 A801 6000 0200 1000
        # 0001 0708 0100 0101 0000 0000 8001 A000 0400 2000
        # DC0B 0000 0100 0201 A040 2020 A04E 1F0F 0001 0000 000E 1E00 0E00 0E00 A000 4000
        # 8C0B 0000 0100 0201 A040 2020 A04E 1F0F 0001 0000 000E 1E00 0E00 0E00 A000 4000

        # in MAP034.MPD
        # 8401 0000 0001 0601 0000 0000 FEFF FFFF 0200 0000 0000 0000 000C 0000 0000 0000 0000 0000
        # C401 0000 0001 0601 0000 0000 FEFF FFFF 0200 0000 0000 0000 000C 0000 0000 0000 0000 0000
        # 0402 0000 0001 0601 0000 0000 0200 0000 0200 0000 0000 0000 0004 0000 0000 0000 0000 0000
        # 0101 0708 0100 0101 0000 0000 8001 A000 0400 2000
        # AC0A 0000 0100 0201 A040 2020 A04C 1F0F 0001 0100 1E00 0E00 0E0E 0000 A000 4000
        # 0C0A 0000 0100 0201 A040 2020 A04C 1F0F 0001 0100 1E00 0E00 0E0E 0000 A000 4000
        # 5C0A 0000 0100 0201 A040 2020 A04C 1F0F 0001 0100 1E00 0E00 0E0E 0000 A000 4000

        # in MAP027.MPD ( 1 lantern, 1 candle, 1 save, 1 chest, 2 exits)
        # 8400 0000 0001 0603 0000 0000 FEFF FFFF 0300 0000 0000 0000 000E 0000 0000 0000 0000 0000
        # 0103 0304 0100 0101 0000 0000 A801 6000 0200 1000
        # 0104 0708 0100 0101 0000 0000 8001 A000 0400 2000
        # 1C11 0000 0100 0201 A040 2020 A14E 1F0F 0001 0100 000E 1E00 0E00 0E00 A100 5100
        # FC10 0000 0100 0201 A040 2020 A04F 1F0F 0001 0100 000E 1E00 0E00 0E00 A000 4000
        # save
        # 2C0A 0000 0100 0201 8040 2040 9057 0F1F 0001 0100 0000 0E0E 1E00 1E00 9000 4000
        # 540A 0000 0100 0201 8040 2040 9057 0F1F 0001 0100 0000 0E0E 1E00 1E00 9000 4000
        # 7C0A 0000 0100 0201 8040 2040 8057 111F 0001 0100 0000 1010 1E00 1E00 8000 4000
        # A40A 0000 0100 0201 8040 2040 8057 111F 0001 0100 0000 1010 1E00 1E00 8000 4000
        # 940B 0000 0100 0201 8040 2040 9057 0F1F 0001 0100 0000 0E0E 1E00 1E00 9000 4000
        # 6C0B 0000 0100 0201 8040 2040 9057 0F1F 0001 0100 0000 0E0E 1E00 1E00 9000 4000
        # 440B 0000 0100 0201 8040 2040 8057 111F 0001 0100 0000 1010 1E00 1E00 8000 4000
        # 8C09 0000 0100 0201 8040 2040 8057 111F 0001 0100 0000 1010 1E00 1E00 8000 4000
        # 040A 0000 0100 0201 8040 2040 9057 0F1F 0001 0100 0000 0E0E 1E00 1E00 9000 4000
        # DC09 0000 0100 0201 8040 2040 9057 0F1F 0001 0100 0000 0E0E 1E00 1E00 9000 4000
        # F40A 0000 0100 0201 8040 2040 8057 111F 0001 0100 0000 1010 1E00 1E00 8000 4000
        # CC0A 0000 0100 0201 8040 2040 8057 111F 0001 0100 0000 1010 1E00 1E00 8000 4000
        # B409 0000 0100 0201 8040 2040 9057 0F1F 0001 0100 0000 0E0E 1E00 1E00 9000 4000
        # 3C09 0000 0100 0201 8040 2040 9057 0F1F 0001 0100 0000 0E0E 1E00 1E00 9000 4000
        # 1C0B 0000 0100 0201 8040 2040 8057 111F 0001 0100 0000 1010 1E00 1E00 8000 4000
        # 6409 0000 0100 0201 8040 2040 8057 111F 0001 0100 0000 1010 1E00 1E00 8000 4000
        file.seek(self.lenTextureEffectsSection, 1)

        #print("SubSection0D  len("+repr(self.lenSubSection0D)+") at : "+repr("{0:8X}".format(file.tell())))
        # no noticable effect when full of 00
        # black screen when filled with FF
        # dunno what it can be
        # 0100 0100 FF00 0000
        # 0800 0600 0000 0100 0400 0200 0000 0000 0100 0000 0200 0000 1C00 0800 0064 0000 00E4 FFFF 0064 0000 0000 0000 0000 0000 0000 0000 1400 0100 4000 0000 C0FF 0000 0000 0000 0000 0000
        # 0800 0500 8000 0200 0400 0200 0000 0000 0100 0000 0200 0000 1C00 0800 0084 0000 00E4 FFFF 0044 0000 0000 0000 0000 0000 0000 0000 1400 0100 C0FF 0000 4000 0000 0000 0000 0000 0000
        # 0800 0500 8000 0200 0400 0200 0000 0000 0100 0000 0200 0000 1C00 0800 0064 0000 00E4 FFFF 0064 0000 0000 0000 0000 0000 0000 0000 1400 0100 4000 0000 C0FF 0000 0000 0000 0000 0000
        # 0800 0500 8000 0200 0800 0500 3C00 0000 1C00 0800 0084 0000 00E4 FFFF 0044 0000 0000 0000 0000 0000 0000 0000 1400 0100 C0FF 0000 4000 0000 0000 0000 0000 0000
        # 0800 0500 8000 0200 0800 0500 3C00 0000 80FF 0B00 0000 0000
        #
        # 0100 0100 FF00 0000
        # 0800 0600 0000 0100 0400 0200 0000 0000 0100 0000 0200 0000 1C00 0800 0064 0000 00E4 FFFF 0064 0000 0000 0000 0000 0000 0000 0000 1400 0100 4000 0000 C0FF 0000 0000 0000 0000 0000
        # 0800 0500 8000 0200 0400 0200 0000 0000 0100 0000 0200 0000 1C00 0800 0084 0000 00E4 FFFF 0044 0000 0000 0000 0000 0000 0000 0000 1400 0100 C0FF 0000 4000 0000 0000 0000 0000 0000
        # 0800 0500 8000 0200 0400 0200 0000 0000 0100 0000 0200 0000 1C00 0800 0064 0000 00E4 FFFF 0064 0000 0000 0000 0000 0000 0000 0000 1400 0100 4000 0000 C0FF 0000 0000 0000 0000 0000
        # 0800 0500 8000 0200 0800 0500 3C00 0000 1C00 0800 0084 0000 00E4 FFFF 0044 0000 0000 0000 0000 0000 0000 0000 1400 0100 C0FF 0000 4000 0000 0000 0000 0000 0000
        # 0800 0500 8000 0200 0800 0500 3C00 0000 80FF 0B00 0000 0000
        #
        # 0100 0100 FF00 0000
        # 0800 0600 0000 0100 0400 0200 0000 0000 0100 0000 0200 0000 1C00 0800 0064 0000 00E4 FFFF 0064 0000 0000 0000 0000 0000 0000 0000 1400 0100 4000 0000 C0FF 0000 0000 0000 0000 0000
        # 0800 0500 8000 0200 0400 0200 0000 0000 0100 0000 0200 0000 1C00 0800 0084 0000 00E4 FFFF 0044 0000 0000 0000 0000 0000 0000 0000 1400 0100 C0FF 0000 4000 0000 0000 0000 0000 0000
        # 0800 0500 8000 0200 0400 0200 0000 0000 0100 0000 0200 0000 1C00 0800 0064 0000 00E4 FFFF 0064 0000 0000 0000 0000 0000 0000 0000 1400 0100 4000 0000 C0FF 0000 0000 0000 0000 0000
        # 0800 0500 8000 0200 0800 0500 3C00 0000 1C00 0800 0084 0000 00E4 FFFF 0044 0000 0000 0000 0000 0000 0000 0000 1400 0100 C0FF 0000 4000 0000 0000 0000 0000 0000
        # 0800 0500 8000 0200 0800 0500 3C00 0000 80FF 0B00 0000 0000

        # 01000100FF0000000800060000000100040002000000000001000000020000001C0008000064000000E40000006400000000000000000000000000001400010040000000C0FF000000000000000000000800050080000200040002000000000001000000020000001C0008000084000000E4FFFF0044000000000000000000000000000014000100C0FF00004000000000000000000000000800050080000200040002000000000001000000020000001C0008000064000000E4FFFF006400000000000000000000000000001400010040000000C0FF000000000000000000000800050080000200080005003C0000001C0008000084000000E4FFFF0044000000000000000000000000000014000100C0FF00004000000000000000000000000800050080000200080005003C00000080FF0B0000000000
        # 00000000FF0000000800060000000100040002000000000001000000020000001C0008000064000000E40000006400000000000000000000000000001400010040000000C0FF000000000000000000000800050080000200040002000000000001000000020000001C0008000084000000E4FFFF0044000000000000000000000000000014000100C0FF00004000000000000000000000000800050080000200040002000000000001000000020000001C0008000064000000E4FFFF006400000000000000000000000000001400010040000000C0FF000000000000000000000800050080000200080005003C0000001C0008000084000000E4FFFF0044000000000000000000000000000014000100C0FF00004000000000000000000000000800050080000200080005003C00000080FF0B0000000000
        file.seek(self.lenSubSection0D, 1)

        #print("SubSection0E  len("+repr(self.lenSubSection0E)+") at : "+repr("{0:8X}".format(file.tell())))
        # black screen when nulled
        file.seek(self.lenSubSection0E, 1)

        #print("MiniMapSection  len("+repr(self.lenMiniMapSection)+") at : "+repr("{0:8X}".format(file.tell())))
        endMiniMap = file.tell() + self.lenMiniMapSection
        self.arm = ARM.ARM()
        self.arm.filesize = self.lenMiniMapSection
        self.arm.parse(file)
        file.seek(endMiniMap)

        #print("SubSection10  len("+repr(self.lenSubSection10)+") at : "+repr("{0:8X}".format(file.tell())))
        file.seek(self.lenSubSection10, 1)

        #print("SubSection11  len("+repr(self.lenSubSection11)+") at : "+repr("{0:8X}".format(file.tell())))
        # in MAP013.MPD
        # no noticable effect when full of 00 or FF
        # 40300600050B0F151A1C000060300600050B0F151A1C000080300600050B0F151A1C0000A0300600050B0F151A1C000041300600050B0F151A1C000061300600050B0F151A1C000081300600050B0F151A1C0000A1300600050B0F151A1C000042300600050B0F151A1C000062300600050B0F151A1C000082300600050B0F151A1C0000A2300600050B0F151A1C000023300600050B0F151A1C000043300600050B0F151A1C000063300600050B0F151A1C000083300600050B0F151A1C0000A3300600050B0F151A1C0000
        # 000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
        file.seek(self.lenSubSection11, 1)


        #print("FloatingStoneSection  len("+repr(self.lenFloatingStoneSection)+") at : "+repr("{0:8X}".format(file.tell())))
        # SubSection12
        # +$00    1    mpdGroupId (ref to the floating stone)
        # +$01    1    ? translation type maybe
        # +$02    2    ? init position ?
        # +$04    2    ? init position ?
        # +$06    2    padding
        # +$08    4    pos 1 X
        # +$012   4    pos 1 Z (or Y but height)
        # +$016   4    pos 1 Y
        # +$020   4    delay at pos 1
        # +$024   4    pos 2 X
        # +$028   4    pos 2 Z
        # +$032   4    pos 2 Y
        # +$036   4    delay at pos 2

        # in MAP014.MPD
        #                end  x       z       y   delay start x       z       y   delay                                                                                                                                                                                                                                                                 init  X       Z       Y
        # 0234FF0FFE0300000000840000001C00000044003C0000000000640000001C00000064003C000000AEAD400002000000010000000100000000000000050000000000000000000080FBA4FFFF00000000055B00005A000000055B000000000000FBA4FFFF5A000000EE037900A8FE4000D0037900E4FC66005F61400058FA6600A2F3400040000000C8FE40008161400058FA6600A0F3400040000000AF38400058FA6600A0F340000000840000001C000000440000000000
        # 0234FF0FFE0300000000840000001C00000044003C0000000000640000001C00000064003C000000AEAD400002000000010000000100000000000000050000000000000000000080FBA4FFFF00000000055B00005A000000055B000000000000FBA4FFFF5A000000EE037900A8FE4000D0037900E4FC66005F61400058FA6600A2F3400040000000C8FE40008161400058FA6600A0F3400040000000AF38400058FA6600A0F340000000840000001C000000440000000000
        file.seek(self.lenFloatingStoneSection, 1)


        #print("ChestInteractionSection  len("+repr(self.lenChestInteractionSection)+") at : "+repr("{0:8X}".format(file.tell())))
        # SubSection13
        # chest interaction section
        file.seek(self.lenChestInteractionSection, 1)

        #print("AKAOSubSection  len("+repr(self.lenAKAOSubSection)+") at : "+repr("{0:8X}".format(file.tell())))
        file.seek(self.lenAKAOSubSection, 1)

        #print("SubSection15  len("+repr(self.lenSubSection15)+") at : "+repr("{0:8X}".format(file.tell())))
        file.seek(self.lenSubSection15, 1)

        #print("SubSection16  len("+repr(self.lenSubSection16)+") at : "+repr("{0:8X}".format(file.tell())))
        file.seek(self.lenSubSection16, 1)

        #print("SubSection17  len("+repr(self.lenSubSection17)+") at : "+repr("{0:8X}".format(file.tell())))
        file.seek(self.lenSubSection17, 1)

        #print("CameraAreaSection  len("+repr(self.lenCameraAreaSection)+") at : "+repr("{0:8X}".format(file.tell())))
        # SubSection18 is camera area in tile
        # 0000 0000 0700 1200 -> meens the camera can move 7 tiles in X and 18 tiles in Y
        # values are close to roomX & roomY
        ints =  struct.unpack("4H", file.read(8))
        camX = ints[2]
        camY = ints[3]



    def blenderize(self):
        #print("blenderizing MPD Room...")
        self.blender = BlenderDatas()
        idx = 0
        for group in self.groups:
            for face in group.faces:
                self.blender.vertices.append(face.vertices[0].blenderSwaped())
                self.blender.vertices.append(face.vertices[1].blenderSwaped())
                self.blender.vertices.append(face.vertices[2].blenderSwaped())
                self.blender.matrefs.append(face.materialRef)
                # MPD faces has a special vertices order because normals must be inside instead of outside
                # maybe we can use MeshPolygon.flip() ?
                # https://docs.blender.org/api/current/bpy.types.MeshPolygon.html
                if face.quad == True:
                    self.blender.vertices.append(face.vertices[3].blenderSwaped())
                    self.blender.faces.append((int(idx+3), int(idx+1), int(idx+0), int(idx+2)))
                    self.blender.uvs.extend([face.uv[3], face.uv[2], face.uv[1], face.uv[0]])
                    self.blender.colors.extend([face.colors[3], face.colors[1], face.colors[0], face.colors[2]])
                    idx += 4
                else:
                    self.blender.faces.append((int(idx+2), int(idx+1), int(idx+0)))
                    self.blender.uvs.extend([face.uv[0], face.uv[2], face.uv[1]])
                    self.blender.colors.extend([face.colors[2], face.colors[1], face.colors[0]])
                    idx += 3

class BlenderDatas:
    def __init__(self):
        self.vertices = []
        self.faces = []
        self.colors = []
        self.uvs = []
        self.matrefs = []

class CollisionTile:
    def __init__(self):
        self.index = 0
        self.floor = 0
        self.floorMode = 0
        self.ceil = 0
        self.ceilMode = 0
    def __repr__(self):
        return ("CollisionTile "+repr(self.index)+" : "+" floor : "+repr(self.floor)+", floorMode : "+repr(self.floorMode)+", ceil : "+repr(self.ceil)+", ceilMode : "+repr(self.ceilMode))


class TileMode(Enum):
    FULL = 0
    FLAT = 1
    RAMP1Xp = 2
    RAMP1Xn = 3
    RAMP1Yp = 4
    RAMP1Yn = 5
    RAMP2Xp = 6
    RAMP2Xn = 7
    RAMP2Yp = 8
    RAMP2Yn = 9
    BUMP = 10
    DIAGX = 11
    DIAGY = 12
    VOID = 13
    CHEST = 14
    HALF = 15
