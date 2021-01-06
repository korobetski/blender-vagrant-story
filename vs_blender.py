import bpy
import bmesh
import struct
import os
import math
import mathutils

from bpy_extras.io_utils import (ImportHelper,
                                 ExportHelper)

from bpy.props import (BoolProperty,
                       FloatProperty,
                       StringProperty,
                       EnumProperty,
                       )

bl_info = {
    "name": "Vagrant Story file formats Add-on",
    "description": "Import-Export Vagrant Story file formats (WEP, SHP, SEQ, ZUD).",
    "author": "Sigfrid Korobetski (LunaticChimera)",
    "version": (1, 3),
    "blender": (2, 91, 0),
    "location": "File > Import-Export",
    "category": "Import-Export",
}


class ImportWEP(bpy.types.Operator, ImportHelper):
    """Load a WEP file"""
    bl_idname = "import_mesh.wep"
    bl_label = "Import WEP"
    filename_ext = ".WEP"

    filepath: bpy.props.StringProperty(default="", subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.WEP", options={'HIDDEN'})

    def execute(self, context):
        keywords = self.as_keywords(ignore=('axis_forward',
                                            'axis_up',
                                            'filter_glob',
                                            ))
        loadWEP(self, context, **keywords)

        return {'FINISHED'}


class ImportSHP(bpy.types.Operator, ImportHelper):
    """Load a SHP file"""
    bl_idname = "import_mesh.shp"
    bl_label = "Import SHP"
    filename_ext = ".SHP"

    filepath: bpy.props.StringProperty(default="", subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.SHP", options={'HIDDEN'})

    def execute(self, context):
        keywords = self.as_keywords(ignore=('axis_forward',
                                            'axis_up',
                                            'filter_glob',
                                            ))
        loadSHP(self, context, **keywords)

        return {'FINISHED'}


class ImportZUD(bpy.types.Operator, ImportHelper):
    """Load a ZUD file"""
    bl_idname = "import_mesh.zud"
    bl_label = "Import ZUD"
    filename_ext = ".ZUD"

    filepath: bpy.props.StringProperty(default="", subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.ZUD", options={'HIDDEN'})

    def execute(self, context):
        keywords = self.as_keywords(ignore=('axis_forward',
                                            'axis_up',
                                            'filter_glob',
                                            ))
        loadZUD(self, context, **keywords)

        return {'FINISHED'}


class ImportSEQ(bpy.types.Operator, ImportHelper):
    """Load a SEQ file"""
    bl_idname = "import_mesh.seq"
    bl_label = "Import SEQ"
    filename_ext = ".SEQ"

    filepath: bpy.props.StringProperty(default="", subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.SEQ", options={'HIDDEN'})

    def execute(self, context):
        keywords = self.as_keywords(ignore=('axis_forward',
                                            'axis_up',
                                            'filter_glob',
                                            ))
        loadSEQ(self, context, **keywords)

        return {'FINISHED'}


class ExportWEP(bpy.types.Operator, ExportHelper):
    """Save a WEP file"""
    bl_idname = "export_mesh.wep"
    bl_label = "Export WEP"
    check_extension = True
    filename_ext = ".WEP"

    filter_glob: bpy.props.StringProperty(default="*.WEP", options={'HIDDEN'})

    def execute(self, context):
        keywords = self.as_keywords(ignore=('axis_forward',
                                            'axis_up',
                                            'filter_glob',
                                            'check_existing',
                                            ))
        return saveWEP(self, context, **keywords)


def menu_func_import(self, context):
    self.layout.operator(ImportWEP.bl_idname, text="Vagrant Story Weapon (.WEP)")
    #self.layout.operator(ImportSHP.bl_idname, text="Vagrant Story Character Shape (.SHP)")
    #self.layout.operator(ImportSEQ.bl_idname, text="Vagrant Story Animations Sequence (.SEQ)")
    self.layout.operator(ImportZUD.bl_idname, text="Vagrant Story Zone Unit Datas (.ZUD)")


def menu_func_export(self, context):
    self.layout.operator(ExportWEP.bl_idname, text="Vagrant Story Weapon (.WEP)")


classes = (
    ImportWEP,
    ImportSHP,
    ImportZUD,
    ImportSEQ,
    ExportWEP,
)

VS_HEADER = b"H01\x00"
ACTIONS = {
  0x01: ['loop', 0], # verified
  0x02: ['0x02', 0], # often at end, used for attack animations
  0x04: ['0x04', 1], #
  0x0a: ['0x0a', 1], # verified in 00_COM (no other options, 0x00 x00 follows)
  0x0b: ['0x0b', 0], # pretty sure, used with walk/run, followed by 0x17/left, 0x18/right
  0x0c: ['0x0c', 1],
  0x0d: ['0x0d', 0],
  0x0f: ['0x0f', 1], # first
  0x13: ['unlockBone', 1], # verified in emulation
  0x14: ['0x14', 1], # often at end of non-looping
  0x15: ['0x15', 1], # verified 00_COM (no other options, 0x00 0x00 follows)
  0x16: ['0x16', 2], # first, verified 00_BT3
  0x17: ['0x17', 0], # + often at end
  0x18: ['0x18', 0], # + often at end
  0x19: ['0x19', 0], # first, verified 00_COM (no other options, 0x00 0x00 follows)
  0x1a: ['0x1a', 1], # first, verified 00_BT1 (0x00 0x00 follows)
  0x1b: ['0x1b', 1], # first, verified 00_BT1 (0x00 0x00 follows)
  0x1c: ['0x1c', 1],
  0x1d: ['paralyze?', 0], # first, verified 1C_BT1
  0x24: ['0x24', 2], # first
  0x27: ['0x27', 4], # first, verified see 00_COM
  0x34: ['0x34', 3], # first
  0x35: ['0x35', 5], # first
  0x36: ['0x36', 3],
  0x37: ['0x37', 1], # pretty sure
  0x38: ['0x38', 1],
  0x39: ['0x39', 1],
  0x3a: ['disappear', 0], # used in death animations
  0x3b: ['land', 0],
  0x3c: ['adjustShadow', 1], # verified
  0x3f: ['0x3f', 0], # first, pretty sure, often followed by 0x16
  0x40: ['0x40', 0], # often preceded by 0x1a, 0x1b, often at end
}

def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


def loadWEP(operator, context, filepath):
    # Parse mesh from WEP file
    file = open(filepath, "rb")
    filename = bpy.path.display_name_from_filepath(filepath)
    wep = parseWEP(file, filename)

    # EOF
    file.close()

    buildWEPGeometry(wep, filename)

    return {'FINISHED'}


def parseWEP(file, filename):
    signature = file.read(4)
    if signature != VS_HEADER:
        return {'CANCELLED'}

    # WEP HEADER
    wep = VSWEPHeader()
    wep.feed(file)
    print(wep)
    # WEP BONES SECTION
    parseBoneSection(file, wep)

    # WEP GROUPS SECTION
    if wep.groupPtr != file.tell():
        print("Pointer group : bad position")
        file.seek(wep.groupPtr)

    parseGroupSection(file, wep)

    # WEP VERTEX SECTION
    if wep.vertexPtr != file.tell():
        print("Pointer vertex : bad position")
        file.seek(wep.vertexPtr)

    parseVertexSection(file, wep)

    # hard fixes for staves 39.WEP to 3F.WEP
    staves = ["39", "3A", "3B", "3C", "3D", "3E", "3F"]
    if staves.__contains__(filename):
        # its a staff, so we need to correct vertices of the first group
        for i in range(wep.groups[0].numVertices):
            wep.vertices[i].x = wep.groups[0].bone.length * 2 - wep.vertices[i].x  # its work but why ?
            wep.vertices[i].y = -wep.vertices[i].y  # simple invert

    # WEP FACES SECTION
    if wep.polygonPtr != file.tell():
        print("Pointer polygon : bad position")
        file.seek(wep.polygonPtr)

    parseFaceSection(file, wep)

    # WEP TEXTURE SECTION
    if wep.texturePtr != file.tell():
        print("Pointer Texture : bad position")
        file.seek(wep.texturePtr)

    parseTextureSection(file, wep)

    # Rotations
    # the first row is always 0000000000000700 for all 127 .WEP files change values doesn't have a visual effect in game
    # the second row seems to control rotations, the last value 0x0700 doesn't have a visual effect in game (the last value is always 0x0700 every WEP every row)
    for i in range(0, 3):  # 3 axis ? 3 bones ?
        # tested in game on Z048U26.ZUD
        # default u2 is FF0F it can be ? 4095 i don't think its 65295
        # with u2 = FFC3 the weapon seems to rotate 90° (or maybe a multiple)
        # with u2 = 0077 the weapon seems to rotate 180°(or maybe a multiple)
        u1, u2, u3, u4 = struct.unpack("<4h", file.read(8))
        u1 = u1 / 22.75
        u2 = u2 / 22.75
        u3 = u3 / 22.75
        print("u1 : "+repr(u1)+"  u2 : "+repr(u2) +  "  u3 : "+repr(u3)+"  u4 : "+repr(u4))
        wep.rotations.append([u1, u2, u3, u4])
    return wep


def saveWEP(operator, context, filepath):
    scene = context.scene
    obj = bpy.context.view_layer.objects.active
    mesh = obj.to_mesh()

    wep = VSWEPHeader()
    wep.fromBlenderMesh(mesh)

    # Write geometry to file
    filepath = os.fsencode(filepath)
    fp = open(filepath, 'w+b')
    bytes_array = bytearray(wep.tobin())
    fp.write(bytes_array)
    fp.close()

    return {'FINISHED'}


def loadSHP(operator, context, filepath):
    file = open(filepath, "rb")
    file_size = os.stat(filepath).st_size

    shp = parseSHP(file)

    # EOF
    file.close()

    char = buildSHPGeometry(shp, bpy.path.display_name_from_filepath(filepath))

    return {'FINISHED'}


def parseSHP(file):
    signature = file.read(4)
    if signature != VS_HEADER:
        return {'CANCELLED'}
    # SHP HEADER
    shp = VSSHPHeader()
    shp.feed(file)
    print(shp)

    # SHP BONES SECTION
    parseBoneSection(file, shp)

    # SHP GROUPS SECTION
    if shp.groupPtr != file.tell():
        print("Pointer group : bad position -> shp.groupPtr :" +
              repr(shp.groupPtr)+"  file.tell : "+repr(file.tell()))
        file.seek(shp.groupPtr)

    parseGroupSection(file, shp)

    # SHP VERTEX SECTION
    if shp.vertexPtr != file.tell():
        print("Pointer vertex : bad position")
        file.seek(shp.vertexPtr)

    parseVertexSection(file, shp)

    # SHP FACES SECTION
    if shp.polygonPtr != file.tell():
        print("Pointer polygon : bad position")
        file.seek(shp.polygonPtr)

    parseFaceSection(file, shp)

    # SHP AKAO SECTION SKIPPED
    # GOTO MAGIC SECTION
    file.seek(shp.magicPtr)
    num, magicNum = struct.unpack("2I", file.read(8))
    file.seek(magicNum, 1)

    # TEXTURES SECTION
    shp.tim = VSSHPTIM()
    shp.tim.doubleClut = shp.isVertexColored
    shp.tim.feed(file)
    print(shp.tim)

    # Default Rotation ???

    return shp


def loadZUD(operator, context, filepath):
    file = open(filepath, "rb")
    zud_id = bpy.path.display_name_from_filepath(filepath)
    zud = VSZUDHeader()
    zud.feed(file)
    print(zud)


    # SHP SECTION
    file.seek(zud.ptrSHP)
    shp = parseSHP(file)

    # WEAPON SECTION
    if zud.idWEP != 0:
        file.seek(zud.ptrWEP)
        wep = parseWEP(file, "{:02X}".format(zud.idWEP))

    # SHIELD SECTION
    if zud.idWEP2 != 0:
        file.seek(zud.ptrWEP2)
        wep2 = parseWEP(file, "{:02X}".format(zud.idWEP2))

    # COMMON SEQ SECTION
    if zud.lenCSEQ > 0:
        file.seek(zud.ptrCSEQ)
        cseq = parseSEQ(file, zud_id+"_Com")

    # BATTLE SEQ SECTION
    if zud.lenBSEQ > 0:
        file.seek(zud.ptrBSEQ)
        bseq = parseSEQ(file, zud_id+"_Bat")

    # EOF
    file.close()

    # Creating Geometry and Meshes for Blender
    char = buildSHPGeometry(shp, "{:02X}".format(zud.idSHP)+"_ZSHP")
    if zud.idWEP != 0:
        wep_obj = buildWEPGeometry(wep, "{:02X}".format(zud.idWEP)+"_ZWEP")
        chiof = wep_obj.constraints.new(type='CHILD_OF')
        chiof.target = char.parent # Armature
        chiof.subtarget = shp.getWeaponBoneName()
        bpy.ops.constraint.childof_clear_inverse(constraint=chiof.name, owner='OBJECT')
        if zud.idWEPType == 6:
            # if its a staff
            wep_obj.location = (2.8, 0, 0) # arbitrary value but seems not bad

    if zud.idWEP2 != 0:
        wep_obj = buildWEPGeometry(wep2, "{:02X}".format(zud.idWEP2)+"_ZEP2")
        chiof = wep_obj.constraints.new(type='CHILD_OF')
        chiof.target = char.parent # Armature
        chiof.subtarget = shp.getShieldBoneName()
        bpy.ops.constraint.childof_clear_inverse(constraint=chiof.name, owner='OBJECT')
    
    if zud.lenCSEQ > 0:
        buildAnimations(char, cseq)
    if zud.lenBSEQ > 0:
        buildAnimations(char, bseq)
    
    # selecting armature
    char.parent.name = zud_id
    char.parent.select_set(True)
    bpy.context.view_layer.objects.active = char.parent

    # maybe we should considere invert Y and Z axis when building bones and vertices
    char.parent.rotation_euler = (-math.pi/2, 0, 0) # height to Z+
    if zud.lenCSEQ > 0:
        char.parent.animation_data.action = bpy.data.actions[cseq.name+"_Animation_0"]
    if zud.lenBSEQ > 0:
        char.parent.animation_data.action = bpy.data.actions[bseq.name+"_Animation_0"]

    return {'FINISHED'}


def loadSEQ(operator, context, filepath):
    file = open(filepath, "rb")
    seq = parseSEQ(file)
    # EOF
    file.close()


def parseSEQ(file, name = "SEQ"):
    seq = VSSEQHeader()
    seq.name = name
    seq.feed(file)
    
    seq.animations = []
    for i in range(0, seq.numAnimations):
        a = VSAnim()
        a.feed(file, i, seq.numBones)
        seq.animations.append(a)

    slots = []
    for i in range(0, seq.numSlots):
        slots.append(struct.unpack("b", file.read(1))[0])

    for i in range(0, seq.numAnimations):
        seq.animations[i].getData(file, seq)
    
    return seq


def parseBoneSection(file, mesh):
    mesh.bones = []
    for i in range(0, mesh.numBones):
        bone = VSBone()
        bone.feed(file, i)
        # in theory parent bone are defined before
        if bone.parentIndex < mesh.numBones:
            bone.parent = mesh.bones[bone.parentIndex]
        print(bone)
        mesh.bones.append(bone)


def parseGroupSection(file, mesh):
    mesh.groups = []
    for i in range(0, mesh.numGroups):
        group = VSGroup()
        group.feed(file, i)
        group.bone = mesh.bones[group.boneIndex]
        group.bone.group = group # double reference
        #print(group)
        mesh.groups.append(group)


def parseVertexSection(file, mesh):
    mesh.vertices = []
    mesh.numVertices = mesh.getLastGroupVNum()
    g = 0
    for i in range(0, mesh.numVertices):
        if i >= mesh.groups[g].numVertices:
            g = g+1

        vertex = VSVertex()
        vertex.group = mesh.groups[g]
        vertex.bone = vertex.group.bone
        vertex.feed(file, i)
        #vertex.reverse()
        #print(vertex)
        vertex.x += vertex.bone.decalage()
        mesh.vertices.append(vertex)


def parseFaceSection(file, mesh):
    face_uvs = []
    for i in range(0, mesh.totalPoly):
        face = VSFace()
        face.default()
        face.feed(file, i, mesh.isVertexColored)
        if face.isColored == True:
            mesh.isVertexColored = True
        #print(face)
        mesh.faces.append(face)


def parseTextureSection(file, mesh):
    mesh.tim = VSWEPTIM()
    mesh.tim.feed(file)
    #print(mesh.tim)


def buildWEPGeometry(wep, name):
    # Creating Material & Textures for Blender
    # https://docs.blender.org/api/current/bpy.types.Material.html
    mat = bpy.data.materials.new(
        name=str(name+'_Material'))
    mat.use_nodes = True
    mat.blend_method = "CLIP"  # to handle alpha cutout
    # maybe i should consider using a simpler material... VS doesn't need a PBR Material :D
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs['Specular'].default_value = 0
    bsdf.inputs['Metallic'].default_value = 0
    for i in range(0, len(wep.tim.textures)):
        texImage = mat.node_tree.nodes.new('ShaderNodeTexImage')
        texImage.image = bpy.data.images.new(str(name+'_Tex'+str(i)), wep.tim.textureWidth, wep.tim.textureHeigth)
        texImage.image.pixels = wep.tim.textures[i]
        texImage.interpolation = "Closest"  # texture filter
        # we use the first texture for the material by default
        if i == 0:
            mat.node_tree.links.new(
                bsdf.inputs['Base Color'], texImage.outputs['Color'])
            # to handle alpha cutout
            mat.node_tree.links.new(
                bsdf.inputs['Alpha'], texImage.outputs['Alpha'])

    # Creating Geometry and Mesh for Blender
    mesh_name = name
    blender_mesh = bpy.data.meshes.new(name=mesh_name+"_MESH")
    blender_mesh.from_pydata(wep.getVerticesForBlender(),
                             [], wep.getFacesForBlender())
    # TODO : we need to handle double sided faces
    blender_mesh.materials.append(mat)

    # Creating UVs for Blender
    uvlayer = blender_mesh.uv_layers.new()
    face_uvs = wep.getUVsForBlender()
    for face in blender_mesh.polygons:
        # loop_idx increment for each vertex of each face so if there is 9 triangle -> 9*3 = 27 loop_idx, even if some vertex are common between faces
        for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
            # uvs needs to be scaled from texture W&H
            uvlayer.data[loop_idx].uv = (
                face_uvs[loop_idx][0]/(wep.tim.textureWidth-1), face_uvs[loop_idx][1]/(wep.tim.textureHeigth-1))

    # Creating Blender object and link into the current collection
    blender_obj = bpy.data.objects.new(
        str(name), object_data=blender_mesh)
    view_layer = bpy.context.view_layer
    view_layer.active_layer_collection.collection.objects.link(blender_obj)
    blender_obj.select_set(True)

    # maybe axis arn't the same in VS and Blender, we should care
    blender_obj.rotation_euler = (math.radians(wep.rotations[1][0]), math.radians( wep.rotations[1][1]), math.radians(wep.rotations[1][2]))

    view_layer.objects.active = blender_obj
    blender_mesh.validate()
    blender_mesh.update()

    return blender_obj


def buildSHPGeometry(shp, name):
    mat = bpy.data.materials.new(name=str(name+'_Material'))
    mat.use_nodes = True
    mat.blend_method = "CLIP"  # to handle alpha cutout
    # maybe i should consider using a simpler material... VS doesn't need a PBR Material :D
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs['Specular'].default_value = 0
    bsdf.inputs['Metallic'].default_value = 0
    for i in range(0, len(shp.tim.textures)):
        texImage = mat.node_tree.nodes.new('ShaderNodeTexImage')
        texImage.image = bpy.data.images.new(str(name+'_Tex'+str(i)), shp.tim.textureWidth, shp.tim.textureHeigth)
        texImage.image.pixels = shp.tim.textures[i]
        texImage.interpolation = "Closest"  # texture filter
        # we use the first texture for the material by default
        if i == 0:
            if shp.isVertexColored == True:
                vc = mat.node_tree.nodes.new('ShaderNodeVertexColor')
                # https://docs.blender.org/manual/fr/2.91/render/shader_nodes/color/mix.html
                mix = mat.node_tree.nodes.new('ShaderNodeMixRGB')
                mix.blend_type = "MULTIPLY" # ('MIX', 'DARKEN', 'MULTIPLY', 'BURN', 'LIGHTEN', 'SCREEN', 'DODGE', 'ADD', 'OVERLAY', 'SOFT_LIGHT', 'LINEAR_LIGHT', 'DIFFERENCE', 'SUBTRACT', 'DIVIDE', 'HUE', 'SATURATION', 'COLOR', 'VALUE')
                mix.inputs[0].default_value = 1
                mat.node_tree.links.new( mix.inputs[1], vc.outputs["Color"])
                mat.node_tree.links.new( mix.inputs[2], texImage.outputs["Color"])
                mat.node_tree.links.new( bsdf.inputs['Base Color'], mix.outputs['Color'])
                # to handle alpha cutout
                mat.node_tree.links.new(bsdf.inputs['Alpha'], texImage.outputs['Alpha'])
            else:
                mat.node_tree.links.new( bsdf.inputs['Base Color'], texImage.outputs['Color'])
                # to handle alpha cutout
                mat.node_tree.links.new( bsdf.inputs['Alpha'], texImage.outputs['Alpha'])

    view_layer = bpy.context.view_layer
    # Creating Bones for Blender
    armature = bpy.data.armatures.new('Armature')
    arm_obj = bpy.data.objects.new('Armature', armature)
    view_layer.active_layer_collection.collection.objects.link(arm_obj)
    armature_data = arm_obj
    # Must make armature active and in edit mode to create a bone
    view_layer.objects.active = armature_data
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)
    edit_bones = armature_data.data.edit_bones
    for vs_bone in shp.bones:
        blender_bone = edit_bones.new(vs_bone.name)
        blender_bone.use_relative_parent = False
        blender_bone.use_inherit_rotation = True
        blender_bone.use_local_location = True
        #matrix = mathutils.Matrix.Identity(4)
        if vs_bone.parent is None:
            blender_bone.head = (0, 0, 0)
            #blender_bone.length = 0.5 # by default bones go up in Z+
            blender_bone.tail = (0, 0.00001, 0) # Blender delete bones when length = 0
        else:
            blender_bone.parent = edit_bones[vs_bone.parent.name]
            #matrix[0][3] = blender_bone.parent.head[0] + vs_bone.parent.length / 100
            #print("Bone "+repr(vs_bone)+" -> id : "+repr(blender_bone.matrix))
            if vs_bone.parentIndex != 0:
                #blender_bone.head = blender_bone.parent.tail
                blender_bone.head = (blender_bone.parent.head[0] + vs_bone.parent.length / 100, 0, 0)
            else:
                blender_bone.head = (0, 0, 0)
            # bones direction should be X+
            # but VS animations seems good when bones go forward in Y+
            # this is because Blender change the bone matrix when the bone.tail is defined
            # so if we want render bones in the good axis we need to "rotate" by Z-90° all animations keyframe in bone "normal / local mode"
            #blender_bone.tail = (blender_bone.head[0] + vs_bone.length / 100, 0, 0)
            blender_bone.tail = (blender_bone.head[0], vs_bone.length / 1000, 0)
            


    # exit edit mode to save bones so they can be used in pose mode
    bpy.ops.object.mode_set(mode='OBJECT')
    # Creating Geometry and Mesh for Blender
    mesh_name = name
    blender_mesh = bpy.data.meshes.new(name=mesh_name+"_MESH")
    blender_mesh.from_pydata(shp.getVerticesForBlender(), [], shp.getFacesForBlender())
    blender_obj = bpy.data.objects.new(mesh_name, object_data=blender_mesh)
    

    blender_mesh.materials.append(mat)
    # Creating vertices groups
    # https://docs.blender.org/api/current/bpy.types.VertexGroup.html
    lastv = 0
    for vs_group in shp.groups:
        blender_group = blender_obj.vertex_groups.new(name=vs_group.bone.name)
        indexes = []
        for i in range(lastv, vs_group.numVertices):
            indexes.append(i)
        lastv = vs_group.numVertices
        blender_group.add(indexes, 1, "REPLACE") # type (enum in ['REPLACE', 'ADD', 'SUBTRACT'])
        blender_group.lock_weight = True

    view_layer.active_layer_collection.collection.objects.link(blender_obj)
    blender_obj.select_set(True)
    view_layer.objects.active = blender_obj

    blender_obj.parent = arm_obj
    modifier = blender_obj.modifiers.new(type='ARMATURE', name="Armature")
    modifier.object = arm_obj

    # Creating UVs and Vertex colors for Blender
    uvlayer = blender_mesh.uv_layers.new()
    vcol_layer = blender_mesh.vertex_colors.new()
    colors = shp.getVColForBlender()
    face_uvs = shp.getUVsForBlender()
    for face in blender_mesh.polygons:
        for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
            # uvs needs to be scaled from texture W&H
            uvlayer.data[loop_idx].uv = ( face_uvs[loop_idx][0]/(shp.tim.textureWidth - 1), face_uvs[loop_idx][1]/(shp.tim.textureHeigth - 1) )
            vcol_layer.data[loop_idx].color = colors[loop_idx].toFloat()

    blender_mesh.validate()
    blender_mesh.update()

    # compute normals outside
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    # face smooth
    bpy.ops.object.shade_smooth()
    
    return blender_obj


def buildAnimations(shp, seq):
    for i in range(0, seq.numAnimations):
        anim = seq.animations[i]
        anim.build(shp, seq.name+"_Animation_"+repr(i))


def rot13toRad(angle):
	return angle*(math.pi/4096)


class VSWEPHeader:
    def __init__(self):
        self.numBones = 0
        self.numGroups = 0  # group of vertices weighted to a bone
        self.numVertices = 0
        self.numTri = 0
        self.numQuad = 0
        self.numFace = 0  # can be quads or tris or vcolored faces in some SHP
        self.totalPoly = 0
        self.texturePointer1 = 0
        self.dec = 0  # always the same in WEP files, but not when packed in ZUD
        self.bonePtr = 0
        self.groupPtr = 0
        self.vertexPtr = 0
        self.polygonPtr = 0
        self.texturePtr = 0
        self.bones = []
        self.groups = []
        self.vertices = []
        self.faces = []
        self.tim = VSWEPTIM()
        self.rotations = []
        self.isVertexColored = False # always False fo WEP

    def __repr__(self):
        return "(--WEP-- | " + " numBones : "+repr(self.numBones) + " numGroups : "+repr(self.numGroups) + " numTri : "+repr(self.numTri) + " numQuad : "+repr(self.numQuad) + " numFace : "+repr(self.numFace) + " bonePtr : "+repr(self.bonePtr) + " groupPtr : "+repr(self.groupPtr) + " vertexPtr : "+repr(self.vertexPtr) + " polygonPtr : "+repr(self.polygonPtr) + " texturePtr : "+repr(self.texturePtr)+")"

    def getLastGroupVNum(self):
        if self.numGroups > 0:
            return self.groups[self.numGroups-1].numVertices
        else:
            return 0

    def getVerticesForBlender(self):
        bvertices = []
        for i in range(0, self.numVertices):
            vertex = self.vertices[i]
            bvertices.append(vertex.vector())
        return bvertices

    def getFacesForBlender(self):
        bfaces = []
        for i in range(0, self.totalPoly):
            face = self.faces[i]
            if face.type == 0x24:
                bfaces.append(face.vertices)
            elif face.type == 0x2C:
                # little twist for quads
                bfaces.append([face.vertices[0], face.vertices[1],
                               face.vertices[3], face.vertices[2]])
        return bfaces

    def getUVsForBlender(self):
        buvs = []
        for i in range(0, self.totalPoly):
            face = self.faces[i]
            if face.type == 0x24:
                buvs.extend([face.uv[1], face.uv[2], face.uv[0]])
            elif face.type == 0x2C:
                buvs.extend([face.uv[0], face.uv[1], face.uv[3], face.uv[2]])
        return buvs

    def feed(self, file):
        self.numBones, self.numGroups, self.numTri, self.numQuad, self.numFace, self.texturePointer1 = struct.unpack(
            "2B 3H I", file.read(12))
        self.totalPoly = self.numTri+self.numQuad+self.numFace
        self.dec = file.tell()
        file.seek(48, 1)  # padding
        self.texturePtr, self.groupPtr, self.vertexPtr, self.polygonPtr = struct.unpack(
            "4I", file.read(16))
        self.bonePtr = file.tell()
        self.texturePtr += self.dec
        self.groupPtr += self.dec
        self.vertexPtr += self.dec
        self.polygonPtr += self.dec

    def tobin(self):
        bin = bytes()
        bin += (VS_HEADER)
        bin += (struct.pack("2B 3H I", self.numBones, self.numGroups,
                            self.numTri, self.numQuad, self.numFace, self.texturePointer1))
        bin += (bytearray(48))
        bin += (struct.pack("4I", self.texturePtr-self.dec, self.groupPtr -
                            self.dec, self.vertexPtr-self.dec, self.polygonPtr-self.dec))
        for bone in self.bones:
            bin += (bone.tobin())
        for group in self.groups:
            bin += (group.tobin())
        for vertex in self.vertices:
            bin += (vertex.tobin())
        for face in self.faces:
            bin += (face.tobin())
        bin += (self.tim.tobin())
        # Default Rotation
        for i in range(0, 3):  # 3 axis
            bin += struct.pack("4h", 0, 0, 0, 1792)
        return bin

    def fromBlenderMesh(self, blender_mesh):
        verts = blender_mesh.vertices[:]
        facets = [f for f in blender_mesh.polygons]
        self.numBones = 2  # bone 0, is never used by groups, but maybe it is used by VS
        self.numGroups = 1  # we will simplify the WEP output as much as possible
        self.numTri = 0  # need to be determinated
        self.numQuad = 0  # need to be determinated
        self.numFace = 0  # we want this to be 0 if possible

        # WEP BONES SECTION
        self.bones = []
        defaultBone = VSBone()
        defaultBone.defaultBones()
        self.bones.append(defaultBone)
        mainBone = VSBone()
        mainBone.index = 1
        # for the main bone length, we need to check all vertices x value and take the minimal value
        xmin = 0
        for i in range(0, len(verts)):
            xmin = min(xmin, verts[i].co[0]*100)
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
        mainGroup = VSGroup()
        mainGroup.boneIndex = 1
        mainGroup.numVertices = len(verts)
        self.groups.append(mainGroup)
        group_section_size = len(self.groups) * 4

        # WEP VERTEX SECTION
        self.vertices = []
        for i in range(0, len(verts)):
            blender_vert = verts[i]
            vertex = VSVertex()
            vertex.x = int(blender_vert.co[0]*100)
            vertex.y = int(blender_vert.co[1]*100)
            vertex.z = int(blender_vert.co[2]*100)
            vertex.w = 0
            vertex.reverse()
            self.vertices.append(vertex)
        vertex_section_size = len(self.vertices) * 8

        # WEP TEXTURE SECTION
        # we do texture section before face section to get texture width and height for faces UVs
        self.tim = VSWEPTIM()
        mat = blender_mesh.materials[0]
        blender_textures = []
        # default values
        self.tim.textureWidth = 48
        self.tim.textureHeigth = 32
        if mat.node_tree:
            blender_textures.extend(
                [x for x in mat.node_tree.nodes if x.type == 'TEX_IMAGE'])
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
            color = []
            assoc = {}
            pix_count = 0
            for pixel in btex.image.pixels:
                # R G B A - R G B A - ....
                # we must iterate 4 times to get one pixel
                color.append(pixel)
                if len(color) == 4:
                    vs_color = VSColor()
                    vs_color.fromFloat(color[0], color[1], color[2], color[3])
                    #print("vs_color : "+repr(vs_color))
                    color = []
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
                        if self.tim.palletColors[t][self.tim.cluts[pix_count]].code != vs_color.code:
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
        for i in range(0, len(facets)):
            bface = facets[i]
            vnum = len(bface.vertices)
            face = VSFace()
            face.verticesCount = vnum
            face.vertices = []
            face.uv = []
            if vnum == 3:  # its a triangle
                self.numTri += 1
                face.type = 0x24
                face.size = 16
                face.side = 4
                face.alpha = 0
            elif vnum == 4:  # its a quad
                self.numQuad += 1
                face.type = 0x2C
                face.size = 20
                face.side = 4
                face.alpha = 0
            # we need to organize indexes like VS do
            if vnum == 3:
                face.vertices.append(bface.vertices[0])
                face.vertices.append(bface.vertices[1])
                face.vertices.append(bface.vertices[2])
                # uvs needs to be scaled from texture W&H 1,2,0
                face.uv.append([int(uvlayer.data[loop_idx+2].uv[0]*self.tim.textureWidth),
                                int(uvlayer.data[loop_idx+2].uv[1]*self.tim.textureHeigth)])
                face.uv.append([int(uvlayer.data[loop_idx].uv[0]*self.tim.textureWidth),
                                int(uvlayer.data[loop_idx].uv[1]*self.tim.textureHeigth)])
                face.uv.append([int(uvlayer.data[loop_idx+1].uv[0]*self.tim.textureWidth),
                                int(uvlayer.data[loop_idx+1].uv[1]*self.tim.textureHeigth)])
                loop_idx += 3  # inc for each vertex of each face
            if vnum == 4:
                face.vertices.append(bface.vertices[0])
                face.vertices.append(bface.vertices[1])
                face.vertices.append(bface.vertices[3])
                face.vertices.append(bface.vertices[2])
                face.uv.append([int(uvlayer.data[loop_idx].uv[0]*self.tim.textureWidth),
                                int(uvlayer.data[loop_idx].uv[1]*self.tim.textureHeigth)])
                face.uv.append([int(uvlayer.data[loop_idx+1].uv[0]*self.tim.textureWidth),
                                int(uvlayer.data[loop_idx+1].uv[1]*self.tim.textureHeigth)])
                face.uv.append([int(uvlayer.data[loop_idx+3].uv[0]*self.tim.textureWidth),
                                int(uvlayer.data[loop_idx+3].uv[1]*self.tim.textureHeigth)])
                face.uv.append([int(uvlayer.data[loop_idx+2].uv[0]*self.tim.textureWidth),
                                int(uvlayer.data[loop_idx+2].uv[1]*self.tim.textureHeigth)])
                loop_idx += 4
            self.faces.append(face)

        face_section_size = self.numTri * 16
        face_section_size += self.numQuad * 20

        self.dec = 12  # is different in ZUD
        self.bonePtr = self.dec + 48 + 16
        self.groupPtr = self.bonePtr + bone_section_size
        self.vertexPtr = self.groupPtr + group_section_size
        self.polygonPtr = self.vertexPtr + vertex_section_size
        self.texturePtr = self.polygonPtr + face_section_size


class VSBone:
    # https://docs.blender.org/api/current/bpy.types.Bone.html
    def __init__(self):
        self.index = 0
        self.name = ""
        self.length = 0
        self.parent = None
        self.parentIndex = -1
        self.parentName = None
        self.group = None
        self.groupId = 0
        self.mountId = 0
        self.bodyPartId = 0
        self.mode = 0
        self.unk = (0, 0, 0, 0, 0, 0, 0)

    def __repr__(self):
        return "(BONE : " + " index = " + repr(self.index) + " length = " + repr(self.length) + " parentIndex = " + repr(self.parentIndex) + " groupId :" + repr(self.groupId) + " mountId :" + repr(self.mountId) + " bodyPartId :" + repr(self.bodyPartId) + "  mode = " + repr(self.mode) + "  unk = " + repr(self.unk) + ")"

    def defaultBones(self):
        self.index = 0
        self.length = 0
        self.parentIndex = 47
        self.groupId = 255
        self.mountId = 0
        self.bodyPartId = 0
        self.mode = 0
        self.unk = (0, 0, 0, 0, 0, 0, 0)

    def feed(self, file, i):
        self.index = i
        self.name = "bone_" + str(i)
        self.length, self.parentIndex, self.groupId, self.mountId, self.bodyPartId, self.mode = struct.unpack(
            "i 5b", file.read(9))
        self.unk = struct.unpack("7B", file.read(7))
        self.length = -self.length # positive length

    def decalage(self):
        if self.parent != None:
            return self.parent.length + self.parent.decalage()
        else:
            return 0

    def tobin(self):
        return struct.pack("i 12B", self.length, self.parentIndex, self.groupId, self.mountId, self.bodyPartId, self.mode, self.unk[0], self.unk[1], self.unk[2], self.unk[3], self.unk[4], self.unk[5], self.unk[6])

    def binsize(self):
        return 16


class VSGroup:
    def __init__(self):
        self.index = 0
        self.bone = None
        self.boneIndex = -1
        self.numVertices = 0

    def __repr__(self):
        return "(GROUP : "+" boneIndex = "+repr(self.boneIndex)+" numVertices = "+repr(self.numVertices)+")"

    def feed(self, file, i):
        self.index = i
        self.boneIndex, self.numVertices = struct.unpack("hH", file.read(4))

    def tobin(self):
        return struct.pack("hH", self.boneIndex, self.numVertices)

    def binsize(self):
        return 4


class VSVertex:
    def __init__(self):
        self.group = None
        self.bone = None
        self.x = 0
        self.y = 0
        self.z = 0
        self.w = 0  # always 00
        self.index = -1

    def __repr__(self):
        return "(VERTEX : " + " index = " + repr(self.index) + " [x:" + repr(self.x) + ", y:" + repr(self.y) + ", z:" + repr(self.z) + ", w:" + repr(self.w)+"] )"

    def feed(self, file, i):
        self.index = i
        self.x, self.y, self.z, self.w = struct.unpack("4h", file.read(8))

    def tobin(self):
        return struct.pack("4h", self.x, self.y, self.z, self.w)

    def binsize(self):
        return 8

    def reverse(self):
        self.x = -self.x
        self.y = -self.y
        self.z = -self.z

    def swapYZ(self):
        _y = self.y
        _z = self.z
        self.y = _z
        self.z = _y

    def vector(self):
        return (self.x/100, self.y/100, self.z/100)


class VSFace:
    def __init__(self, _type=0, size=0, side=0, flag=0, verticesCount=3, vertices=[], uv=[], colors=[]):
        self.index = 0
        self.type = _type
        self.size = size
        self.side = side
        self.flag = flag
        self.verticesCount = verticesCount
        self.vertices = vertices
        self.uv = uv
        self.colors = colors
        self.isColored = False

    def default(self):
        self.index = 0
        self.type = 0
        self.size = 0
        self.side = 0  # 4 = normal, 5 double sided ?
        self.flag = 0  # unknown
        self.verticesCount = 3
        self.vertices = []
        self.uv = []
        self.colors = []
        self.isColored = False

    def __repr__(self):
        return "(FACE : " + " index = " + repr(self.index) + " type = " + repr(self.type) + " size = " + repr(self.size) + " side = " + repr(self.side) + " flag = " + repr(self.flag) + " vertices = " + repr(self.vertices) + ")"

    def feed(self, file, i, vc=False):
        self.index = i
        self.type, self.size, self.side, self.flag = struct.unpack(
            "4B", file.read(4))
        if vc == False and (self.type == 0x24 or self.type == 0x2C):
            if self.type == 0x24:  # 0x34 is v colored tri
                self.verticesCount = 3
            elif self.type == 0x2C:  # 0x3C is v colored quad
                self.verticesCount = 4
            for i in range(0, self.verticesCount):
                vidx = struct.unpack("H", file.read(2))[0]
                vidx = int(vidx / 4)
                self.vertices.append(vidx)
            for i in range(0, self.verticesCount):
                self.uv.append(struct.unpack("2B", file.read(2)))
                col = VSColor()
                self.colors.append(col.White())
        else:
            # handle v colored faces for special SHP
            self.isColored = True
            file.seek(file.tell()-4)
            # Triangle vt1  vt2  vt3  u1-v1 col1  t  col2   sz col3   sd u2-v2  u3-v3
            # Quad     vt1  vt2  vt3  vt4   col1  t  col2   sz col3   sd col4   pa u1-v1 u2-v2 u3-v3 u4-v4
            self.colors = []
            vIdx = struct.unpack("4H", file.read(8))
            self.colors.append(VSColor().setRGB(
                struct.unpack("3B", file.read(3))))
            self.type = struct.unpack("B", file.read(1))[0]
            self.colors.append(VSColor().setRGB(
                struct.unpack("3B", file.read(3))))
            self.size = struct.unpack("B", file.read(1))[0]
            self.colors.append(VSColor().setRGB(
                struct.unpack("3B", file.read(3))))
            self.side = struct.unpack("B", file.read(1))[0]
            if self.type == 0x34:
                self.verticesCount = 3
                for i in range(0, 3):
                    self.vertices.append(int(vIdx[i]/4))
                # uv1 at the same place of vt4 for quads
                self.uv.append((vIdx[3]).to_bytes(2, 'little'))
                self.uv.append(struct.unpack("2B", file.read(2)))
                self.uv.append(struct.unpack("2B", file.read(2)))
            elif self.type == 0x3C:
                self.verticesCount = 4
                self.colors.append(VSColor().setRGB(
                    struct.unpack("3B", file.read(3))))
                self.flag = struct.unpack("B", file.read(1))[0]  # padding
                for i in range(0, 4):
                    self.vertices.append(int(vIdx[i]/4))
                    self.uv.append(struct.unpack("2B", file.read(2)))

    def tobin(self):
        bin = bytes()
        bin += (struct.pack("4B", self.type, self.size, self.side, self.flag))
        for i in range(0, self.verticesCount):
            # v index should be multiply by 4 for the WEP format
            bin += (struct.pack("H", int(self.vertices[i] * 4)))
        for i in range(0, self.verticesCount):
            bin += (struct.pack("2B", self.uv[i][0], self.uv[i][1]))
        # TODO : handle vertex colored faces
        return bin

    def binsize(self):
        return self.size


class VSColor:
    def White(self):
        self.setRGBA(255, 255, 255, 255)
        return self

    def __init__(self):
        self.R = 0
        self.G = 0
        self.B = 0
        self.A = 0
        self.L = 0  # Light value, 0 is the darkest, 255 the lightest
        self.code = "00000000"

    def __repr__(self):
        return "(COLOR : "+repr(self.code)+")"

    def setRGB(self, rgb):
        self.R = rgb[0]
        self.G = rgb[1]
        self.B = rgb[2]
        self.A = 255
        self.update()
        return self

    def setRGBA(self, r, g, b, a):
        self.R = r
        self.G = g
        self.B = b
        self.A = a
        self.update()
        return self

    def from16bits(self, H):
        # H must be 2bytes long
        b = (H & 0x7C00) >> 10
        g = (H & 0x03E0) >> 5
        r = (H & 0x001F)
        self.R = int(r * 8)
        self.G = int(g * 8)
        self.B = int(b * 8)
        if H == 0:
            self.A = 0  # transparent
        else:
            self.A = 255  # opaque
        self.update()
        return self

    def fromFloat(self, r, g, b, a):
        self.R = r * 255
        self.G = g * 255
        self.B = b * 255
        self.A = a * 255
        self.update()
        return self

    def toRGBA(self):
        return [self.R, self.G, self.B, self.A]

    def toFloat(self):
        return [self.R/255, self.G/255, self.B/255, self.A/255]

    def to32bits(self):
        return "{:02X}{:02X}{:02X}{:02X}".format(round(self.R), round(self.G), round(self.B), round(self.A))

    def to16bits(self):
        # here we compress the color from 4bytes value into 2bytes (16bits : 1bit for alpha + 5bits * R, G and B channels)
        a = 0
        if self.A > 0:
            a = 1
        binstr = "{:01b}{:05b}{:05b}{:05b}".format(
            a, round(self.B / 8), round(self.G / 8), round(self.R / 8))
        # for a certain reason i'm always 0x0080 bytes more than original, maybe a matter of round
        hexv = int(binstr, 2)
        #hexv -= 0x0080
        hexstr = "{:04X}".format(hexv)
        #print("binstr : "+repr(binstr)+"   ---   "+"hexstr : "+repr(hexstr))
        return hexstr

    def update(self):
        self.code = self.to32bits()
        self.L = self.R + self.G + self.B + self.A


class VSAnim:
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
        self.length, self.idOtherAnimation, self.scaleFlags , self.ptrActions, self.ptrTranslation, self.ptrMove = struct.unpack("HbB3H", file.read(10))

        for i in range(0, self.numBones):
            self.ptrBones.append( int(struct.unpack("H", file.read(2))[0]) )
            
        for i in range(0, self.numBones):
            self.ptrBonesScale.append( int(struct.unpack("H", file.read(2))[0]))
    def tobin(self):
        bin = bytes()
        return bin
    def readXYZ(self, file):
        return struct.unpack(">3h", file.read(6))
    def readActions(self, file):
        actions = []
        while True:
            f = int(struct.unpack("B", file.read(1))[0]) #frame number or 0xff
            # TODO probably wrong to break here
            if (f == 0xff):
                break
            if (f > self.length):
                print("Unexpected frame number")
            a = int(struct.unpack("B", file.read(1))[0]) # action
            if (a == 0x00):
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

            if f >= (self.length -1):
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

        if (code & 0xe0) > 0:
            # number of frames, byte case
            f = code & 0x1f
            if (f == 0x1f):
                f = 0x20 + struct.unpack("B", file.read(1))[0]
            else:
                f = 1 + f
        else:
            # number of frames, half word case
            f = code & 0x3
            if (f == 0x3):
                f = 4 + struct.unpack("B", file.read(1))[0]
            else:
                f = 1 + f
            
            # half word values
            code = code << 3
            h = struct.unpack(">h", file.read(2))[0]

            if ((h & 0x4) > 0):
                x = h >> 3
                code = code & 0x60

                if ((h & 0x2) > 0):
                    y = struct.unpack(">h", file.read(2))[0]
                    code = code & 0xa0

                if ((h & 0x1) > 0):
                    z = struct.unpack(">h", file.read(2))[0]
                    code = code & 0xc0
            elif ((h & 0x2) > 0):
                y = h >> 3
                code = code & 0xa0

                if ((h & 0x1) > 0):
                    z = struct.unpack(">h", file.read(2))[0]
                    code = code & 0xc0
            elif ((h & 0x1) > 0):
                z = h >> 3
                code = code & 0xc0
        # byte values (fallthrough)
        if ((code & 0x80) > 0):
            x = struct.unpack("b", file.read(1))[0]
        if ((code & 0x40) > 0):
            y = struct.unpack("b", file.read(1))[0]
        if ((code & 0x20) > 0):
            z = struct.unpack("b", file.read(1))[0]
        return [x, y, z, f]        
    def getData(self, file, seq):
        self.localPtr = self.ptrTranslation+seq.baseOffset+seq.dataOffset
        file.seek(self.localPtr)
        # read translation
        self.trans.append(struct.unpack('>3h', file.read(6))) # BIG_ENDIAN
        self.translationKeys = self.readKeys(file)

        if (self.ptrActions > 0):
            file.seek(seq.ptrData(self.ptrActions))
            self.readActions(file)

        self.rotationPerBone = []
        self.rotationKeysPerBone = []
        self.scalePerBone = []
        self.scaleKeysPerBone = []

        #read bone animation data
        for i in range(0, seq.numBones):
            #default values
            self.rotationPerBone.append([0, 0, 0])
            self.rotationKeysPerBone.append([0, 0, 0, 0])
            self.scalePerBone.append([1, 1, 1])
            self.scaleKeysPerBone.append([1, 1, 1, 0])

            file.seek(seq.ptrData(self.ptrBones[i]))

            if (self.idOtherAnimation == -1):
                self.rotationPerBone[i] = self.readXYZ(file)
            else:
                file.seek(seq.ptrData(seq.animations[self.idOtherAnimation].ptrBones[i]))
                self.rotationPerBone[i] = self.readXYZ(file)

            self.rotationKeysPerBone[i] = (self.readKeys(file))

            #print("getData bone "+repr(i)+"  :  "+repr(seq.ptrData(self.ptrBones[i]))+ "  rot : "+repr(self.rotationPerBone[i]))

            file.seek(seq.ptrData(self.ptrBonesScale[i]))

            if (self.scaleFlags & 0x1):
                self.scalePerBone[i] = (struct.unpack("3B", file.read(3)))

            if (self.scaleFlags & 0x2):
                self.scaleKeysPerBone[i] = self.readKeys(file)
    def build(self, blender_obj, anim_name):
        arm_obj = blender_obj.parent
        arm_obj.animation_data_create()
        arm_obj.animation_data.action = bpy.data.actions.new(name=anim_name)
        for i in range(0, self.numBones):
            bone = arm_obj.pose.bones["bone_"+repr(i)]
            if i < len(self.rotationKeysPerBone):
                keyframes = self.rotationKeysPerBone[i]
                pose = self.rotationPerBone[i]
                
                rx = pose[0]*2
                ry = pose[1]*2
                rz = pose[2]*2
                t = 0
                kfl = len(keyframes)

                for j in range(0, kfl):
                    keyframe = keyframes[j]
                    f = keyframe[3]
                    t += f
                    if keyframe[0] == None:
                        keyframe[0] = keyframes[j-1][0]

                    if keyframe[1] == None:
                        keyframe[1] = keyframes[j-1][1]

                    if keyframe[2] == None:
                        keyframe[2] = keyframes[j-1][2]
                    
                    rx = rx +(keyframe[0]*f)
                    ry = ry +(keyframe[1]*f)
                    rz = rz +(keyframe[2]*f)
                    bone_rotation = ((rot13toRad(rx), rot13toRad(ry), rot13toRad(rz)))

                    # euler rotations isn't good enough for animations interpolations so we build Quaternions
                    #bone.rotation_mode = 'XYZ' 
                    #bone.rotation_euler = bone_rotation
                    #bone.keyframe_insert(data_path='rotation_euler', frame=t)

                    qu = mathutils.Quaternion((1.0, 0.0, 0.0), bone_rotation[0])
                    qv = mathutils.Quaternion((0.0, 1.0, 0.0), bone_rotation[1])
                    qw = mathutils.Quaternion((0.0, 0.0, 1.0), bone_rotation[2])
                    q = qw @ qv @ qu
                    
                    bone.rotation_mode = 'QUATERNION'
                    bone.rotation_quaternion = q
                    bone.keyframe_insert(data_path='rotation_quaternion', frame=t)


class VSWEPTIM:
    def __init__(self):
        self.texMapSize = 0
        self.unk = 0
        self.halfW = 0
        self.halfH = 0
        self.textureWidth = 0
        self.textureHeigth = 0
        self.numColor = 0
        self.palletColors = []
        self.handleColors = []  # common colors between pallets, 1/3 of num colors
        self.textures = []
        self.numPallets = 7
        self.cluts = []

    def __repr__(self):
        return "(TIM : "+" texMapSize = "+repr(self.texMapSize)+" unk = "+repr(self.unk)+" halfW = "+repr(self.halfW)+" halfH = "+repr(self.halfH)+" numColor = "+repr(self.numColor)+")"

    def feed(self, file):
        self.texMapSize, self.unk, self.halfW, self.halfH, self.numColor = struct.unpack(
            "I 4B", file.read(8))
        self.textureWidth = self.halfW * 2
        self.textureHeigth = self.halfH * 2
        self.textures = []
        if self.numColor > 0:
            self.handleColors = []
            for j in range(0, int(self.numColor/3)):
                colorData = struct.unpack("H", file.read(2))[0]
                color = VSColor()
                color.from16bits(colorData)
                color.update()
                self.handleColors.append(color)
            for i in range(0, self.numPallets):
                colors = []
                colors += self.handleColors
                for j in range(0, int(self.numColor/3*2)):
                    colorData = struct.unpack("H", file.read(2))[0]
                    color = VSColor()
                    color.from16bits(colorData)
                    color.update()
                    colors.append(color)
                self.palletColors.append(colors)
            # pallet colors indexes
            cluts = []
            for x in range(0, self.textureWidth):
                for y in range(0, self.textureHeigth):
                    clut = struct.unpack("B", file.read(1))[
                        0]  # CLUT colour reference
                    cluts.append(clut)
            for i in range(0, self.numPallets):
                pixmap = []
                for j in range(0, len(cluts)):
                    if int(cluts[j]) < self.numColor:
                        pixmap.extend(
                            self.palletColors[i][int(cluts[j])].toFloat())
                    else:
                        pixmap.extend(self.palletColors[i][0].toFloat())
                self.textures.append(pixmap)
            # we add pallets colors in the first raw (never used in UVs)
            # by doing this we make sure all colors are used and ordered
            i = 0
            for x in range(0, 7):
                for y in range(0, 48):
                    self.textures[x][i] = self.palletColors[x][y].R / 255
                    self.textures[x][i+1] = self.palletColors[x][y].G / 255
                    self.textures[x][i+2] = self.palletColors[x][y].B / 255
                    self.textures[x][i+3] = self.palletColors[x][y].A / 255
                    i += 4
                i = 0
                #print("self.palletColors[x] : "+repr(self.palletColors[x]))

    def tobin(self):
        bin = bytes()
        bin += (struct.pack("I 4B", self.texMapSize, self.unk,
                            self.halfW, self.halfH, self.numColor))
        for i in range(0, 16):  # 16 = 48/3
            if i < len(self.handleColors):
                bin += (struct.pack("H",
                                    int(self.handleColors[i].to16bits(), 16)))
            else:
                bin += (struct.pack("H", 65535))
        for i in range(0, 7):
            for j in range(16, 48):
                if i < len(self.palletColors):
                    if j < len(self.palletColors[i]):
                        bin += (struct.pack("H",
                                            int(self.palletColors[i][j].to16bits(), 16)))
                    else:
                        bin += (struct.pack("H", 65535))
                else:
                    bin += (struct.pack("H", 65535))

        i = 0
        for x in range(0, self.textureWidth):
            for y in range(0, self.textureHeigth):
                if i < len(self.cluts):
                    bin += (struct.pack("B", self.cluts[i]))
                else:
                    bin += (b"\x00")
                i += 1
        return bin

    def binsize(self):
        size = 8  # tim header
        # we considere 48 colors
        size += 16 * 2  # handle colors
        size += 32 * 2 * 7  # pallets colors
        size += self.textureWidth * self.textureHeigth  # clut one byte per pixel
        return size


class VSSHPTIM:
    def __init__(self):
        self.texMapSize = 0
        self.unk = 0
        self.halfW = 0
        self.halfH = 0
        self.textureWidth = 0
        self.textureHeigth = 0
        self.numColor = 0
        self.palletColors = []
        self.textures = []
        self.numPallets = 2
        self.cluts = []
        self.doubleClut = False

    def __repr__(self):
        return "(TIM : "+" texMapSize = "+repr(self.texMapSize)+" unk = "+repr(self.unk)+" halfW = "+repr(self.halfW)+" halfH = "+repr(self.halfH)+" numColor = "+repr(self.numColor)+")"

    def feed(self, file):
        self.texMapSize, self.unk, self.halfW, self.halfH, self.numColor = struct.unpack("I 4B", file.read(8))
        self.textureWidth = self.halfW * 2
        self.textureHeigth = self.halfH * 2
        self.textures = []
        if self.numColor > 0:
            for i in range(0, self.numPallets):
                colors = []
                for j in range(0, int(self.numColor)):
                    colorData = struct.unpack("H", file.read(2))[0]
                    color = VSColor()
                    color.from16bits(colorData)
                    colors.append(color)
                self.palletColors.append(colors)
            # pallet colors indexes
            cluts = []
            for x in range(0, self.textureWidth):
                for y in range(0, self.textureHeigth):
                    if self.doubleClut == False:
                        clut = struct.unpack("B", file.read(1))[0]  # CLUT colour reference
                        cluts.append(clut)
                    else:
                        # when colored faces a single byte is two pixels
                        id = struct.unpack("B", file.read(1))[0]
                        cluts.append(id % 16)
                        cluts.append(id // 16)
            for i in range(0, self.numPallets):
                pixmap = []
                for j in range(0, len(cluts)):
                    if int(cluts[j]) < self.numColor:
                        pixmap.extend(self.palletColors[i][int(cluts[j])].toFloat())
                    else:
                        pixmap.extend(self.palletColors[i][0].toFloat())
                self.textures.append(pixmap)   
        if self.doubleClut == True:  # when colored faces we must multiply by 4
            self.textureWidth = self.halfW * 4
        # TODO : inverse textures and UVs 

    def tobin(self):
        bin = bytes()
        bin += (struct.pack("I 4B", self.texMapSize, self.unk,
                            self.halfW, self.halfH, self.numColor))
        for i in range(0, 2):
            for j in range(0, self.numColor):
                if i < len(self.palletColors):
                    if j < len(self.palletColors[i]):
                        bin += (struct.pack("H", int(self.palletColors[i][j].to16bits(), 16)))
                    else:
                        bin += (struct.pack("H", 65535))
                else:
                    bin += (struct.pack("H", 65535))

        i = 0
        for x in range(0, self.textureWidth):
            for y in range(0, self.textureHeigth):
                if i < len(self.cluts):
                    bin += (struct.pack("B", self.cluts[i]))
                else:
                    bin += (b"\x00")
                i += 1
        return bin

    def binsize(self):
        size = 8  # tim header
        # we considere 48 colors
        size += 16 * 2  # handle colors
        size += 32 * 2 * 7  # pallets colors
        size += self.textureWidth * self.textureHeigth  # clut one byte per pixel
        return size


class VSZUDHeader:
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
        return "(--ZUD-- | " + " idSHP : " + repr(self.idSHP) + " idWEP : " + repr(self.idWEP) + " idWEPType : " + repr(self.idWEPType) + " idWEPMat : " + repr(self.idWEPMat) + " idWEP2 : " + repr(self.idWEP2) + " idWEP2Mat : " + repr(self.idWEP2Mat) + " uk : " + repr(self.uk) + " pad : " + repr(self.pad)+")"

    def feed(self, file):
        self.idSHP, self.idWEP, self.idWEPType, self.idWEPMat, self.idWEP2, self.idWEP2Mat, self.uk, self.pad = struct.unpack(
            "8B", file.read(8))
        self.ptrSHP, self.lenSHP, self.ptrWEP, self.lenWEP, self.ptrWEP2, self.lenWEP2, self.ptrCSEQ, self.lenCSEQ, self.ptrBSEQ, self.lenBSEQ = struct.unpack(
            "10I", file.read(40))


class VSSHPHeader:
    def __init__(self):
        self.numBones = 0
        self.numGroups = 0  # group of vertices weighted to a bone
        self.numVertices = 0
        self.numTri = 0
        self.numQuad = 0
        self.numFace = 0  # can be quads or tris or vcolored faces in some SHP
        self.totalPoly = 0
        self.overlays = []
        self.dec = 0  # always the same in WEP files, but not when packed in ZUD
        self.isVertexColored = False
        self.bonePtr = 0
        self.groupPtr = 0
        self.vertexPtr = 0
        self.polygonPtr = 0
        self.texturePtr = 0
        self.magicPtr = 0
        self.AKAOPtr = 0
        self.bones = []
        self.groups = []
        self.vertices = []
        self.faces = []
        self.tim = VSWEPTIM()
        self.rotations = []
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
        return "(--SHP-- | " + " numBones : "+repr(self.numBones) + " numGroups : "+repr(self.numGroups) + " numTri : "+repr(self.numTri) + " numQuad : "+repr(self.numQuad) + " numFace : "+repr(self.numFace) + " bonePtr : "+repr(self.bonePtr) + " groupPtr : "+repr(self.groupPtr) + " vertexPtr : "+repr(self.vertexPtr) + " polygonPtr : "+repr(self.polygonPtr) + " texturePtr : "+repr(self.texturePtr)+")"

    def getLastGroupVNum(self):
        if self.numGroups > 0:
            return self.groups[self.numGroups-1].numVertices
        else:
            return 0

    def getVerticesForBlender(self):
        bvertices = []
        for i in range(0, self.numVertices):
            vertex = self.vertices[i]
            bvertices.append(vertex.vector())
        return bvertices

    def getFacesForBlender(self):
        bfaces = []
        for i in range(0, self.totalPoly):
            face = self.faces[i]
            if face.type == 0x24 or face.type == 0x34:
                bfaces.append(face.vertices)
            elif face.type == 0x2C or face.type == 0x3C:
                # little twist for quads
                bfaces.append([face.vertices[0], face.vertices[1],
                               face.vertices[3], face.vertices[2]])
        return bfaces

    def getUVsForBlender(self):
        buvs = []
        for i in range(0, self.totalPoly):
            face = self.faces[i]
            if face.type == 0x24 or face.type == 0x34:
                buvs.extend([face.uv[1], face.uv[2], face.uv[0]])
            elif face.type == 0x2C or face.type == 0x3C:
                buvs.extend([face.uv[0], face.uv[1], face.uv[3], face.uv[2]])
        return buvs

    def getVColForBlender(self):
        vcols = []
        for i in range(0, self.totalPoly):
            face = self.faces[i]
            if face.type == 0x24 or face.type == 0x34:
                vcols.extend([face.colors[0], face.colors[1], face.colors[2]])
            elif face.type == 0x2C or face.type == 0x3C:
                vcols.extend([face.colors[0], face.colors[1],
                              face.colors[3], face.colors[2]])
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


    def feed(self, file):
        self.numBones, self.numGroups, self.numTri, self.numQuad, self.numFace = struct.unpack("2B 3H", file.read(8))
        self.totalPoly = self.numTri+self.numQuad+self.numFace
        self.dec = file.tell()
        self.overlays = []
        for i in range(0, 8):
            self.overlays.append(struct.unpack("4b", file.read(4)))
        self.unk1 = struct.unpack("36b", file.read(36))
        self.collider = struct.unpack("6b", file.read(6))
        self.menuYpos = struct.unpack("h", file.read(2))[0]
        self.unk2 = struct.unpack("12b", file.read(12))
        self.shadowRadius, self.shadowInc, self.shadowDec, self.h1, self.h2, self.menuScale, self.h3, self.tSphereYpos, self.h4, self.h5, self.h6, self.h7 = struct.unpack("12h", file.read(24))
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
        self.dec = file.tell()+4
        # pointer to magic effects section (relative to offset $F8)
        self.magicPtr = struct.unpack("I", file.read(4))[0] + self.dec
        self.unk3 = struct.unpack("24H", file.read(48))
        self.AKAOPtr, self.groupPtr, self.vertexPtr, self.polygonPtr = struct.unpack("4I", file.read(16))
        self.bonePtr = file.tell()
        self.AKAOPtr += self.dec
        self.groupPtr += self.dec
        self.vertexPtr += self.dec
        self.polygonPtr += self.dec

    def tobin(self):
        bin = bytes()
        bin += (VS_HEADER)
        bin += (struct.pack("2B 3H", self.numBones, self.numGroups, self.numTri, self.numQuad, self.numFace))
        # TODO
        return bin


class VSSEQHeader:
    def __init__(self):
        self.name = "SEQ"
        self.numSlots = 0
        self.numBones = 0
        self.size = 0
        self.baseOffset = 0
        self.dataOffset = 0
        self.slotOffset = 0
        self.headerOffset = 0
        self.numAnimations = 0
        self.animations = []

    def __repr__(self):
        return "(--SEQ--"+" numSlots : "+repr(self.numSlots)+" numBones : "+repr(self.numBones)+" size : "+repr(self.size)+" dataOffset : "+repr(self.dataOffset)+" slotOffset : "+repr(self.slotOffset)+" headerOffset : "+repr(self.headerOffset)+")"

    def feed(self, file):
        self.baseOffset = file.tell()  # base ptr needed because SEQ may be embedded
        self.numSlots, self.numBones, self.size, self.dataOffset, self.slotOffset = struct.unpack(
            '2H3I', file.read(16))
        self.dataOffset += 8  # offset to animation data
        self.slotOffset += 8  # offset to slots
        # offset to rotation and keyframe data
        self.headerOffset = self.slotOffset + self.numSlots
        self.numAnimations = int(
            (self.dataOffset - self.numSlots - 16) / (self.numBones * 4 + 10))

    def ptrData(self, i):
        return i + self.headerOffset + self.baseOffset

    def tobin(self):
        bin = bytes()
        return bin
