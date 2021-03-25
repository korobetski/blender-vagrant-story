bl_info = {
    "name": "Vagrant Story file formats Add-on",
    "description": "Import-Export Vagrant Story file formats (WEP, SHP, SEQ, ZUD, MPD, ZND).",
    "author": "Sigfrid Korobetski (LunaticChimera)",
    "version": (2, 0),
    "blender": (2, 92, 0),
    "location": "File > Import-Export",
    "category": "Import-Export",
}

#http://datacrystal.romhacking.net/wiki/Vagrant_Story:SHP_files

import os
import math
import struct

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, StringProperty
from bpy_extras.io_utils import ExportHelper, ImportHelper

from . import TIM, VS, BoneSection, FaceSection, GroupSection, VertexSection, SEQ


# CALLED BY BLENDER
class Import(bpy.types.Operator, ImportHelper):
    """Load a SHP file"""

    bl_idname = "import_mesh.shp"
    bl_label = "Import SHP"
    filename_ext = ".SHP"

    filepath: bpy.props.StringProperty(default="", subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.SHP", options={"HIDDEN"})
    bool_anim_trans: bpy.props.BoolProperty(
        name="Anims Translation",
        description="Add translation when importing SEQ animations ?",
        default=False
    )


    def execute(self, context):
        keywords = self.as_keywords(ignore=("filter_glob"))
        BlenderImport(self, context, **keywords)

        return {"FINISHED"}

# CALLED BY BLENDER
class Export(bpy.types.Operator, ExportHelper):
    """Save a SHP file"""

    bl_idname = "export_mesh.shp"
    bl_label = "Export SHP"
    check_extension = True
    filename_ext = ".SHP"

    filter_glob: bpy.props.StringProperty(default="*.SHP", options={"HIDDEN"})
    def execute(self, context):
        keywords = self.as_keywords(ignore=("filter_glob", "check_existing"))
        check = False
        #check = saveWEP(self, context, **keywords)
        return check




def BlenderImport(operator, context, filepath, bool_anim_trans = False):
    print("bool_anim_trans : "+repr(bool_anim_trans))
    shp = SHP()
    # we read datas from a file
    shp.loadFromFile(filepath)
    # we build geometry from datas
    shpObj = shp.buildGeometry()

    # we seek a corresponding SEQ to display the SHP in a better way
    print("filepath : "+filepath)
    print("bpy.path.basename : "+bpy.path.basename(filepath))
    print("bpy.path.display_name : "+bpy.path.display_name(filepath))
    topa = ["_COM.SEQ","_BT1.SEQ","_BT2.SEQ","_BT3.SEQ","_BT4.SEQ","_BT5.SEQ","_BT6.SEQ","_BT7.SEQ","_BT8.SEQ","_BT9.SEQ","_BTA.SEQ"]
    seq = None
    for seqpath in topa:
        seqfilepath = filepath.replace(bpy.path.basename(filepath), bpy.path.display_name(filepath)+seqpath)
        if os.path.isfile(seqfilepath):
            print("Corresponding SEQ found at : "+repr(seqfilepath))

            seq = SEQ.SEQ()
            seq.loadFromFile(seqfilepath)
            # we attach SEQ animations to the builded 3D model
            seq.buildAnimations(shpObj, bool_anim_trans)
            shpObj.parent.animation_data.action = bpy.data.actions[seq.name + "_Animation_0"]
            break # we don't need to load every corresponding SEQ

    # selecting armature
    shpObj.parent.name = bpy.path.display_name(filepath)
    shpObj.parent.select_set(True)
    bpy.context.view_layer.objects.active = shpObj.parent

    # maybe we should considere invert Y and Z axis when building bones and vertices
    #shpObj.parent.rotation_euler = (-math.pi / 2, 0, 0)  # height to Z+
    return {"FINISHED"}

class SHP:
    def __init__(self):
        self.name = ".SHP"
        self.header = SHPHeader()
        self.bones = []
        self.groups = []
        self.vertices = []
        self.faces = []
        self.tim = TIM.WEPTIM()
        self.hasColoredVertex = False
    def __repr__(self):
        return("(--"+repr(self.name)+".SHP-- | "+repr(self.header)+")")
    def loadFromFile(self, filepath):
        # Open a SHP file and parse it
        file = open(filepath, "rb")
        self.name = bpy.path.display_name(filepath)
        self.parse(file)
        file.close()
    def parse(self, file):
        signature = file.read(4)
        if signature != VS.SIG:
            return

        # SHP HEADER
        self.header.feed(file)
        print(self)

        # SHP BONES SECTION
        self.bones = BoneSection.parse(file, self.header.numBones)

        # SHP GROUPS SECTION
        if self.header.groupPtr != file.tell():
            print("WARNING : Pointer group : bad position")
            file.seek(self.header.groupPtr)
        self.groups = GroupSection.parse(file, self.header.numGroups, self.bones)

        # SHP VERTEX SECTION
        # we get numVertices by checking the last group datas
        self.numVertices = 0
        if len(self.groups) > 0:
            self.numVertices = self.groups[len(self.groups)- 1].numVertices
        if self.header.vertexPtr != file.tell():
            print("WARNING : Pointer vertex : bad position")
            file.seek(self.header.vertexPtr)
        self.vertices = VertexSection.parse(file, self.numVertices, self.groups)

        # WEP FACES SECTION
        if self.header.polygonPtr != file.tell():
            print("WARNING : Pointer face : bad position")
            file.seek(self.header.polygonPtr)
        self.faces = FaceSection.parse(file, self.header.numFaces)
        self.hasColoredVertex = FaceSection.hasColoredVertex(self.faces)

        # SHP AKAO SECTION SKIPPED
        # GOTO MAGIC SECTION
        file.seek(self.header.magicPtr)
        num, magicNum = struct.unpack("2I", file.read(8))
        file.seek(magicNum, 1)

        # TEXTURES SECTION
        self.tim = TIM.SHPTIM()
        self.tim.doubleClut = self.hasColoredVertex
        self.tim.feed(file)
        print(self.tim)

    def buildGeometry(self):
        print("SHP Building...")

        view_layer = bpy.context.view_layer
        # Creating Bones for Blender
        armature = bpy.data.armatures.new("Armature")
        arm_obj = bpy.data.objects.new("Armature", armature)
        view_layer.active_layer_collection.collection.objects.link(arm_obj)
        armature_data = arm_obj
        # Must make armature active and in edit mode to create a bone
        view_layer.objects.active = armature_data
        bpy.ops.object.mode_set(mode="EDIT", toggle=False)
        edit_bones = armature_data.data.edit_bones
        for vs_bone in self.bones:
            blender_bone = edit_bones.new(vs_bone.name)
            blender_bone.use_relative_parent = False
            blender_bone.use_inherit_rotation = True
            blender_bone.use_local_location = True
            # we store additionnal datas
            blender_bone.datas.mountId = vs_bone.mountId
            blender_bone.datas.bodyPartId = vs_bone.bodyPartId
            blender_bone.datas.mode = vs_bone.mode
            blender_bone.datas.unk = vs_bone.unk
            # matrix = mathutils.Matrix.Identity(4)
            if vs_bone.parent is None:
                blender_bone.head = (0, 0, 0)
                # blender_bone.length = 0.5 # by default bones go up in Z+
                # Blender delete bones when length = 0
                blender_bone.tail = (0, 0.0001, 0)
            else:
                blender_bone.parent = edit_bones[vs_bone.parent.name]
                # matrix[0][3] = blender_bone.parent.head[0] + vs_bone.parent.length / 100
                # print("Bone "+repr(vs_bone)+" -> id : "+repr(blender_bone.matrix))
                if vs_bone.parentIndex != 0:
                    # blender_bone.head = blender_bone.parent.tail
                    blender_bone.head = (blender_bone.parent.head[0] - vs_bone.parent.length / VS.VERTEX_RATIO, 0, 0)
                else:
                    blender_bone.head = (0, 0, 0)
                # bones direction should be X+
                # but VS animations seems good when bones go forward in Y+
                # this is because Blender change the bone matrix when the bone.tail is defined
                # so if we want render bones in the good axis we need to "rotate" by Z-90° all animations keyframe in bone "normal / local mode"
                # blender_bone.tail = (blender_bone.head[0] + vs_bone.length / 100, 0, 0)
                blender_bone.tail = (blender_bone.head[0], 0, vs_bone.length / VS.VERTEX_RATIO / 10)

        # exit edit mode to save bones so they can be used in pose mode
        bpy.ops.object.mode_set(mode="OBJECT")

        # Creating Geometry and Mesh for Blender
        mesh_name = self.name
        blender_mesh = bpy.data.meshes.new(name=mesh_name + "_MESH")
        blender_mesh.from_pydata(self.getVerticesForBlender(), [], self.getFacesForBlender())
        blender_obj = bpy.data.objects.new(mesh_name, object_data=blender_mesh)

        for i in range(0, len(self.tim.textures)):
            mat = bpy.data.materials.new(name=str(self.name + "_Mat"+str(i)))
            mat.use_nodes = True
            mat.blend_method = "CLIP"  # to handle alpha cutout
            # maybe i should consider using a simpler material... VS doesn't need a PBR Material :D
            bsdf = mat.node_tree.nodes["Principled BSDF"]
            bsdf.inputs["Specular"].default_value = 0
            bsdf.inputs["Metallic"].default_value = 0
            texImage = mat.node_tree.nodes.new("ShaderNodeTexImage")
            texImage.image = bpy.data.images.new(str(self.name + "_Tex"+str(i)), self.tim.textureWidth, self.tim.textureHeigth)
            texImage.image.pixels = self.tim.textures[i]
            texImage.interpolation = "Closest"  # texture filter
            # we use the first texture for the material by default
            if self.hasColoredVertex == True:
                # We must melt vertex color and texture
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
            else:
                mat.node_tree.links.new(bsdf.inputs["Base Color"], texImage.outputs["Color"])
                # to handle alpha cutout
                mat.node_tree.links.new(bsdf.inputs["Alpha"], texImage.outputs["Alpha"])
            blender_mesh.materials.append(mat)

        # Creating vertices groups
        # https://docs.blender.org/api/current/bpy.types.VertexGroup.html
        lastv = 0
        for vs_group in self.groups:
            blender_group = blender_obj.vertex_groups.new(name=vs_group.bone.name)
            indexes = []
            for i in range(lastv, vs_group.numVertices):
                indexes.append(i)
            lastv = vs_group.numVertices
            # type (enum in ['REPLACE', 'ADD', 'SUBTRACT'])
            blender_group.add(indexes, 1, "REPLACE")
            blender_group.lock_weight = True

        view_layer.active_layer_collection.collection.objects.link(blender_obj)
        blender_obj.select_set(True)
        view_layer.objects.active = blender_obj

        blender_obj.parent = arm_obj
        modifier = blender_obj.modifiers.new(type="ARMATURE", name="Armature")
        modifier.object = arm_obj

        # Creating UVs and Vertex colors for Blender
        uvlayer = blender_mesh.uv_layers.new()
        vcol_layer = blender_mesh.vertex_colors.new()
        colors = self.getVColForBlender()
        face_uvs = self.getUVsForBlender()
        for face in blender_mesh.polygons:
            for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
                # uvs needs to be scaled from texture W&H
                uvlayer.data[loop_idx].uv = (
                    face_uvs[loop_idx][0] / (self.tim.textureWidth - 1),
                    face_uvs[loop_idx][1] / (self.tim.textureHeigth - 1),
                )
                vcol_layer.data[loop_idx].color = colors[loop_idx].toFloat()

        blender_mesh.validate()
        blender_mesh.update()

        # compute normals outside
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode="OBJECT")
        # face smooth
        bpy.ops.object.shade_smooth()

        return blender_obj

    def getVerticesForBlender(self):
        bvertices = []
        for vertex in self.vertices:
            bvertices.append(vertex.blenderSwaped())
        return bvertices

    def getFacesForBlender(self):
        bfaces = []
        for face in self.faces:
            if face.type == 0x24 or face.type == 0x34:
                bfaces.append(face.vertices)
            elif face.type == 0x2C or face.type == 0x3C:
                # little twist for quads
                bfaces.append([face.vertices[0],face.vertices[1],face.vertices[3],face.vertices[2]])
        return bfaces

    def getUVsForBlender(self):
        buvs = []
        for face in self.faces:
            if face.type == 0x24 or face.type == 0x34:
                buvs.extend([face.uv[1], face.uv[2], face.uv[0]])
            elif face.type == 0x2C or face.type == 0x3C:
                buvs.extend([face.uv[0], face.uv[1], face.uv[3], face.uv[2]])
        return buvs

    def getVColForBlender(self):
        vcols = []
        for face in self.faces:
            if face.type == 0x24 or face.type == 0x34:
                vcols.extend([face.colors[0], face.colors[1], face.colors[2]])
            elif face.type == 0x2C or face.type == 0x3C:
                vcols.extend([face.colors[0], face.colors[1],face.colors[3], face.colors[2]])
        return vcols

    def getWeaponBoneName(self):
        for bone in self.bones:
            if bone.mountId == -16:
                return bone.name
        return None

    def getShieldBoneName(self):
        for bone in self.bones:
            if bone.mountId == -15:
                return bone.name
        return None


class SHPHeader:
    def __init__(self):
        self.numBones = 0
        self.numGroups = 0  # group of vertices weighted to a bone
        self.numVertices = 0
        self.numTri = 0
        self.numQuad = 0
        self.numPoly = 0  # can be quads or tris or vcolored faces in some SHP
        self.numFaces = 0
        self.overlays = []
        self.dec = 0  # always the same in SHP files, but not when packed in ZUD
        self.bonePtr = 0
        self.groupPtr = 0
        self.vertexPtr = 0
        self.polygonPtr = 0
        self.texturePtr = 0
        self.magicPtr = 0
        self.AKAOPtr = 0
        self.unk1 = []
        self.unk2 = []
        self.unk3 = []
        self.collider = []
        self.menuYpos = 0
        self.shadowRadius = 0
        self.shadowInc = 0
        self.shadowDec = 0
        self.h1 = 0
        self.h2 = 0
        self.menuScale = 0
        self.h3 = 0
        self.tSphereYpos = 0
        self.h4 = 0
        self.h5 = 0
        self.h6 = 0
        self.h7 = 0

    def __repr__(self):
        return " numBones : "+ repr(self.numBones)+ " numGroups : "+ repr(self.numGroups)+ " numTri : "+ repr(self.numTri)+ " numQuad : "+ repr(self.numQuad)+ " numFace : "+ repr(self.numFaces)+ " bonePtr : "+ repr(self.bonePtr)+ " groupPtr : "+ repr(self.groupPtr)+ " vertexPtr : "+ repr(self.vertexPtr)+ " polygonPtr : "+ repr(self.polygonPtr)+ " texturePtr : "+ repr(self.texturePtr)


    def feed(self, file):
        self.numBones,self.numGroups,self.numTri,self.numQuad,self.numPoly = struct.unpack("2B 3H", file.read(8))
        self.numFaces = self.numTri + self.numQuad + self.numPoly
        self.dec = file.tell()
        self.overlays = []
        for i in range(0, 8):
            self.overlays.append(struct.unpack("4b", file.read(4)))
        self.unk1 = struct.unpack("36b", file.read(36))
        self.collider = struct.unpack("6b", file.read(6))
        self.menuYpos = struct.unpack("h", file.read(2))[0]
        self.unk2 = struct.unpack("12b", file.read(12))
        (
            self.shadowRadius,
            self.shadowInc,
            self.shadowDec,
            self.h1,
            self.h2,
            self.menuScale,
            self.h3,
            self.tSphereYpos,
            self.h4,
            self.h5,
            self.h6,
            self.h7,
        ) = struct.unpack("12h", file.read(24))
        bSeqLBA = []
        for i in range(0, 0x0C):
            # LBA XX_BTX.SEQ  (battle animations first one is actually XX_COM.SEQ)
            bSeqLBA.append(struct.unpack("I", file.read(4))[0])
        chains = []
        for i in range(0, 0x0C):
            chains.append(struct.unpack("H", file.read(2))[0])  # chain attack animation ID
        specialAttacksLBA = []
        for i in range(0, 12):
            # LBA XXSP0X.SEQ (special attack animations)	 + unknown (probably more LBA tables, there are also special attack ids stored here.)
            specialAttacksLBA.append(struct.unpack("I", file.read(4))[0])

        # pointer to magic effects section (relative to offset $F8)
        self.magicPtr = struct.unpack("I", file.read(4))[0]
        self.dec = file.tell()
        self.unk3 = struct.unpack("24H", file.read(48))
        self.AKAOPtr, self.groupPtr, self.vertexPtr, self.polygonPtr = struct.unpack("4I", file.read(16))
        self.bonePtr = file.tell()
        self.magicPtr += self.dec
        self.AKAOPtr += self.dec
        self.groupPtr += self.dec
        self.vertexPtr += self.dec
        self.polygonPtr += self.dec

    def tobin(self):
        bin = bytes()
        bin += VS.SIG
        bin += struct.pack("2B 3H",self.numBones,self.numGroups,self.numTri,self.numQuad,self.numPoly)
        # TODO
        return bin