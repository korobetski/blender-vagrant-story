bl_info = {
    "name": "Vagrant Story file formats Add-on",
    "description": "Import-Export Vagrant Story file formats (WEP, SHP, SEQ, ZUD, MPD, ZND, P, FBT, FBC).",
    "author": "Sigfrid Korobetski (LunaticChimera)",
    "version": (2, 1),
    "blender": (2, 92, 0),
    "location": "File > Import-Export",
    "category": "Import-Export",
}

import os
import struct
import math

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, StringProperty
from bpy_extras.io_utils import ExportHelper, ImportHelper

from . import VertexSection, FaceSection, Kildean


class Import(bpy.types.Operator, ImportHelper):
    """Load a ARM file"""

    bl_idname = "import_mesh.arm"
    bl_label = "Import ARM"
    filename_ext = ".ARM"

    filepath: bpy.props.StringProperty(default="", subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.ARM", options={"HIDDEN"})

    def execute(self, context):
        keywords = self.as_keywords(ignore=("axis_forward","axis_up","filter_glob",))
        BlenderImport(self, context, **keywords)

        return {"FINISHED"}


def BlenderImport(operator, context, filepath):
    arm = ARM()
    # we read datas from a file
    arm.loadFromFile(filepath)
    
    # Creating Geometry and Meshes for Blender
    arm.buildGeometry()


class ARM:
    def __init__(self):
        self.numRooms = 0
        self.rooms = []
        self.filesize = 0
    def __repr__(self):
        return("(--"+repr(self.name)+".ARM-- | "+repr(self.rooms)+")")
    def loadFromFile(self, filepath):
        self.filesize = os.stat(filepath).st_size
        # Open a ARM file and parse it
        file = open(filepath, "rb")
        self.name = bpy.path.display_name(filepath)
        self.parse(file)
        file.close()
    def parse(self, file):
        self.numRooms = struct.unpack("I", file.read(4))[0]
        self.rooms = []
        for i in range (0, self.numRooms):
            room = ARMRoom()
            room.u1, room.length, room.zoneId, room.roomId = struct.unpack("2I2H", file.read(12))
            self.rooms.append(room)
        
        for i in range (0, self.numRooms):
            self.rooms[i].numVertices = struct.unpack("I", file.read(4))[0]
            self.rooms[i].vertices = []
            for j in range (0, self.rooms[i].numVertices):
                vertex = VertexSection.Vertex()
                vertex.feed(file, j)
                self.rooms[i].vertices.append(vertex)

            self.rooms[i].numTriangles = struct.unpack("I", file.read(4))[0]
            self.rooms[i].faces = []
            for j in range (0, self.rooms[i].numTriangles):
                face = FaceSection.Face()
                face.verticesCount = 3
                face.type = 0x24
                # the last byte is a padding but nevermind
                face.vertices = struct.unpack("4B", file.read(4))
                self.rooms[i].faces.append(face)

            self.rooms[i].numQuads = struct.unpack("I", file.read(4))[0]
            for j in range (0, self.rooms[i].numQuads):
                face = FaceSection.Face()
                face.verticesCount = 4
                face.type = 0x2C
                face.vertices = struct.unpack("4B", file.read(4))
                self.rooms[i].faces.append(face)
            
            self.rooms[i].numFloorEdges = struct.unpack("I", file.read(4))[0]
            self.rooms[i].edges = []
            for j in range (0, self.rooms[i].numFloorEdges):
                edge = Edge()
                edge.isFloor = True
                edge.vertices = struct.unpack("2B", file.read(2))
                padding = struct.unpack("2B", file.read(2))
                self.rooms[i].edges.append(edge)
            
            self.rooms[i].numCeilEdges = struct.unpack("I", file.read(4))[0]
            for j in range (0, self.rooms[i].numCeilEdges):
                edge = Edge()
                edge.vertices = struct.unpack("2B", file.read(2))
                padding = struct.unpack("2B", file.read(2))
                self.rooms[i].edges.append(edge)

            self.rooms[i].numMarkers = struct.unpack("I", file.read(4))[0]
            self.rooms[i].markers = []
            for j in range (0, self.rooms[i].numMarkers):
                self.rooms[i].markers.append(struct.unpack("4B", file.read(4)))

        # Rooms Names
        if (file.tell() + 36 <= self.filesize):
            for i in range (0, self.numRooms):
                nums1 = struct.unpack("3H", file.read(6))
                rawName = file.read(24)
                roomName = Kildean.Translate(rawName).split("\r\n")[0]
                self.rooms[i].name = roomName
                nums2 = struct.unpack("3H", file.read(6))


    def buildGeometry(self):
        print("ARM Building...")

        
        for i in range (0, self.numRooms):
            # Creating Geometry and Mesh for Blender
            room = self.rooms[i]
            mesh_name = room.name
            blender_mesh = bpy.data.meshes.new(name=mesh_name + "_MESH")
            blender_mesh.from_pydata(room.getVerticesForBlender(), room.getEdgesForBlender(), room.getFacesForBlender())

            # Creating Materials & Textures for Blender
            # https://docs.blender.org/api/current/bpy.types.Material.html


            # Creating Blender object and link into the current collection
            blender_obj = bpy.data.objects.new(str(room.name), object_data=blender_mesh)
            view_layer = bpy.context.view_layer
            view_layer.active_layer_collection.collection.objects.link(blender_obj)
            blender_obj.select_set(True)

            view_layer.objects.active = blender_obj
            blender_mesh.validate()
            blender_mesh.update()




class ARMRoom:
    def __init__(self):
        self.name = ""
        self.u1 = 0
        self.length = 0
        self.zoneId = 0
        self.roomId = 0
        self.numVertices = 0
        self.vertices = []
        self.numTriangles = 0
        self.numQuads = 0
        self.faces = []
        self.numFloorEdges = 0
        self.numCeilEdges = 0
        self.edges = []
        self.numMarkers = 0
        self.markers = []
    def __repr__(self):
        return("(--"+repr(self.name)+" ARM ROOM-- | )")

    
    def getVerticesForBlender(self):
        bvertices = []
        for vertex in self.vertices:
            bvertices.append(vertex.blenderSwaped())
        return bvertices

    def getEdgesForBlender(self):
        bedges = []
        for edge in self.edges:
            bedges.append(edge.vertices)
        return bedges

    def getFacesForBlender(self):
        bfaces = []
        for face in self.faces:
            if face.type == 0x24:
                bfaces.append([face.vertices[2],face.vertices[1],face.vertices[0]])
            elif face.type == 0x2C:
                # little twist for quads
                bfaces.append([face.vertices[0],face.vertices[1],face.vertices[2] ,face.vertices[3]])
        return bfaces

class Edge:
    def __init__(self):
        self.isFloor = False
        self.vertices = []