import bpy
import bmesh
import struct
import os

from bpy_extras.io_utils import (ImportHelper,
                                 ExportHelper)

from bpy.props import (BoolProperty,
    FloatProperty,
    StringProperty,
    EnumProperty,
    )

bl_info = {
    "name": "Vagrant Story formats Add-on",
    "description": "Import-Export Vagrant Story WEP mesh format.",
    "author": "Sigfrid Korobetski (LunaticChimera)",
    "version":(1, 0),
    "blender": (2, 91, 0),
    "location": "File > Import-Export",
    "category": "Import-Export",
}

class ImportWEP(bpy.types.Operator, ImportHelper):
    """Load a WEP Mesh file"""
    bl_idname = "import_mesh.wep"
    bl_label = "Import WEP Mesh"
    filename_ext = ".WEP"

    filepath : bpy.props.StringProperty(default="",subtype="FILE_PATH")
    filter_glob : bpy.props.StringProperty(default="*.WEP", options={'HIDDEN'})

    def execute(self, context):
        keywords = self.as_keywords(ignore=('axis_forward',
            'axis_up',
            'filter_glob',
        ))
        mesh = loadWEP(self, context, **keywords)
        if not mesh:
            return {'CANCELLED'}

        blender_obj = bpy.data.objects.new(str(bpy.path.display_name_from_filepath(keywords["filepath"])), object_data=mesh)
        view_layer = bpy.context.view_layer
        view_layer.active_layer_collection.collection.objects.link(blender_obj)
        blender_obj.select_set(True)
        view_layer.objects.active = blender_obj
        return {'FINISHED'}

class ExportWEP(bpy.types.Operator, ExportHelper):
    """Save a WEP Mesh file"""
    bl_idname = "export_mesh.wep"
    bl_label = "Export WEP Mesh"
    check_extension = True
    filename_ext = ".WEP"

    filter_glob : bpy.props.StringProperty(default="*.WEP", options={'HIDDEN'})

    def execute(self, context):
        keywords = self.as_keywords(ignore=('axis_forward',
            'axis_up',
            'filter_glob',
            'check_existing',
        ))
        return saveWEP(self, context, **keywords)

def menu_func_import(self, context):
    self.layout.operator(ImportWEP.bl_idname, text="Vagrant Story WEP Mesh (.WEP)")

def menu_func_export(self, context):
    self.layout.operator(ExportWEP.bl_idname, text="Vagrant Story WEP Mesh (.WEP)")

classes = (
    ImportWEP,
    ExportWEP,
)

VS_HEADER = b"H01\x00"

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

    # EOF
    file.close()



    # Creating Material & Textures for Blender
    # https://docs.blender.org/api/current/bpy.types.Material.html
    mat = bpy.data.materials.new(name=str(bpy.path.display_name_from_filepath(filepath)+'_Material'))
    mat.use_nodes = True
    mat.blend_method = "CLIP" # to handle alpha cutout
    # maybe i should consider using a simpler material... VS doesn't need a PBR Material :D
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs['Specular'].default_value = 0
    bsdf.inputs['Metallic'].default_value = 0
    for i in range(0, len(wep.tim.textures)):
        texImage = mat.node_tree.nodes.new('ShaderNodeTexImage')
        texImage.image = bpy.data.images.new(str(bpy.path.display_name_from_filepath(filepath)+'_Tex'+str(i)), wep.tim.textureWidth, wep.tim.textureHeigth)
        texImage.image.pixels = wep.tim.textures[i]
        texImage.interpolation = "Closest" # texture filter
        # we use the first texture for the material by default
        if i == 0:
            mat.node_tree.links.new(bsdf.inputs['Base Color'], texImage.outputs['Color'])
            mat.node_tree.links.new(bsdf.inputs['Alpha'], texImage.outputs['Alpha']) # to handle alpha cutout

    # Creating Geometry and Mesh for Blender
    mesh_name = bpy.path.display_name_from_filepath(filepath)
    blender_mesh = bpy.data.meshes.new(name=mesh_name+"_MESH")
    blender_mesh.from_pydata(wep.getVerticesForBlender(), [], wep.getFacesForBlender())
    # TODO : we need to handle double sided faces
    blender_mesh.materials.append(mat)
    blender_mesh.validate()
    blender_mesh.update()

    # Creating UVs for Blender
    uvlayer = blender_mesh.uv_layers.new()
    face_uvs = wep.getUVsForBlender()
    for face in blender_mesh.polygons:
        # loop_idx increment for each vertex of each face so if there is 9 triangle -> 9*3 = 27 loop_idx, even if some vertex are common between faces
        for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
            # uvs needs to be scaled from texture W&H
            uvlayer.data[loop_idx].uv = (face_uvs[loop_idx][0]/(wep.tim.textureWidth-1), face_uvs[loop_idx][1]/(wep.tim.textureHeigth-1))
    
    return blender_mesh

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
        print(group)
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
        vertex.reverse()
        print(vertex)
        # easy trick to weight vertices without armature
        # but WEP will need bones for Export mode i supose so maybe we'll should make bones in all case
        vertex.x += vertex.bone.decalage()
        mesh.vertices.append(vertex)

def parseFaceSection(file, mesh):
    face_uvs = []
    for i in range(0, mesh.totalPoly):
        face = VSFace()
        face.default()
        face.feed(file, i)
        print(face)
        mesh.faces.append(face)

def parseTextureSection(file, mesh):
    tim = VSWEPTIM()
    tim.feed(file, mesh)
    print(tim)

class VSWEPHeader:
    def __init__(self):
        self.numBones = 0
        self.numGroups = 0 # group of vertices weighted to a bone
        self.numVertices = 0
        self.numTri = 0
        self.numQuad = 0
        self.numFace = 0 # can be quads or tris or vcolored faces in some SHP
        self.totalPoly = 0
        self.texturePointer1 = 0
        self.dec = 0 # always the same in WEP files, but not when packed in ZUD
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
    def __repr__(self):
        return "(--WEP-- | "+ " numBones : "+repr(self.numBones)+ " numGroups : "+repr(self.numGroups)+ " numTri : "+repr(self.numTri)+ " numQuad : "+repr(self.numQuad)+ " numFace : "+repr(self.numFace) + " bonePtr : "+repr(self.bonePtr)+ " groupPtr : "+repr(self.groupPtr)+ " vertexPtr : "+repr(self.vertexPtr)+ " polygonPtr : "+repr(self.polygonPtr)+ " texturePtr : "+repr(self.texturePtr)+")"
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
                bfaces.append([face.vertices[0], face.vertices[1], face.vertices[3], face.vertices[2]])
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
        self.numBones, self.numGroups, self.numTri, self.numQuad, self.numFace, self.texturePointer1 = struct.unpack("2B 3H I", file.read(12))
        self.totalPoly = self.numTri+self.numQuad+self.numFace
        self.dec = file.tell()
        file.seek(48, 1) # padding
        self.texturePtr, self.groupPtr, self.vertexPtr, self.polygonPtr = struct.unpack("4I", file.read(16))
        self.bonePtr = file.tell()
        self.texturePtr += self.dec
        self.groupPtr += self.dec
        self.vertexPtr += self.dec
        self.polygonPtr += self.dec
    def tobin(self):
        bin = bytes()
        bin += (VS_HEADER) 
        bin += (struct.pack("2B 3H I", self.numBones, self.numGroups, self.numTri, self.numQuad, self.numFace, self.texturePointer1))
        bin += (bytearray(48))
        bin += (struct.pack("4I", self.texturePtr-self.dec, self.groupPtr-self.dec, self.vertexPtr-self.dec, self.polygonPtr-self.dec))
        for bone in self.bones:
            bin += (bone.tobin())
        for group in self.groups:
            bin += (group.tobin())
        for vertex in self.vertices:
            bin += (vertex.tobin())
        for face in self.faces:
            bin += (face.tobin())
        bin += (self.tim.tobin())
        return bin
    def fromBlenderMesh(self, blender_mesh):
        verts = blender_mesh.vertices[:]
        facets = [ f for f in blender_mesh.polygons ]

        self.numBones = 2 # bone 0, is never used by groups, but maybe it is used by VS
        self.numGroups = 1 # we will simplify the WEP output as much as possible
        self.numTri = 0 # need to be determinated
        self.numQuad = 0 # need to be determinated
        self.numFace = 0 # we want this to be 0 if possible
        
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
        mainBone.unk = (0,0,0,0,0,0,0)
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
            blender_textures.extend([x for x in mat.node_tree.nodes if x.type=='TEX_IMAGE'])
            if len(blender_textures) > 0:
                self.tim.textureWidth = blender_textures[0].image.size[0]
                self.tim.textureHeigth = blender_textures[0].image.size[1]
        self.tim.halfW = int(self.tim.textureWidth / 2)
        self.tim.halfH = int(self.tim.textureHeigth / 2)
        self.tim.unk = 1 # must be a flag that say how to decode the pallets
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
            btex = blender_textures[t] # ShaderNodeTexImage btex
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
            if vnum == 3: # its a triangle
                self.numTri += 1
                face.type = 0x24
                face.size = 16
                face.side = 4
                face.alpha = 0
            elif vnum == 4: # its a quad
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
                face.uv.append([int(uvlayer.data[loop_idx+2].uv[0]*self.tim.textureWidth), int(uvlayer.data[loop_idx+2].uv[1]*self.tim.textureHeigth)])
                face.uv.append([int(uvlayer.data[loop_idx].uv[0]*self.tim.textureWidth), int(uvlayer.data[loop_idx].uv[1]*self.tim.textureHeigth)])
                face.uv.append([int(uvlayer.data[loop_idx+1].uv[0]*self.tim.textureWidth), int(uvlayer.data[loop_idx+1].uv[1]*self.tim.textureHeigth)])
                loop_idx += 3 # inc for each vertex of each face
            if vnum == 4:
                face.vertices.append(bface.vertices[0])
                face.vertices.append(bface.vertices[1])
                face.vertices.append(bface.vertices[3])
                face.vertices.append(bface.vertices[2])
                face.uv.append([int(uvlayer.data[loop_idx].uv[0]*self.tim.textureWidth), int(uvlayer.data[loop_idx].uv[1]*self.tim.textureHeigth)])
                face.uv.append([int(uvlayer.data[loop_idx+1].uv[0]*self.tim.textureWidth), int(uvlayer.data[loop_idx+1].uv[1]*self.tim.textureHeigth)])
                face.uv.append([int(uvlayer.data[loop_idx+3].uv[0]*self.tim.textureWidth), int(uvlayer.data[loop_idx+3].uv[1]*self.tim.textureHeigth)])
                face.uv.append([int(uvlayer.data[loop_idx+2].uv[0]*self.tim.textureWidth), int(uvlayer.data[loop_idx+2].uv[1]*self.tim.textureHeigth)])
                loop_idx += 4
            self.faces.append(face)

        face_section_size = self.numTri * 16
        face_section_size += self.numQuad * 20

        self.dec = 12 # is different in ZUD
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
        self.groupId = 0
        self.mountId = 0
        self.bodyPartId = 0
        self.mode = 0
        self.unk = (0,0,0,0,0,0,0)
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
        self.unk = (0,0,0,0,0,0,0)
    def feed(self, file, i):
        self.index = i
        self.name = "bone_" + str(i)
        self.length, self.parentIndex, self.groupId, self.mountId, self.bodyPartId, self.mode = struct.unpack("i 5B", file.read(9))
        self.unk = struct.unpack("7B", file.read(7))
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
        self.w = 0 # always 00
        self.index = -1
    def __repr__(self):
        return "(VERTEX : " + " index = " + repr(self.index) + " [x:" + repr(self.x) + ", y:" + repr(self.y) + ", z:" + repr(self.z)+"] )"
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
    def vector(self):
        return (self.x/100, self.y/100, self.z/100)

class VSFace:
    def __init__(self, _type=0, size=0, side=0, alpha=0, verticesCount=3, vertices=[], uv=[], colors=[]):
        self.type = _type
        self.size = size
        self.side = side
        self.alpha = alpha
        self.verticesCount = verticesCount
        self.vertices = vertices
        self.uv = uv
        self.colors = colors
    def default(self):
        self.type = 0
        self.size = 0
        self.side = 0
        self.alpha = 0
        self.verticesCount = 3
        self.vertices = []
        self.uv = []
        self.colors = []
    def __repr__(self):
        return "(FACE : " + " type = "+ repr(self.type) + " size = "+ repr(self.size) + " side = "+ repr(self.side) + " alpha = "+ repr(self.alpha) + " verticesCount = "+ repr(self.verticesCount) + ")"
    def feed(self, file, i):
        # TODO : handle v colored faces
        self.type, self.size, self.side, self.alpha = struct.unpack("4B", file.read(4))
        if self.type == 0x24 or self.type == 0x34:
            self.verticesCount = 3
        elif self.type == 0x2C or self.type == 0x3C:
            self.verticesCount = 4
        for i in range(0, self.verticesCount):
            vidx = struct.unpack("H", file.read(2))[0]
            vidx = vidx / 4
            self.vertices.append(vidx)
        for i in range(0, self.verticesCount):
            self.uv.append(struct.unpack("2B", file.read(2)))
            self.colors.append((0, 0, 0, 0))
    def tobin(self):
        bin = bytes()
        bin += (struct.pack("4B", self.type, self.size, self.side, self.alpha))
        for i in range(0, self.verticesCount):
            bin += (struct.pack("H", int(self.vertices[i] * 4))) # v index should be multiply by 4 for the WEP format
        for i in range(0, self.verticesCount):
            bin += (struct.pack("2B", self.uv[i][0], self.uv[i][1]))
        return bin
    def binsize(self):
        return self.size

class VSColor:
    def __init__(self):
        self.R = 0
        self.G = 0
        self.B = 0
        self.A = 0
        self.L = 0 # Light value, 0 is the darkest, 255 the lightest
        self.code = "00000000"
    def __repr__(self):
        return "(COLOR : "+repr(self.code)+")"
    def setRGBA(self, r, g, b, a):
        self.R = r
        self.G = g
        self.B = b
        self.A = a
        self.update()
    def from16bits(self, H):
        # H must be 2bytes long
        b = (H & 0x7C00) >> 10
        g = (H & 0x03E0) >> 5
        r = (H & 0x001F)
        self.R = int(r * 8)
        self.G = int(g * 8)
        self.B = int(b * 8)
        if H == 0:
            self.A = 0 # transparent
        else:
            self.A = 255 # opaque
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
        binstr = "{:01b}{:05b}{:05b}{:05b}".format(a, round(self.B / 8), round(self.G / 8), round(self.R / 8))
        # for a certain reason i'm always 0x0080 bytes more than original, maybe a matter of round
        hexv = int(binstr, 2)
        #hexv -= 0x0080
        hexstr = "{:04X}".format(hexv)
        #print("binstr : "+repr(binstr)+"   ---   "+"hexstr : "+repr(hexstr))
        return hexstr
    def update(self):
        self.code = self.to32bits()
        self.L = self.R + self.G + self.B + self.A

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
        self.handleColors = [] # common colors between pallets, 1/3 of num colors
        self.textures = []
        self.numPallets = 7
        self.cluts = []
    def __repr__(self):
        return "(TIM : "+" texMapSize = "+repr(self.texMapSize)+" unk = "+repr(self.unk)+" halfW = "+repr(self.halfW)+" halfH = "+repr(self.halfH)+" numColor = "+repr(self.numColor)+")"
    def feed(self, file, mesh):
        self.texMapSize, self.unk, self.halfW, self.halfH, self.numColor = struct.unpack("I 4B", file.read(8))
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
                    clut = struct.unpack("B", file.read(1))[0]  # CLUT colour reference
                    cluts.append(clut)
            for i in range(0, self.numPallets):
                pixmap = []
                for j in range(0, len(cluts)):
                    if int(cluts[j]) < self.numColor:
                        pixmap.extend(self.palletColors[i][int(cluts[j])].toFloat())
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
        mesh.tim = self
    def tobin(self):
        bin = bytes()
        bin += (struct.pack("I 4B", self.texMapSize, self.unk, self.halfW, self.halfH, self.numColor))
        for i in range(0, 16): # 16 = 48/3
            if i < len(self.handleColors):
                bin += (struct.pack("H", int(self.handleColors[i].to16bits(), 16)))
            else:
                bin += (struct.pack("H", 65535))
        for i in range(0, 7):
            for j in range(16, 48):
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
        size = 8 # tim header
        # we considere 48 colors
        size += 16 * 2 # handle colors
        size += 32 * 2 * 7 # pallets colors
        size += self.textureWidth * self.textureHeigth # clut one byte per pixel
        return size
