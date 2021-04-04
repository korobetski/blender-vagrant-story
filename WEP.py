bl_info = {
    "name": "Vagrant Story file formats Add-on",
    "description": "Import-Export Vagrant Story file formats (WEP, SHP, SEQ, ZUD, MPD, ZND, P, FBT, FBC).",
    "author": "Sigfrid Korobetski (LunaticChimera)",
    "version": (2, 1),
    "blender": (2, 92, 0),
    "location": "File > Import-Export",
    "category": "Import-Export",
}


# http://datacrystal.romhacking.net/wiki/Vagrant_Story:WEP_files


import os
import math
import struct

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, StringProperty, CollectionProperty
from bpy_extras.io_utils import ExportHelper, ImportHelper

from . import TIM, VS, BoneSection, FaceSection, GroupSection, VertexSection, color


# CALLED BY BLENDER
class Import(bpy.types.Operator, ImportHelper):
    """Load a WEP file"""

    bl_idname = "import_mesh.wep"
    bl_label = "Import WEP"
    filename_ext = ".WEP"

    filepath: bpy.props.StringProperty(default="", subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.WEP", options={"HIDDEN"})

    def execute(self, context):
        keywords = self.as_keywords(ignore=("axis_forward", "axis_up", "filter_glob"))
        BlenderImport(self, context, **keywords)

        return {"FINISHED"}

# CALLED BY BLENDER
class Export(bpy.types.Operator, ExportHelper):
    """Save a WEP file"""

    bl_idname = "export_mesh.wep"
    bl_label = "Export WEP"
    check_extension = True
    filename_ext = ".WEP"

    filter_glob: bpy.props.StringProperty(default="*.WEP", options={"HIDDEN"})

    def execute(self, context):
        keywords = self.as_keywords(ignore=("axis_forward", "axis_up", "filter_glob", "check_existing"))
        check = False
        check = BlenderExport(self, context, **keywords)
        return check


def BlenderImport(operator, context, filepath):
    wep = WEP()
    # we read datas from a file
    wep.loadFromFile(filepath)
    # we build geometry from datas
    wep.buildGeometry()
    return {"FINISHED"}

def BlenderExport(operator, context, filepath):
    scene = context.scene
    obj = bpy.context.view_layer.objects.active
    mesh = obj.to_mesh()
    wep = WEP()
    wep.fromBlenderMesh(mesh)

    # Write geometry to file
    filepath = os.fsencode(filepath)
    fp = open(filepath, "w+b")
    bytes_array = bytearray(wep.tobin())
    fp.write(bytes_array)
    fp.close()

    return {"FINISHED"}
    
class WEP:
    def __init__(self):
        self.name = ".WEP"
        self.header = WEPHeader()
        self.bones = []
        self.groups = []
        self.vertices = []
        self.faces = []
        self.tim = TIM.WEPTIM()
        self.rotations = [
            (0, 0, 0, 7),
            (0, 0, 0, 7),
            (0, 0, 0, 7)
        ]
    def __repr__(self):
        return("(--"+repr(self.name)+".WEP-- | "+repr(self.header)+")")
    def loadFromFile(self, filepath):
        # Open a WEP file and parse it
        file = open(filepath, "rb")
        self.name = bpy.path.display_name(filepath)
        self.parse(file)
        file.close()
    def parse(self, file):
        signature = file.read(4)
        if signature != VS.SIG:
            return

        # WEP HEADER
        self.header.feed(file)
        print(self)

        # WEP BONES SECTION
        self.bones = BoneSection.parse(file, self.header.numBones)

        # WEP GROUPS SECTION
        if self.header.groupPtr != file.tell():
            print("WARNING : Pointer group : bad position")
            file.seek(self.header.groupPtr)
        self.groups = GroupSection.parse(file, self.header.numGroups, self.bones)

        # WEP VERTEX SECTION
        # we get numVertices by checking the last group datas
        self.numVertices = 0
        if len(self.groups) > 0:
            self.numVertices = self.groups[len(self.groups)- 1].numVertices
        if self.header.vertexPtr != file.tell():
            print("WARNING : Pointer vertex : bad position")
            file.seek(self.header.vertexPtr)
        self.vertices = VertexSection.parse(file, self.numVertices, self.groups)

        # hard fixes for staves 39.WEP to 3F.WEP
        staves = ["39", "3A", "3B", "3C", "3D", "3E", "3F"]
        if staves.__contains__(self.name):
            # its a staff, so we need to correct vertices of the first group
            for i in range(self.groups[0].numVertices):
                self.vertices[i].x = (-self.groups[0].bone.length * 2 - self.vertices[i].x)  # its work but why ?
                self.vertices[i].y = -self.vertices[i].y  # simple invert

        # WEP FACES SECTION
        if self.header.polygonPtr != file.tell():
            print("WARNING : Pointer face : bad position")
            file.seek(self.header.polygonPtr)
        self.faces = FaceSection.parse(file, self.header.numFaces)

        # WEP TEXTURE SECTION
        if self.header.texturePtr != file.tell():
            print("WARNING : Pointer Texture : bad position")
            file.seek(self.header.texturePtr)
        self.tim.feed(file)

        self.rotations = []
        # 00000000000007000000FF0F0000070000000000B0000700
        # 0000000000000700000000000000070000000000B0000700
        # Rotations
        # not fully understood yet
        # the first row is always 0000000000000700 for all 127 .WEP files change values doesn't have a visual effect in game
        # the second row seems to control rotations, the last value 0x0700 doesn't have a visual effect in game (the last value is always 0x0700 every WEP every row)
        for i in range(0, 3):  # 3 axis ? 3 bones ?
            # tested in game on Z048U26.ZUD
            # default u2 is FF0F it can be ? 4095 i don't think its 65295
            # with u2 = FFC3 the weapon seems to rotate 90° (or maybe a multiple)
            # with u2 = 0077 the weapon seems to rotate 180°(or maybe a multiple)
            u1, u2, u3, u4 = struct.unpack("<4h", file.read(8))
            print("rots : "+" u1 : "+repr(u1)+" - u2 : "+repr(u2)+" - u3 : "+repr(u3)+" - u4 : "+repr(u4))
            self.rotations.append([u1, u2, u3, u4])
    def buildGeometry(self, material_index = 0):
        print("WEP Building...")

        # Creating Geometry and Mesh for Blender
        mesh_name = self.name
        blender_mesh = bpy.data.meshes.new(name=mesh_name + "_MESH")
        blender_mesh.from_pydata(self.getVerticesForBlender(), [], self.getFacesForBlender())

        # https://docs.blender.org/api/current/bpy.types.Mesh.html#bpy.types.Mesh.polygon_layers_int
        # we can't store datas on faces, so we store face datas in mesh polygon layers instead
        side_layer = blender_mesh.polygon_layers_int.new(name='side')
        flag_layer = blender_mesh.polygon_layers_int.new(name='flag')
        for face in self.faces:
            side_layer.data[face.index].value = face.side
            flag_layer.data[face.index].value = face.flag

        # Creating Materials & Textures for Blender
        # https://docs.blender.org/api/current/bpy.types.Material.html
        # https://github.com/mac7ua/Palette-Generator/blob/master/Palette_Generator.py

        palette = bpy.data.palettes.new(name=str(self.name + ".WEP_Common_Palette"))
        for col in self.tim.handleColors:
            palcol = palette.colors.new()
            palcol.color = (col.R/255, col.G/255, col.B/255)

        vs_weapon_materials = ["Wood", "Leather", "Bronze", "Iron", "Hagane", "Silver", "Damascus"]
        for i in range(0, len(self.tim.textures)):
            mat = bpy.data.materials.new(name=str(self.name + "_"+vs_weapon_materials[i]+"_Mat"))
            # we add the palette reference in a custom property of the material
            mat.palette.ref = str(self.name + ".WEP_"+vs_weapon_materials[i]+"_Palette")
            mat.use_nodes = True
            mat.blend_method = "CLIP"  # to handle alpha cutout

            # we save the palettes
            palette = bpy.data.palettes.new(name=str(self.name + ".WEP_"+vs_weapon_materials[i]+"_Palette"))
            # we skip handle colors thats why we start at 16
            for j in range(16, 48):
                col = self.tim.palletColors[i][j]
                palcol = palette.colors.new()
                palcol.color = (col.R/255, col.G/255, col.B/255)

            # maybe i should consider using a simpler material... VS doesn't need a PBR Material :D
            bsdf = mat.node_tree.nodes["Principled BSDF"]
            bsdf.inputs["Specular"].default_value = 0
            bsdf.inputs["Metallic"].default_value = 0
            texImage = mat.node_tree.nodes.new("ShaderNodeTexImage")
            texImage.image = bpy.data.images.new(str(self.name + "_"+vs_weapon_materials[i]+"_Tex"), self.tim.textureWidth, self.tim.textureHeigth)
            texImage.image.pixels = self.tim.textures[i]
            texImage.interpolation = "Closest"  # texture filter
            # we use the first texture for the material by default
            mat.node_tree.links.new(bsdf.inputs["Base Color"], texImage.outputs["Color"])
            # to handle alpha cutout
            mat.node_tree.links.new(bsdf.inputs["Alpha"], texImage.outputs["Alpha"])
            blender_mesh.materials.append(mat)

        # Creating UVs for Blender
        uvlayer = blender_mesh.uv_layers.new()
        face_uvs = self.getUVsForBlender()
        for face in blender_mesh.polygons:
            face.material_index = material_index  # XD cherry on the cake 
            # loop_idx increment for each vertex of each face so if there is 9 triangle -> 9*3 = 27 loop_idx, even if some vertex are common between faces
            for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
                # uvs needs to be scaled from texture W&H
                uvlayer.data[loop_idx].uv = (
                    face_uvs[loop_idx][0] / (self.tim.textureWidth - 1),
                    face_uvs[loop_idx][1] / (self.tim.textureHeigth - 1),
                )

        # Creating Blender object and link into the current collection
        blender_obj = bpy.data.objects.new(str(self.name), object_data=blender_mesh)
        view_layer = bpy.context.view_layer
        view_layer.active_layer_collection.collection.objects.link(blender_obj)
        blender_obj.select_set(True)

        # maybe axis arn't the same in VS and Blender, we should care
        #blender_obj.rotation_euler = (math.radians(self.rotations[1][0]),math.radians(self.rotations[1][1]),math.radians(self.rotations[1][2]))

        # we store datas for export
        blender_mesh.datas.rots0 = (self.rotations[0][0], self.rotations[0][1], self.rotations[0][2])
        blender_mesh.datas.rots1 = (self.rotations[1][0], self.rotations[1][1], self.rotations[1][2])
        blender_mesh.datas.rots2 = (self.rotations[2][0], self.rotations[2][1], self.rotations[2][2])

        view_layer.objects.active = blender_obj
        blender_mesh.validate()
        blender_mesh.update()

        return blender_obj

    def fromBlenderMesh(self, blender_mesh):
        verts = blender_mesh.vertices[:]
        facets = [f for f in blender_mesh.polygons]
        self.header = WEPHeader()
        self.header.numBones = 2  # bone 0, is never used by groups, but maybe it is used by VS
        self.header.numGroups = 1  # we will simplify the WEP output as much as possible
        self.header.numTri = 0  # need to be determinated
        self.header.numQuad = 0  # need to be determinated
        self.header.numFace = 0  # we want this to be 0 if possible

        # WEP BONES SECTION
        self.bones = []
        defaultBone = BoneSection.Bone()
        defaultBone.defaultBones()
        self.bones.append(defaultBone)
        mainBone = BoneSection.Bone()
        mainBone.index = 1
        # for the main bone length, we need to check all vertices x value and take the minimal value
        xmin = 0
        for i in range(0, len(verts)):
            xmin = min(xmin, verts[i].co[0] * VS.VERTEX_RATIO)
        # VSBone length is an int32 so we don't really need to check if xmin is in the range
        # but we must be sure it's an integer
        mainBone.length = int(xmin)
        mainBone.parentIndex = 0
        mainBone.groupId = 0
        mainBone.mountId = 0
        mainBone.bodyPartId = 0
        mainBone.mode = 0
        mainBone.unk = (0, 0, 0, 0, 0, 0, 0)
        self.bones.append(mainBone)
        bone_section_size = len(self.bones) * 16

        # WEP GROUPS SECTION
        # since we try to use one only bone, this section is very simple
        self.groups = []
        mainGroup = GroupSection.Group()
        mainGroup.boneIndex = 1
        mainGroup.numVertices = len(verts)
        self.groups.append(mainGroup)
        group_section_size = len(self.groups) * 4

        # WEP VERTEX SECTION
        self.vertices = []
        for i in range(0, len(verts)):
            blender_vert = verts[i]
            vertex = VertexSection.Vertex()
            vertex.x = int(blender_vert.co[0] * VS.VERTEX_RATIO)
            vertex.y = int(blender_vert.co[1] * VS.VERTEX_RATIO)
            vertex.z = int(blender_vert.co[2] * VS.VERTEX_RATIO)
            vertex.w = 0
            vertex.swapYnZ() # Blender axis arn't the same of VS ones
            self.vertices.append(vertex)
        vertex_section_size = len(self.vertices) * 8

        # WEP TEXTURE SECTION
        # we do texture section before face section to get texture width and height for faces UVs
        self.tim = TIM.WEPTIM()
        mat = blender_mesh.materials[0]
        blender_textures = []
        # default values
        self.tim.textureWidth = 48
        self.tim.textureHeigth = 32
        if mat.node_tree:
            blender_textures.extend([x for x in mat.node_tree.nodes if x.type == "TEX_IMAGE"])
            if len(blender_textures) > 0:
                self.tim.textureWidth = blender_textures[0].image.size[0]
                self.tim.textureHeigth = blender_textures[0].image.size[1]
        self.tim.halfW = int(self.tim.textureWidth / 2)
        self.tim.halfH = int(self.tim.textureHeigth / 2)
        self.tim.unk = 1  # must be a flag that say how to decode the pallets
        self.tim.numColor = 48
        # to rebuild the texture section we need many things...
        # first the color table
        # 1 / 3 of colors are common between pallets
        # 2 / 3 of colors are set for a specific pallet so we need to set this 7 times
        # most weapons use 48 colors, 16 common and 32 for a pallet, its understandable because 256 / 8 = 32
        # i think the VS team didn't want to set more than 256 different colors for a model
        # then we can build textures using pallets colors
        # when importing a WEP we stored pallets in the first 48 pixels, i think the impact is null when the borders are always a transparent margin
        # but maybe we should consider make them transparent again when exporting
        texturesColors16bits = []
        self.tim.handleColors = []
        self.tim.palletColors = []
        self.tim.cluts = []
        for t in range(0, len(blender_textures)):
            self.tim.palletColors.append([])
            btex = blender_textures[t]  # ShaderNodeTexImage btex
            col = []
            assoc = {}
            pix_count = 0
            for pixel in btex.image.pixels:
                # R G B A - R G B A - ....
                # we must iterate 4 times to get one pixel
                col.append(pixel)
                if len(col) == 4:
                    vs_color = color.Color()
                    vs_color.fromFloat(col[0], col[1], col[2], col[3])
                    # print("vs_color : "+repr(vs_color))
                    col = []
                    # this is possible when the first 48 pixels defines the pallet
                    if t == 0 and len(self.tim.palletColors[t]) < 16:
                        self.tim.handleColors.append(vs_color)
                    if len(self.tim.palletColors[t]) < 48:
                        assoc[vs_color.code] = pix_count
                        self.tim.palletColors[t].append(vs_color)

                    # building the clut with the first texture
                    if t == 0:
                        self.tim.cluts.append(assoc[vs_color.code])
                    else:
                        # we must be sure the clut is correct for all pallets, sometimes colors are duplicated in handle and the first pallet and this cause trouble for other pallets
                        if ( self.tim.palletColors[t][self.tim.cluts[pix_count]].code != vs_color.code ):
                            # the texture color does not fit the clut definition
                            # we update it and hope this does not do more troubles...
                            self.tim.cluts[pix_count] = assoc[vs_color.code]
                    pix_count += 1

            self.tim.texMapSize = self.tim.binsize()

        texture_section_size = self.tim.binsize()

        # WEP FACES SECTION
        uvlayer = blender_mesh.uv_layers.active
        self.faces = []
        loop_idx = 0
        side_layer = blender_mesh.polygon_layers_int.get('side')
        flag_layer = blender_mesh.polygon_layers_int.get('flag')
        for i in range(0, len(facets)):
            bface = facets[i]
            vnum = len(bface.vertices)
            face = FaceSection.Face()
            face.verticesCount = vnum
            face.vertices = []
            face.uv = []
            if vnum == 3:  # its a triangle
                self.header.numTri += 1
                face.type = 0x24
                face.size = 16
                face.side = 4
                face.flag = 0
                if side_layer is not None:
                    face.side = side_layer.data[i].value
                    face.flag = flag_layer.data[i].value
            elif vnum == 4:  # its a quad
                self.header.numQuad += 1
                face.type = 0x2C
                face.size = 20
                face.side = 4
                face.alpha = 0
                if side_layer is not None:
                    face.side = side_layer.data[i].value
                    face.flag = flag_layer.data[i].value
            # we need to organize indexes like VS do
            if vnum == 3:
                face.vertices.append(bface.vertices[0])
                face.vertices.append(bface.vertices[1])
                face.vertices.append(bface.vertices[2])
                # uvs needs to be scaled from texture W&H 1,2,0
                face.uv.append(
                    [
                        int(uvlayer.data[loop_idx + 2].uv[0] * self.tim.textureWidth),
                        int(uvlayer.data[loop_idx + 2].uv[1] * self.tim.textureHeigth),
                    ]
                )
                face.uv.append(
                    [
                        int(uvlayer.data[loop_idx].uv[0] * self.tim.textureWidth),
                        int(uvlayer.data[loop_idx].uv[1] * self.tim.textureHeigth),
                    ]
                )
                face.uv.append(
                    [
                        int(uvlayer.data[loop_idx + 1].uv[0] * self.tim.textureWidth),
                        int(uvlayer.data[loop_idx + 1].uv[1] * self.tim.textureHeigth),
                    ]
                )
                loop_idx += 3  # inc for each vertex of each face
            if vnum == 4:
                face.vertices.append(bface.vertices[0])
                face.vertices.append(bface.vertices[1])
                face.vertices.append(bface.vertices[3])
                face.vertices.append(bface.vertices[2])
                face.uv.append(
                    [
                        int(uvlayer.data[loop_idx].uv[0] * self.tim.textureWidth),
                        int(uvlayer.data[loop_idx].uv[1] * self.tim.textureHeigth),
                    ]
                )
                face.uv.append(
                    [
                        int(uvlayer.data[loop_idx + 1].uv[0] * self.tim.textureWidth),
                        int(uvlayer.data[loop_idx + 1].uv[1] * self.tim.textureHeigth),
                    ]
                )
                face.uv.append(
                    [
                        int(uvlayer.data[loop_idx + 3].uv[0] * self.tim.textureWidth),
                        int(uvlayer.data[loop_idx + 3].uv[1] * self.tim.textureHeigth),
                    ]
                )
                face.uv.append(
                    [
                        int(uvlayer.data[loop_idx + 2].uv[0] * self.tim.textureWidth),
                        int(uvlayer.data[loop_idx + 2].uv[1] * self.tim.textureHeigth),
                    ]
                )
                loop_idx += 4
            self.faces.append(face)

        self.rotations[0] = (blender_mesh.datas.rots0[0], blender_mesh.datas.rots0[1], blender_mesh.datas.rots0[2], 7)
        self.rotations[1] = (blender_mesh.datas.rots1[0], blender_mesh.datas.rots1[1], blender_mesh.datas.rots1[2], 7)
        self.rotations[2] = (blender_mesh.datas.rots0[0], blender_mesh.datas.rots2[1], blender_mesh.datas.rots2[2], 7)

        face_section_size = self.header.numTri * 16
        face_section_size += self.header.numQuad * 20

        self.header.dec = 12  # is different in ZUD
        self.header.bonePtr = self.header.dec + 48 + 16
        self.header.groupPtr = self.header.bonePtr + bone_section_size
        self.header.vertexPtr = self.header.groupPtr + group_section_size
        self.header.polygonPtr = self.header.vertexPtr + vertex_section_size
        self.header.texturePtr = self.header.polygonPtr + face_section_size

    def getVerticesForBlender(self):
        bvertices = []
        for vertex in self.vertices:
            bvertices.append(vertex.blenderSwaped())
        return bvertices

    def getFacesForBlender(self):
        bfaces = []
        for face in self.faces:
            if face.type == 0x24:
                bfaces.append(face.vertices)
            elif face.type == 0x2C:
                # little twist for quads
                bfaces.append([face.vertices[0],face.vertices[1],face.vertices[3],face.vertices[2]])
        return bfaces

    def getUVsForBlender(self):
        buvs = []
        for face in self.faces:
            if face.type == 0x24:
                buvs.extend([face.uv[1], face.uv[2], face.uv[0]])
            elif face.type == 0x2C:
                buvs.extend([face.uv[0], face.uv[1], face.uv[3], face.uv[2]])
        return buvs

    def tobin(self):
        bin = bytes()
        bin += self.header.tobin()
        for bone in self.bones:
            bin += bone.tobin()
        for group in self.groups:
            bin += group.tobin()
        for vertex in self.vertices:
            bin += vertex.tobin()
        for face in self.faces:
            bin += face.tobin()
        bin += self.tim.tobin()
        # Default Rotation
        for i in range(0, 3):  # 3 axis
            bin += struct.pack("4h", self.rotations[i][0], self.rotations[i][1], self.rotations[i][2], self.rotations[i][3])
        return bin



class WEPHeader:
    def __init__(self):
        self.numBones = 0
        self.numGroups = 0  # group of vertices weighted to a bone
        self.numVertices = 0
        self.numTri = 0
        self.numQuad = 0
        self.numPoly = 0  # can be quads or tris or vcolored faces in some SHP
        self.numFaces = 0
        self.texturePointer1 = 0
        self.dec = 0  # always the same in WEP files, but not when packed in ZUD
        self.bonePtr = 0
        self.groupPtr = 0
        self.vertexPtr = 0
        self.polygonPtr = 0
        self.texturePtr = 0
    def __repr__(self):
        return " numBones : "+ repr(self.numBones)+ " numGroups : "+ repr(self.numGroups)+ " numTri : "+ repr(self.numTri)+ " numQuad : "+ repr(self.numQuad)+ " numFace : "+ repr(self.numFaces)+ " bonePtr : "+ repr(self.bonePtr)+ " groupPtr : "+ repr(self.groupPtr)+ " vertexPtr : "+ repr(self.vertexPtr)+ " polygonPtr : "+ repr(self.polygonPtr)+ " texturePtr : "+ repr(self.texturePtr)
    def feed(self, file):
        self.numBones, self.numGroups, self.numTri, self.numQuad, self.numPoly, self.texturePointer1 = struct.unpack("2B 3H I", file.read(12))
        self.numFaces = self.numTri + self.numQuad + self.numPoly
        self.dec = file.tell()
        file.seek(48, 1)  # padding
        self.texturePtr, self.groupPtr, self.vertexPtr, self.polygonPtr = struct.unpack("4I", file.read(16))
        self.bonePtr = file.tell()
        self.texturePtr += self.dec
        self.groupPtr += self.dec
        self.vertexPtr += self.dec
        self.polygonPtr += self.dec
    def tobin(self):
        bin = bytes()
        bin += VS.SIG
        bin += struct.pack("2B 3H I",self.numBones,self.numGroups,self.numTri,self.numQuad,self.numPoly,self.texturePointer1)
        bin += bytearray(48)
        bin += struct.pack("4I",self.texturePtr - self.dec, self.groupPtr - self.dec, self.vertexPtr - self.dec, self.polygonPtr - self.dec)
        return bin
