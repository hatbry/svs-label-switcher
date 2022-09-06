TAGNAMES = {
    254: 'NewSubfileType', 
    255: 'SubfileType', 
    256: 'ImageWidth', 
    257: 'ImageLength',
    258: 'BitsPerSample',
    259: 'Compression',
    262: 'PhotometricInterpretation',
    263: 'Thresholding',
    264: 'CellWidth',
    264: 'CellLength',
    270: 'ImageDescription',
    273: 'StripOffsets',
    277: 'Orientation', 
    278: 'RowsPerStrip',
    279: 'StripByteCounts',
    282: 'XResolution',
    283: 'YResolution',
    284: 'PlanarConfiguration',
    317: 'Predictor',
    322: 'TileWidth',
    323: 'TileLength',
    324: 'TileOffsets',
    325: 'TileByteCounts',
    32997: 'ImageDepth', 
    34675: 'TiffTag_ICCProfile'
}

PHOTOMETRIC_INTERPRETATION = {
    0: 'WhiteIsZero',
    1: 'BlackIsZero',
    2: 'RGB',
    3: 'RGP Palette',
    4: 'Transparency mask',
    5: 'CMYK',
    6: 'YCbCr',
    8: 'CIELab'
}

COMPRESSION = {
    1: 'Uncompressed',
    2: 'CCIT 1D',
    3: 'Group 3 Fax', 
    4: 'Group 4 Fax',
    5: 'LZW',
    6: 'JPEG',
    7: 'JPEG 7',
    32773: 'PackBits'
    }

TYPE_DICT = {
    2: 'ASCII',
    3: 'SHORT',
    4: 'LONG',
    7: 'UNDEFINED/:?ASCII',
    11: 'FLOAT',
    12: 'DOUBLE',
    16: 'LONG8'
}

FORMAT_CHARACTERS = {
    2: 'c',
    3: 'H',
    4: 'L',
    5: 'LL',
    6: 'b',
    7: 'c',
    8: 'h',
    9: 'l',
    10: 'll',
    11: 'f',
    12: 'd',
    16: 'Q'
}