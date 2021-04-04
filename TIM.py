bl_info = {
    "name": "Vagrant Story file formats Add-on",
    "description": "Import-Export Vagrant Story file formats (WEP, SHP, SEQ, ZUD, MPD, ZND, P, FBT, FBC).",
    "author": "Sigfrid Korobetski (LunaticChimera)",
    "version": (2, 1),
    "blender": (2, 92, 0),
    "location": "File > Import-Export",
    "category": "Import-Export",
}

import struct
import bpy
from . import color

class WEPTIM:
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
        return "(TIM : "+ " texMapSize = "+ repr(self.texMapSize)+ " unk = "+ repr(self.unk)+ " halfW = "+ repr(self.halfW)+ " halfH = "+ repr(self.halfH)+ " numColor = "+ repr(self.numColor)+ ")"

    def feed(self, file):
        self.texMapSize,self.unk,self.halfW,self.halfH,self.numColor = struct.unpack("I 4B", file.read(8))
        self.textureWidth = self.halfW * 2
        self.textureHeigth = self.halfH * 2
        self.textures = []
        if self.numColor > 0:
            self.handleColors = []
            for j in range(0, int(self.numColor / 3)):
                colorData = struct.unpack("H", file.read(2))[0]
                self.handleColors.append(color.from16bits(colorData))
            for i in range(0, self.numPallets):
                colors = []
                colors += self.handleColors
                for j in range(0, int(self.numColor / 3 * 2)):
                    colorData = struct.unpack("H", file.read(2))[0]
                    colors.append(color.from16bits(colorData))
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
                    self.textures[x][i + 1] = self.palletColors[x][y].G / 255
                    self.textures[x][i + 2] = self.palletColors[x][y].B / 255
                    self.textures[x][i + 3] = self.palletColors[x][y].A / 255
                    i += 4
                i = 0

    def tobin(self):
        bin = bytes()
        bin += struct.pack("I 4B", self.texMapSize, self.unk, self.halfW, self.halfH, self.numColor)
        for i in range(0, 16):  # 16 = 48/3
            if i < len(self.handleColors):
                bin += struct.pack("H", int(self.handleColors[i].to16bits(), 16))
            else:
                bin += struct.pack("H", 65535)
        for i in range(0, 7):
            for j in range(16, 48):
                if i < len(self.palletColors):
                    if j < len(self.palletColors[i]):
                        bin += struct.pack("H", int(self.palletColors[i][j].to16bits(), 16))
                    else:
                        bin += struct.pack("H", 65535)
                else:
                    bin += struct.pack("H", 65535)

        i = 0
        for x in range(0, self.textureWidth):
            for y in range(0, self.textureHeigth):
                if i < len(self.cluts):
                    bin += struct.pack("B", self.cluts[i])
                else:
                    bin += b"\x00"
                i += 1
        return bin

    def binsize(self):
        size = 8  # tim header
        # we considere 48 colors per palette
        size += 16 * 2  # handle colors
        size += 32 * 2 * 7  # palettes colors
        size += self.textureWidth * self.textureHeigth  # indexes one byte per pixel
        return size

class SHPTIM:
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
        return "(TIM : "+ " texMapSize = "+ repr(self.texMapSize)+ " unk = "+ repr(self.unk)+ " halfW = "+ repr(self.halfW)+ " halfH = "+ repr(self.halfH)+ " numColor = "+ repr(self.numColor)+ ")"

    def feed(self, file):
        self.texMapSize,self.unk,self.halfW,self.halfH,self.numColor = struct.unpack("I 4B", file.read(8))
        self.textureWidth = self.halfW * 2
        self.textureHeigth = self.halfH * 2
        self.textures = []
        if self.numColor > 0:
            for i in range(0, self.numPallets):
                colors = []
                for j in range(0, int(self.numColor)):
                    colorData = struct.unpack("H", file.read(2))[0]
                    colors.append(color.from16bits(colorData))
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
                        pixmap.extend(
                            self.palletColors[i][int(cluts[j])].toFloat())
                    else:
                        pixmap.extend(self.palletColors[i][0].toFloat())
                self.textures.append(pixmap)
        if self.doubleClut == True:  # when colored faces we must multiply by 4
            self.textureWidth = self.halfW * 4
        # TODO : inverse textures and UVs

    def tobin(self):
        bin = bytes()
        bin += struct.pack("I 4B", self.texMapSize, self.unk, self.halfW, self.halfH, self.numColor)
        for i in range(0, 2):
            for j in range(0, self.numColor):
                if i < len(self.palletColors):
                    if j < len(self.palletColors[i]):
                        bin += struct.pack("H", int(self.palletColors[i][j].to16bits(), 16))
                    else:
                        bin += struct.pack("H", 65535)
                else:
                    bin += struct.pack("H", 65535)

        i = 0
        for x in range(0, self.textureWidth):
            for y in range(0, self.textureHeigth):
                if i < len(self.cluts):
                    bin += struct.pack("B", self.cluts[i])
                else:
                    bin += b"\x00"
                i += 1
        return bin


class TIM16BPP:
    # 16BPP TIM Header
    # [1-4]   - 10 00 00 00: ID Tag for TIM
    # [5-8]   - 02 00 00 00: ID Tag for 16BPP
    # [9-12]  - Size of image data + 12 (accounting for 12 bytes before image data starts)
    # [13-14] - Image Org X
    # [15-16] - Image Org Y
    # [17-18] - Image Width (Stored as actual width)
    # [19-20] - Image Height
    def __init__(self):
        self.h = 0
        self.bpp = 0
        self.imgLen = 0
        self.fx = 0
        self.fy = 0
        self.width = 0
        self.height = 0
        self.dataLen = 0
        self.dataPtr = 0
        self.idx = ""
        self.texture = None
        self.offset = 0
        self.isCLUT = False
        self.bytes = bytearray()
        self.colors = []
    
    def __repr__(self):
        return (
            "(--TIM16BPP-- |  "+ " offset : "+repr(self.offset)+ ", idx : "+repr(self.idx)+ ", h : "+repr(self.h)+ ", bpp : "+repr(self.bpp)+ ", imgLen : "
            +repr(self.imgLen)+ ", fx : "+repr(self.fx)+ ", fy : "+repr(self.fy)+ ", width : "+repr(self.width)+ ", height : "+repr(self.height)
        )

    def parse(self, idx, file, offset, len):
        self.offset = offset
        self.idx = idx
        self.h, self.bpp, self.imgLen, self.fx, self.fy, self.width, self.height = struct.unpack("3I4H", file.read(20))
        self.dataLen = self.imgLen - 12
        self.dataPtr = file.tell()
        # we fill a bytearray because we don't know yet if the TIM is an index or a CLUT
        self.bytes = bytearray()
        self.bytes = file.read(self.dataLen)
        file.seek(self.dataPtr)
        # if fy != 0 it seems to be a CLUT
        # so we store colors
        if  self.fy != 0:
            self.isCLUT = True
            self.colors = []
            for x in range(0, self.width):
                for y in range(0, self.height):
                    colorData = struct.unpack("H", file.read(2))[0]
                    col = color.from16bits(colorData)
                    self.colors.append(col)
                    # fb.setPixel(self.fx + x, self.fy + y, col)
        #else:
        #    size = self.width * self.height * 2
        #    pixmap = []
        #    for i in range(0, size):
        #        c = self.bytes[i]
        #        l = ( ( c & 0xF0 ) >> 4 )
        #        r = ( c & 0x0F )            
        #        pixmap.extend(color.GreyCLUT[r].toFloat())
        #        pixmap.extend(color.GreyCLUT[l].toFloat())
        #    texImage = bpy.data.textures.new("TIM16BPP-"+repr(self.idx), 'IMAGE')
        #    texImage.image = bpy.data.images.new("TIM16BPP-"+repr(self.idx), self.width*4, self.height)
        #    texImage.image.pixels = pixmap

        

    def buildCLUT(self, x, y, alpha = False):
        ox = x - self.fx
        oy = y - self.fy
        dec = oy * self.width + ox
        bufferArray = []
        for i in range(dec, dec+16):
            col = self.colors[i]
            if alpha == True:
               col.alphaFromGrey() 
            bufferArray.append(col)
        return bufferArray

    def build(self, clut):
        size = self.width * self.height * 2
        pixmap = []
        for i in range(0, size):
            c = self.bytes[i]
            l = ( ( c & 0xF0 ) >> 4 )
            r = ( c & 0x0F )            
            pixmap.extend(clut[r].toFloat())
            pixmap.extend(clut[l].toFloat())
        return pixmap



# we don't need this anymore
class FrameBuffer:
    def __init__(self):
        self.width = 1024
        self.height = 512
        self.buffer = bytearray()
        # clean empty frame
        self.r = self.width*self.height*4
        for i in range(0, self.r):
            self.buffer += b"\x00"

    def setPixel(self, x, y, col):
        i = (y * self.width + x) * 4
        self.buffer[i + 0] = col.R
        self.buffer[i + 1] = col.G
        self.buffer[i + 2] = col.B
        self.buffer[i + 3] = col.A
    
    def buildTexture(self):
        pixmap = []
        for i in range(0, self.r):
            pixmap.append(self.buffer[i]/255)    
        texImage = bpy.data.textures.new("FrameBuffer", 'IMAGE')
        texImage.image = bpy.data.images.new("FrameBuffer_Tex", self.width, self.height)
        texImage.image.pixels = pixmap
