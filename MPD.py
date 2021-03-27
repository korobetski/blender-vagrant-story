bl_info = {
    "name": "Vagrant Story file formats Add-on",
    "description": "Import-Export Vagrant Story file formats (WEP, SHP, SEQ, ZUD, MPD, ZND).",
    "author": "Sigfrid Korobetski (LunaticChimera)",
    "version": (2, 0),
    "blender": (2, 92, 0),
    "location": "File > Import-Export",
    "category": "Import-Export",
}

#http://datacrystal.romhacking.net/wiki/Vagrant_Story:MPD_files

import struct
from enum import Enum

import bpy

import bmesh
from bpy.props import BoolProperty, EnumProperty, FloatProperty, StringProperty
from bpy_extras.io_utils import ExportHelper, ImportHelper

from . import GroupSection, ZND, VS


class Import(bpy.types.Operator, ImportHelper):
    """Load a MPD file"""

    bl_idname = "import_map_mesh.mpd"
    bl_label = "Import MPD"
    filename_ext = ".MPD"

    filepath: bpy.props.StringProperty(default="", subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.MPD", options={"HIDDEN"})

    def execute(self, context):
        keywords = self.as_keywords(ignore=("axis_forward","axis_up","filter_glob",))
        BlenderImport(self, context, **keywords)

        return {"FINISHED"}


def BlenderImport(operator, context, filepath):
    mpd = MPD()
    # we read datas from a file
    mpd.loadFromFile(filepath)

    print("filepath : "+filepath)
    print("bpy.path.abspath : "+bpy.path.abspath(filepath))
    print("bpy.path.basename : "+bpy.path.basename(filepath))

    zndFileName = VS.MDPToZND(bpy.path.basename(filepath))
    print("Corresponding ZND : "+zndFileName)
    zndfilepath = filepath.replace(bpy.path.basename(filepath), zndFileName)
    print("zndfilepath : "+zndfilepath)

    znd = ZND.ZND()
    znd.loadFromFile(zndfilepath)
    
    # Creating Geometry and Meshes for Blender
    mpd.buildGeometry(znd)


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
        
        # RoomSection
        # file.seek(self.header.ptrRoomSection) # useless
        if self.header.lenRoomSection > 96:
            self.room.feed(file)
        
        print("lenDoorSection : "+repr(self.header.lenDoorSection))
        if self.header.lenDoorSection > 0:
            file.seek(self.header.ptrDoorSection)
            

    def buildGeometry(self, znd = None):
        print("MPD Building...")
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
            mat.blend_method = "CLIP"  # to handle alpha cutout
            mat.use_backface_culling = True
            # maybe i should consider using a simpler material... VS doesn't need a PBR Material :D
            bsdf = mat.node_tree.nodes["Principled BSDF"]
            bsdf.inputs["Specular"].default_value = 0
            bsdf.inputs["Metallic"].default_value = 0
            texImage = mat.node_tree.nodes.new("ShaderNodeTexImage")
            texImage.image = bpy.data.images.new(str(ref+"_TEX"), 256, 256)
            texImage.image.pixels = znd.getPixels(ref)
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

        # WIP reversing collisions
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
        
        print("Room Section  len("+repr(self.lenRoomSection)+") at : "+repr(self.ptrRoomSection))
        print("Cleared Section  len("+repr(self.lenClearedSection)+") at : "+repr(self.ptrClearedSection))
        print("Script Section  len("+repr(self.lenScriptSection)+") at : "+repr(self.ptrScriptSection))
        print("Door Section  len("+repr(self.lenDoorSection)+") at : "+repr(self.ptrDoorSection))
        print("Enemy Section  len("+repr(self.lenEnemySection)+") at : "+repr(self.ptrEnemySection))
        print("Treasure Section  len("+repr(self.lenTreasureSection)+") at : "+repr(self.ptrTreasureSection))



class Room:
    def __init__(self):
        self.lenGeometrySection = 0
        self.lenCollisionSection = 0
        self.lenSubSection03 = 0
        self.lenDoorSection = 0
        self.lenLightingSection = 0
        self.lenSubSection06 = 0
        self.lenSubSection07 = 0
        self.lenSubSection08 = 0
        self.lenSubSection09 = 0
        self.lenSubSection0A = 0
        self.lenSubSection0B = 0
        self.lenTextureEffectsSection = 0
        self.lenSubSection0D = 0
        self.lenSubSection0E = 0
        self.lenSubSection0F = 0
        self.lenSubSection10 = 0
        self.lenSubSection11 = 0
        self.lenSubSection12 = 0
        self.lenSubSection13 = 0
        self.lenAKAOSubSection = 0
        self.lenSubSection15 = 0
        self.lenSubSection16 = 0
        self.lenSubSection17 = 0
        self.lenSubSection18 = 0
        self.numGroups = 0
        self.groups = []
        self.materialRefs = []
        self.blender = BlenderDatas()
        self.roomX = 0
        self.roomY = 0
        self.collisions = []
        self.tileModes = []
    def feed(self, file):
        (
            self.lenGeometrySection,
            self.lenCollisionSection,
            self.lenSubSection03,
            self.lenDoorSection,
            self.lenLightingSection,
            self.lenSubSection06,
            self.lenSubSection07,
            self.lenSubSection08,
            self.lenSubSection09,
            self.lenSubSection0A,
            self.lenSubSection0B,
            self.lenTextureEffectsSection,
        ) = struct.unpack("12I", file.read(48))
        (
            self.lenSubSection0D,
            self.lenSubSection0E,
            self.lenSubSection0F,
            self.lenSubSection10,
            self.lenSubSection11,
            self.lenSubSection12,
            self.lenSubSection13,
            self.lenAKAOSubSection,
            self.lenSubSection15,
            self.lenSubSection16,
            self.lenSubSection17,
            self.lenSubSection18,
        ) = struct.unpack("12I", file.read(48))

        # Geometry Section  
        print("Geometry Section  len("+repr(self.lenGeometrySection)+") at : "+repr(file.tell()))

        if self.lenGeometrySection > 4:
            # GeometrySection (Polygon groups)
            self.numGroups = struct.unpack("I", file.read(4))[0]
            self.groups = []
            self.materialRefs = []
            for i in range(0, self.numGroups):
                group = GroupSection.MDPGroup()
                group.name = "Group "+str(i)
                group.feed(file)
                self.groups.append(group)

            for i in range(0, self.numGroups):
                group = self.groups[i]
                group.feedFaces(file)

                # we gather all needed material refs
                for ref in group.materialRefs:
                    if self.materialRefs.__contains__(ref) == False:
                        self.materialRefs.append(ref)
        
        # Collision Section
        print("Collision Section  len("+repr(self.lenCollisionSection)+") at : "+repr(file.tell()))
        ptrEndCollision = file.tell() + self.lenCollisionSection
        #file.seek(self.lenCollisionSection, 1)
        self.roomX, self.roomY, unk1, numTileModes = struct.unpack("4H", file.read(8))
        # unk1 seems to be always 0x00
        print("roomX : "+repr(self.roomX)+", roomY : "+repr(self.roomY)+", unk1 : "+repr(unk1)+", numTileModes : "+repr(numTileModes))
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


        # we skip unknown section
        print("SubSection03  len("+repr(self.lenSubSection03)+") at : "+repr(file.tell()))
        # for i in range(0, self.roomX * self.roomY):
        #   file.read(4)
        file.seek(ptrEndCollision+self.lenSubSection03)

        # Door section (maybe more a warp section)
        print("Room Door Section  len("+repr(self.lenDoorSection)+") at : "+repr(file.tell()))
        # we must be in room doors section
        numDoors = round(self.lenDoorSection /0x0C)
        if self.lenDoorSection >= 0x0C:
            for i in range(0, numDoors):
                destZone, destRoom = struct.unpack("2B", file.read(2))
                rawTileId = struct.unpack("H", file.read(2))[0]
                dunk = struct.unpack("4B", file.read(4))
                doorId = struct.unpack("I", file.read(4))[0]
                # the door section seems to use a grid of 32x32
                # so we need to adapt tileId to the current MPD room grid to figure where the door must be
                tileId = round(rawTileId / 32) * self.roomX + (rawTileId % 32)
                print("MPD door : "+" destZone : "+repr(destZone)+", destRoom : "+repr(destRoom)+" doorId : "+repr(doorId)+" rawTileId : "+repr(rawTileId)+" tileId : "+repr(tileId)+" dunk : "+repr(dunk))
        
        print("LightingSection  len("+repr(self.lenLightingSection)+") at : "+repr(file.tell()))
        file.seek(self.lenLightingSection, 1)
        
        print("SubSection06  len("+repr(self.lenSubSection06)+") at : "+repr(file.tell()))
        # looks like colors ?
        file.seek(self.lenSubSection06, 1)
        
        print("SubSection07  len("+repr(self.lenSubSection07)+") at : "+repr(file.tell()))
        # 256 * 0x00 in MAP014.MPD
        file.seek(self.lenSubSection07, 1)
        
        print("SubSection08  len("+repr(self.lenSubSection08)+") at : "+repr(file.tell()))
        file.seek(self.lenSubSection08, 1)
        
        print("SubSection09  len("+repr(self.lenSubSection09)+") at : "+repr(file.tell()))
        # 0100 0800 0000 1000 01FF 0200 in MAP014.MPD
        file.seek(self.lenSubSection09, 1)
        
        print("SubSection0A  len("+repr(self.lenSubSection0A)+") at : "+repr(file.tell()))
        file.seek(self.lenSubSection0A, 1)
        
        print("SubSection0B  len("+repr(self.lenSubSection0B)+") at : "+repr(file.tell()))
        # 0000 0000 0000 0000 0000 0000 0000 0000 
        # 0000 0000 0000 0000 0000 0000 0000 0000
        # 0000 0000 0000 0000 0000 0000 0100 0000
        # 0000 0000 0000 0000 0000 0000 0000 0000
        # 0000 0000 0000 0000 0000 0000 0000 0000
        # 0100 FFFF FFFF 0900  in MAP014.MPD
        file.seek(self.lenSubSection0B, 1)
        
        print("TextureEffectsSection  len("+repr(self.lenTextureEffectsSection)+") at : "+repr(file.tell()))
        # 96 + 16 * 36 ?
        file.seek(self.lenTextureEffectsSection, 1)
        
        print("SubSection0D  len("+repr(self.lenSubSection0D)+") at : "+repr(file.tell()))
        file.seek(self.lenSubSection0D, 1)
        
        print("SubSection0E  len("+repr(self.lenSubSection0E)+") at : "+repr(file.tell()))
        file.seek(self.lenSubSection0E, 1)
        
        print("SubSection0F  len("+repr(self.lenSubSection0F)+") at : "+repr(file.tell()))
        # 32 bytes header + x*8 bytes blocks
        file.seek(self.lenSubSection0F, 1)
        
        print("SubSection10  len("+repr(self.lenSubSection10)+") at : "+repr(file.tell()))
        file.seek(self.lenSubSection10, 1)
        
        print("SubSection11  len("+repr(self.lenSubSection11)+") at : "+repr(file.tell()))
        file.seek(self.lenSubSection11, 1)
        
        print("SubSection12  len("+repr(self.lenSubSection12)+") at : "+repr(file.tell()))
        file.seek(self.lenSubSection12, 1)
        
        print("SubSection13  len("+repr(self.lenSubSection13)+") at : "+repr(file.tell()))
        file.seek(self.lenSubSection13, 1)
        
        print("AKAOSubSection  len("+repr(self.lenAKAOSubSection)+") at : "+repr(file.tell()))
        file.seek(self.lenAKAOSubSection, 1)
        
        print("SubSection15  len("+repr(self.lenSubSection15)+") at : "+repr(file.tell()))
        file.seek(self.lenSubSection15, 1)
        
        print("SubSection16  len("+repr(self.lenSubSection16)+") at : "+repr(file.tell()))
        file.seek(self.lenSubSection16, 1)
        
        print("SubSection17  len("+repr(self.lenSubSection17)+") at : "+repr(file.tell()))
        file.seek(self.lenSubSection17, 1)
        
        print("SubSection18  len("+repr(self.lenSubSection18)+") at : "+repr(file.tell()))
        file.seek(self.lenSubSection18, 1)


                        
    def blenderize(self):
        print("blenderizing MPD Room...")
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
