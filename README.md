# Vagrant Story Blender addon

Blender addon for importing / exporting Vagrant Story (Squaresoft 2000) file formats
Vagrant Story files formats are mostly explained here : http://datacrystal.romhacking.net/wiki/Vagrant_Story:File_formats

<img src="https://github.com/korobetski/blender-vagrant-story/raw/master/export.png"/>

# Purpose :

The goal of this addon is mainly for modding purpose, use with cautions

# Supported Formats :

For now the only format supported for import and export is *.WEP Weapon Model format
Maybe more formats in the future...

# Limitations :

WEP format can handle complex geometry, but you must take care of fee things :
- imported WEP can contains mistakes
- double sided faces arn't supported yet, the information is lost for export for now
- vertices position are stored in int16 for 3 axis, so float values will be rounded
- face can be Triangle or Quad, but Ngon arn't possible yet
- the textures section is highly optimized and compressed, and work with 7 pallets of 32 colors + one common pallet of 16 colors. When importing a WEP, the pallet will be the first 48 pixels of textures (common + unique)
if you want to change textures you can just use colors defined by pallets and adding more colors is a non explored teritory. We can change pallets colors, but the 16 first colors MUST be the same for each pallets (common colors).
This section is also the biggest part of the WEP format weight (~75%), so making textures in higher resolution can cause memory burden quickly.
Considering all these things, modifying textures in an efficient way can be an hard task, and maybe not fully supported by this addon yet anyway.
- in the original game *.WEP file size is between 2ko and 7ko so keep an eye on this before patching VS with a too big .WEP

# Instalation :

In Blender 2.91 go to Edit / Preferences...
in Addons window clic install and choose <a href="https://github.com/korobetski/blender-vagrant-story/raw/master/vs_blender.py">vs_blender.py</a> file downloaded from this repository

# Discord :

https://discord.gg/Wtmnkqd5

<img src="https://github.com/korobetski/blender-vagrant-story/raw/master/uv_map_addon_win.png"/>
