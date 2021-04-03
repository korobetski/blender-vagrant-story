bl_info = {
    "name": "Vagrant Story file formats Add-on",
    "description": "Import-Export Vagrant Story file formats (WEP, SHP, SEQ, ZUD, MPD, ZND, P, FBT, FBC).",
    "author": "Sigfrid Korobetski (LunaticChimera)",
    "version": (2, 1),
    "blender": (2, 92, 0),
    "location": "File > Import-Export",
    "category": "Import-Export",
}

import bpy
from . import WEP, SHP, SEQ, MPD, ZND, ZUD, TIM, ARM, EFFECT, color

# https://docs.blender.org/api/current/bpy.props.html

class MaterialPalette(bpy.types.PropertyGroup):
    bl_idname = "material.palette"
    bl_label = "Palette"
    ref: bpy.props.StringProperty(name="palette")
    #color: bpy.props.FloatVectorProperty(name="color")

class BoneDatas(bpy.types.PropertyGroup):
    # we store additionnal "unused" datas to rebuild imported formats
    bl_idname = "bone.datas"
    bl_label = "VS Datas"
    mountId: bpy.props.IntProperty(name="groupId")
    bodyPartId: bpy.props.IntProperty(name="bodyPartId")
    mode: bpy.props.IntProperty(name="mode")
    unk: bpy.props.IntVectorProperty(name="unk")

class MeshDatas(bpy.types.PropertyGroup):
    # we store additionnal "unused" datas to rebuild imported formats
    bl_idname = "mesh.datas"
    bl_label = "VS Datas"
    # we use bpy.types.Mesh.polygon_layers_int instead of custom props
    #faces_sides: bpy.props.IntVectorProperty(name="faces_sides")
    #faces_flags: bpy.props.IntVectorProperty(name="faces_flags")
    rots0: bpy.props.IntVectorProperty(name="rots0")
    rots1: bpy.props.IntVectorProperty(name="rots1")
    rots2: bpy.props.IntVectorProperty(name="rots2")


classes = (
    WEP.Import,
    WEP.Export,
    SHP.Import,
    ZUD.Import,
    MPD.Import,
    EFFECT.Import,
    ARM.Import,
    MaterialPalette,
    BoneDatas,
    MeshDatas
)

def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

    bpy.types.Material.palette = bpy.props.PointerProperty(type=MaterialPalette)
    bpy.types.EditBone.datas = bpy.props.PointerProperty(type=BoneDatas)
    bpy.types.Mesh.datas = bpy.props.PointerProperty(type=MeshDatas)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

def menu_func_import(self, context):
    self.layout.operator(WEP.Import.bl_idname, text="Vagrant Story Weapon (.WEP)")
    self.layout.operator(SHP.Import.bl_idname, text="Vagrant Story Character Shape (.SHP)")
    # self.layout.operator(ImportSEQ.bl_idname, text="Vagrant Story Animations Sequence (.SEQ)")
    self.layout.operator(ZUD.Import.bl_idname, text="Vagrant Story Zone Unit Datas (.ZUD)")
    self.layout.operator(MPD.Import.bl_idname, text="Vagrant Story Map Datas (.MPD)")
    #self.layout.operator(ImportZND.bl_idname,text="Vagrant Story Zone Datas(.ZND)")
    self.layout.operator(EFFECT.Import.bl_idname, text="Vagrant Story Effect (.P)")
    self.layout.operator(ARM.Import.bl_idname, text="Vagrant Story Maps (.ARM)")

def menu_func_export(self, context):
    self.layout.operator(WEP.Export.bl_idname, text="Vagrant Story Weapon (.WEP)")