#http://datacrystal.romhacking.net/wiki/Vagrant_Story:MPD_files

import struct

import bpy
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
        # file.seek(self.header.ptrRoomSection) useless
        if self.header.lenRoomSection > 96:
            self.room.feed(file)
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