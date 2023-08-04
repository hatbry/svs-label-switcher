import tkinter as tk
from tkinter import messagebox
from tkinter.filedialog import askopenfilename
from PIL import Image, ImageTk
import sys
import os


'''
Useful resource: https://www.awaresystems.be/imaging/tiff/bigtiff.html
'''

import sys
import os
import argparse
import io
import numpy as np
import pandas as pd
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import qrcode
import struct
import time



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

TIFF_LABEL_IFD_TAG_VALUES = {
    254: {'type': 4, 'count': 1, 'value': (1,)},
    256: {'type': 4, 'count': 1, 'value': None}, #width
    257: {'type': 4, 'count': 1, 'value': None}, #height
    258: {'type': 3, 'count': 3, 'value': None, 'data': (8, 8, 8)},
    259: {'type': 3, 'count': 1, 'value': (5,)}, # COMPRESSION
    262: {'type': 3, 'count': 1, 'value': (2,)},
    273: {'type': 4, 'count': 1, 'value': (180, )}, # STRIP OFFSETS
    277: {'type': 3, 'count': 1, 'value': (3,)},
    278: {'type': 3, 'count': 1, 'value': None},
    279: {'type': 4, 'count': 1, 'value': None}, # STRIP BYTE COUNTS
    284: {'type': 3, 'count': 1, 'value': (1,)},
    317: {'type': 3, 'count': 1, 'value': (2,)}
}

BIG_TIFF_LABEL_TEMPLATE = {
    254: {'type': 4, 'count': 1, 'value': (9,)}, #1 is label, 9 is macro
    256: {'type': 4, 'count': 1, 'value': None}, #Width
    257: {'type': 4, 'count': 1, 'value': None}, #Length
    258: {'type': 3, 'count': 3, 'value': (8, 8, 8)},
    259: {'type': 3, 'count': 1, 'value': (1,)},
    262: {'type': 3, 'count': 1, 'value': (2,)},
    270: {'type': 2, 'count': None, 'value': None}, # Count = len of value; value = bytes(string)
    273: {'type': 16, 'count': 1, 'value': None}, #strip offset
    277: {'type': 3, 'count': 1, 'value': (3,)},
    278: {'type': 4, 'count': 1, 'value': None}, #Rows per strip - same as length
    279: {'type': 16, 'count': 1, 'value': None}, #Strip byte counts, length of image data
    282: {'type': 5, 'count': 1, 'value': (1, 1)}, 
    283: {'type': 5, 'count': 1, 'value': (1, 1)}, 
    284: {'type': 3, 'count': 1, 'value': (1,)},
    296: {'type': 3, 'count': 1, 'value': (1,)},
}


class LabelSaver():
    def __init__(self) -> None:
        """Saves the label from a whole-slide SVS image file. Useful
        when the label IFD does not contain tag 270 with the word "label". 
        This primarily applies to GT450 V1.0.0 software. Leica added the 270 tag
        back in V1.0.1
        """
        self.img = io.BytesIO()

    def label(self, label_data, label_dir_info):
        """Creates a PIL Image using the label data and directory info from BigTiffFile.

        Args:
            label_data (bytes): label image data as bytes
            label_dir_info (dict): label directory information from BigTiffFile

        Returns:
            PIL.Image: Pillow Image object
        """
        self._write_tiff_header()
        self._write_tiff_ifds(label_data, label_dir_info)
        return Image.open(self.img)

    def _write_tiff_header(self):
        endian = 'II'.encode('UTF-8')
        version = struct.pack('<H', 42)
        initial_offset = struct.pack('<H', 8)
        reserved = struct.pack('<H', 0)
        header = endian + version + initial_offset + reserved
        self.img.write(header)
        self.img.seek(8)
    
    def _write_tiff_ifds(self, image_data: bytes, label_directory_info: dict):
        # data must be just the image data in bytes; no headers or IFDs
        #each IFD is 12 bytes, the header is 8, and 4 bytes at the end of
        #the IFD to the next IFD (or 0 if last IFD in file)
        num_entries = len(TIFF_LABEL_IFD_TAG_VALUES)
        extra_data_offset = num_entries * 12 + 8 + 8

        width = label_directory_info['label ifd info'][256]['value']
        height = label_directory_info['label ifd info'][257]['value']
        bits_per_sample = label_directory_info['label ifd info'][258]['value']
        rows_per_strip = label_directory_info['label ifd info'][278]['value']
        compression = label_directory_info['label ifd info'][259]['value']

        TIFF_LABEL_IFD_TAG_VALUES[256]['value'] = width
        TIFF_LABEL_IFD_TAG_VALUES[257]['value'] = height
        TIFF_LABEL_IFD_TAG_VALUES[258]['value'] = bits_per_sample
        TIFF_LABEL_IFD_TAG_VALUES[278]['value'] = rows_per_strip
        TIFF_LABEL_IFD_TAG_VALUES[279]['value'] = (len(image_data),)
        TIFF_LABEL_IFD_TAG_VALUES[259]['value'] = compression
            
        self.img.write(struct.pack('<H', num_entries))

        for ifd, values in TIFF_LABEL_IFD_TAG_VALUES.items():

            # First, write IFD tag, type, and count
            self.img.write(struct.pack('<H', ifd))
            self.img.write(struct.pack('<H', values['type']))
            self.img.write(struct.pack('<L', values['count']))
            
            # Determine the size of the data
            count = str(values['count'])
            _type = FORMAT_CHARACTERS[values['type']]
            fmt = '<' + count + _type

            # If the size of the data is greater than 'L', the data is too large to fit in the IFD
            # and must be placed elsewhere
            if struct.calcsize(fmt) > struct.calcsize('<L'):
                values['value'] = (extra_data_offset, )

                # Write the location where the data will be placed in the IFD
                self.img.write(struct.pack('<L', *values['value']))
                
                # Mark the current position to return to after writing the data
                current_position = self.img.tell()

                # Go to a place in the file with no data.
                self.img.seek(extra_data_offset)

                data_to_write = label_directory_info['label ifd info'][ifd]['value']
                data_to_write = struct.pack(fmt, *data_to_write)
                self.img.write(data_to_write)

                # Mark the new position to insert additional data later
                new_position = self.img.tell()

                # Make sure position is on a word boundary
                if new_position % 2 != 0:
                    new_position += 1

                # Update the offset for any additional new information
                extra_data_offset = new_position

                # Return to the IFD location
                self.img.seek(current_position)
            else:
                # If the data is not too large, it is written as the value/offset in the IFD
                if ifd == 273:
                    TIFF_LABEL_IFD_TAG_VALUES[273]['value'] = (extra_data_offset, )

                self.img.write(struct.pack(fmt, *values['value']))
                post_value_position = self.img.tell()

                data_size = struct.calcsize(fmt)
                word_boundary_size = struct.calcsize('<L')
                if data_size < word_boundary_size:
                    self.img.seek(post_value_position + (word_boundary_size - data_size))
        
        self.img.seek(TIFF_LABEL_IFD_TAG_VALUES[273]['value'][0])
        self.img.write(image_data)
        self.img.seek(0)


class BigTiffMaker():
    def __init__(self, img_data: np.ndarray, label_or_macro: str, description: str=None) -> None:
        self.label_or_macro = label_or_macro
        self.img = io.BytesIO()
        self.img_data = img_data

        self.height = None
        self.width = None
        self._update_image_info()

        self.img_data = img_data.tobytes()
        self.strip_byte_counts = len(self.img_data)

        self.tiff_template = BIG_TIFF_LABEL_TEMPLATE.copy()
        
        self._update_tiff_template(description)

    def create_image(self):
        header, offset = self._write_bigtiff_header()
        
        self.img.write(header)
        self.img.seek(offset)

        self._write_ifds()
        return self.img

    def _update_tiff_template(self, description):
        self.tiff_template[256]['value'] = (self.width,)
        self.tiff_template[257]['value'] = (self.height,)
        self.tiff_template[278]['value'] = (self.height,)
        self.tiff_template[279]['value'] = (len(self.img_data),)
        if self.label_or_macro.lower() == 'label':
            self.tiff_template[254]['value'] = (1,)
        elif self.label_or_macro.lower() == 'macro':
            self.tiff_template[254]['value'] = (9,)
        else:
            error = f'"{self.label_or_macro}" must be either "label" or "macro"'
            raise ValueError(error)

        if description is None:
            self.tiff_template.pop(270, None)
        else:
            count = len(description)
            self.tiff_template[270]['count'] = count

            description = [x.encode('UTF-8') for x in description]
            self.tiff_template[270]['data'] = description


    def _update_image_info(self):
        shape = self.img_data.shape
        self.width = int(shape[1])
        self.height = int(shape[0])
        

    def _write_bigtiff_header(self):
        endian = 'II'.encode('UTF-8')
        version = struct.pack('<H', 43)
        offset_size = struct.pack('<H', 8)
        reserved = struct.pack('<H', 0)
        first_ifd_offset = 16
        initial_offset = struct.pack('<Q', first_ifd_offset)
        header = endian + version + offset_size + reserved + initial_offset
        
        return header, first_ifd_offset


    def _write_ifds(self):

        num_entries = len(self.tiff_template)

        IFD_SIZE = 20 # each IFD is 20 bytes
        NUM_ENTRIES_SIZE = 16 # number of entries stored as 8 bytes
        NEXT_OFFSET_SIZE = 16 # the offset of the next directory is stored in 8 bytes
        extra_data_offset = NUM_ENTRIES_SIZE + num_entries * IFD_SIZE + NEXT_OFFSET_SIZE

        self.img.write(struct.pack('<Q', num_entries))

        for IFD_tag, tag_info in self.tiff_template.items(): #HHQQ
            self.img.write(struct.pack('<H', IFD_tag))
            self.img.write(struct.pack('<H', tag_info['type']))
            self.img.write(struct.pack('<Q', tag_info['count']))

            fmt = '<' + str(tag_info['count']) + FORMAT_CHARACTERS[tag_info['type']]

            if struct.calcsize(fmt) > struct.calcsize('Q'):
                tag_info['value'] = (extra_data_offset, )

                self.img.write(struct.pack('<Q', *tag_info['value']))

                current_position = self.img.tell()

                self.img.seek(extra_data_offset)

                data_to_write = tag_info['data']
                
                self.img.write(struct.pack(fmt, *data_to_write))

                new_position = self.img.tell()

                if new_position % 2 != 0:
                    new_position += 1

                # Update the offset for any additional new information
                extra_data_offset = new_position

                # Return to the IFD location
                self.img.seek(current_position)
            
            else:
                if IFD_tag == 273:
                    self.tiff_template[273]['value'] = (extra_data_offset, )
                    extra_data_offset += 16
                distance_to_move = struct.calcsize('Q')
                current_position = self.img.tell()
                self.img.write(struct.pack(fmt, *tag_info['value']))
                self.img.seek(current_position + distance_to_move)
        if self.label_or_macro == 'macro':
            self.img.write(struct.pack('<Q', 0))
        self.img.seek(self.tiff_template[273]['value'][0])
        self.img.write(self.img_data)
        self.img.seek(0)

class BigTiffFile():
    def __init__(self, file_path) -> None:
        """Reads BigTiff file header and IFD information. The information can be printed for
        informational purposes. Can be used in isolation with de_identify_slide to overwrite 
        the label and macro images in SVS files.

        Args:
            file_path (str | BytesIO): file path as a string or image as a BytesIO object
        """
        self.file_path = file_path
        self.tiff_info = {}
        self.next_dir_offsets = {}
        self.directory_offsets = {}
        self.directory_count = 0

        self._label = None
        self._macro = None

        #TODO add classic tiff support
        self.endian = None
        self.bigtiff = False

        if isinstance(file_path, io.BytesIO):
            bigtiff = file_path
            next_offset = self._read_header(bigtiff)
            while next_offset != 0:  
                next_offset = self._read_IFDs(bigtiff, next_offset)
        else:
            with open(file_path, 'rb') as bigtiff:
                next_offset = self._read_header(bigtiff)
                while next_offset != 0:  
                    next_offset = self._read_IFDs(bigtiff, next_offset)  
                self._get_label_and_macro_info()


    def de_identify_slide(self):
        """Overwrites the macro and label data with 0s.
        """
        label_strip_offset = self._label['strip offset']
        label_byte_count = self._label['strip byte counts']
        macro_strip_offset = self._macro['strip offset']
        macro_byte_count = self._macro['strip byte counts']

        with open(self.file_path, 'rb+') as tiff:
            tiff.seek(label_strip_offset)
            tiff.write(b'\0' * label_byte_count)
            tiff.seek(macro_strip_offset)
            tiff.write(b'\0' * macro_byte_count)


    def get_label(self):
        """Returns the label image as a Pillow Image object
        """
        ls = LabelSaver()
        img = ls.label(self.label_data, self.label_info)
        return img

    def print_IFDs(self, writer=sys.stdout):
        writer.write('=' * 80 + '\n')
        writer.write('=' * 80 + '\n')
        for directory, ifds in self.tiff_info.items():
            writer.write('*' * 80 + '\n')
            writer.write(f'DIRECTORY:\t{directory}\t\t Offset: {self.directory_offsets[directory]}' + '\n')
            for ifd_tag, ifd_data in ifds.items():
                writer.write('_' * 80 + '\n')
                writer.write('IFD Offset: {}\n'.format(ifd_data.get('pre_tag_offset')))
                writer.write('IFD Tag:\t{}\t{}'.format(ifd_tag, TAGNAMES.get(ifd_tag)) + '\n')
                writer.write('IFD Type:\t{}\t{}'.format(ifd_data.get('ifd_type'), TYPE_DICT.get(ifd_data.get('ifd_type'))) + '\n')
                writer.write('IFD Count:\t{}'.format(ifd_data.get('ifd_count')) + '\n')
                writer.write('Data Offset:\t{}'.format(ifd_data.get('data_offset')) + '\n')
                writer.write('Value:\t\t{}'.format(ifd_data.get('value')) + '\n')
            writer.write('Next Directory Offset: {}\n'.format(self.next_dir_offsets[directory]['next_ifd_offset']))
            writer.write('\n')

    def _fmt(self, fmt):
        if not self.bigtiff:
            fmt = fmt.replace('Q', 'H')

    def _read_header(self, bigtiff):
        endian = bigtiff.read(2).decode('UTF-8')
        if endian == 'II':
            self.endian = '<'
        else:
            endian = '>'

        version = struct.unpack('<H', bigtiff.read(struct.calcsize('H')))[0]
        if version == 43:
            self.bigtiff = True
        elif version == 42:
            self.bigtiff == False
        else:
            raise ValueError('Incorrect file type')
        offset_size, reserved = struct.unpack('<HH', bigtiff.read(struct.calcsize('HH')))

        if self.bigtiff:
            initial_offset = struct.unpack('<Q', bigtiff.read(struct.calcsize('Q')))[0]
        else:
            initial_offset = offset_size
          
        return initial_offset
        
    def _read_IFDs(self, bigtiff, directory_offset):
        self.directory_count += 1
        bigtiff.seek(directory_offset)
        IFD_info = {}
        if self.bigtiff:
            entries_fmt = self.endian + 'Q'
            tag_fmt = self.endian + 'HHQ'
            data_offset_fmt = self.endian + 'Q'
            next_offset_fmt = self.endian + 'Q'
        else:
            entries_fmt = self.endian + 'H'
            tag_fmt = self.endian + 'HHL'
            data_offset_fmt = self.endian + 'L'
            next_offset_fmt = self.endian + 'L'
        
        num_of_entries = struct.unpack(entries_fmt, bigtiff.read(struct.calcsize(entries_fmt)))[0]

        for _ in range(num_of_entries):
            tag_offset = bigtiff.tell()
            IFD_tag, IFD_type, IFD_count = struct.unpack(tag_fmt, bigtiff.read(struct.calcsize(tag_fmt)))
            pre_data_offset = bigtiff.tell()
            data_offset = struct.unpack(data_offset_fmt, bigtiff.read(struct.calcsize(data_offset_fmt)))[0]

            IFD_info[IFD_tag] = {
                'pre_tag_offset': tag_offset,
                'ifd_type': IFD_type,
                'ifd_count': IFD_count,
                'pre_data_offset': pre_data_offset,
                'data_offset': data_offset,
                'value': self._ifd_value(IFD_tag, IFD_type, IFD_count, pre_data_offset, data_offset, bigtiff)
            }
        # position before the next IFD offset. This can be used to change
        # the location of the next IFD
        offset_before_next_ifd_offset = bigtiff.tell()
        next_ifd_offset = struct.unpack(next_offset_fmt, bigtiff.read(struct.calcsize(next_offset_fmt)))[0]
        self.tiff_info[self.directory_count] = IFD_info
        self.directory_offsets[self.directory_count] = directory_offset
        self.next_dir_offsets[self.directory_count] = {
            'pre_offset_offset': offset_before_next_ifd_offset,
            'next_ifd_offset': next_ifd_offset,
            'directory_offset': directory_offset
        }
        return next_ifd_offset
    

    def _ifd_value(self, ifd_tag, ifd_type, ifd_count, pre_data_offset, data_offset, bigtiff):
        fmt = '<' + str(ifd_count) + FORMAT_CHARACTERS[ifd_type]
        length = struct.calcsize(fmt)
        if self.bigtiff:
            size = 'Q'
        else:
            size = 'L'
        if length <= struct.calcsize(size):
            start = bigtiff.tell()
            bigtiff.seek(pre_data_offset)
            value = struct.unpack(fmt, bigtiff.read(struct.calcsize(fmt)))
            bigtiff.seek(start)
        elif ifd_tag in [270, 258]:
            current_position = bigtiff.tell()
            bigtiff.seek(data_offset)
            value = struct.unpack(fmt, bigtiff.read(struct.calcsize(fmt)))
            if TYPE_DICT.get(ifd_type) == 'ASCII':
                value = b''.join(value)
            bigtiff.seek(current_position)
        else:
            return 'Too long to display'
        return value

    def _get_label_and_macro_info(self):
        #the label is the second to last directory, compressed with LZW, and may (depending
        #on Leica software version) have label in tag 270
        proposed_label_directory = len(self.tiff_info.items()) - 1
        proprosed_macro_directory = len(self.tiff_info.items())

        label_compression = self.tiff_info[proposed_label_directory][259]['data_offset']
        try:
            image_description = self.tiff_info[proposed_label_directory][270]['value']
        except Exception:
            image_description = None

        #if COMPRESSION.get(label_compression) == 'LZW' or b'label' in image_description or b'Label' in image_description:
        self._label = {
            'label directory': proposed_label_directory,
            'label ifd info': self.tiff_info[proposed_label_directory],
            'strip offset': self.tiff_info[proposed_label_directory][273]['data_offset'],
            'strip byte counts': self.tiff_info[proposed_label_directory][279]['data_offset']
        }

        macro_compression = self.tiff_info[proprosed_macro_directory][259]['data_offset']
        try:
            image_description = self.tiff_info[proprosed_macro_directory][270]['value']
        except Exception:
            image_description = None

        #if COMPRESSION.get(macro_compression) in ['JPEG', 'JPEG 7'] or b'macro' in image_description or b'Macro' in image_description:
        self._macro = {
            'macro directory': proprosed_macro_directory,
            'macro ifd info': self.tiff_info[proprosed_macro_directory],
            'strip offset': self.tiff_info[proprosed_macro_directory][273]['data_offset'],
            'strip byte counts': self.tiff_info[proprosed_macro_directory][279]['data_offset']
        }

    @property
    def label_IFD_offset_adjustment(self):
        """The offset of the label directory

        Returns:
            int: offset of IFD for the label
        """
        offset = self.directory_offsets[self._label['label directory']]
        return offset
    

    def _get_label_data(self):
        label_strip_offset = self._label['strip offset']
        label_byte_count = self._label['strip byte counts']

        with open(self.file_path, 'rb') as tiff:
            tiff.seek(label_strip_offset)
            label_data = tiff.read(label_byte_count)
        return label_data

    @property
    def label_data(self):
        """Label data in bytes. Does not include the IFD. Must be used
        before overwriting the label with de_identify_slide

        Returns:
            bytes: byte string containing the raw label information
        """
        return self._get_label_data()

    @property
    def label_info(self):
        """Information on the label BigTiff directory. Used in the LabelSaver
        under TiffWriter to save the label on SVS GT450 v1.0.0 slides that openslide
        cannot find.

        Returns:
            dict: label IFD info
        """
        return self._label

class SubImage():
    def __init__(self, file_type, label_params=None) -> None:
        """Creates a label or macro image to write into a whole slide image. Only
        works with Aperio whole slide images

        Args:
            file_type (str): Must be 'label' or 'macro'
            temp_dir (str): directory to store the saved label and macro images
            label_params (list, optional): Contains the text for the QR code and any desired
            sub text beneath the QR code. Supports ~ 3 lines of text. More may not fit on 
            the label. Defaults to None.

        Raises:
            ValueError: If file type is not 'label' or 'macro'
        """
        self.label_params = label_params

        if file_type not in ['label', 'macro']:
            raise ValueError(f'{file_type} must be label or macro')
        self.file_type = file_type
        self.file_name = None
        
        self._label_offset_adjustment = None
    
    def create_image(self):
        if self.file_type == 'label':
            img = self._create_label()

        else:
            img = self._create_macro()

        img = np.array(img)

        if self.file_type == 'label':
            btm = BigTiffMaker(img, 'label')
            img = btm.create_image()

        else:
            btm = BigTiffMaker(img, 'macro')
            img = btm.create_image()
        
        return img
    
    def _create_macro(self, img_dims=(1495, 606)):
        img = Image.new('RGB', img_dims, 'red')
        return img
        
    def _create_label(self, img_dims =(609, 567), font_size = 30):
        """Creates a label image with a QR code and text under the QR code

        Returns:
            img: label with image
        """
        

        try:
            myFont = ImageFont.truetype('arial.ttf', size=font_size) # Windows
        except OSError:
            try:
                myFont = ImageFont.truetype('Arial.ttf', size=font_size) # Mac
            except OSError:
                    print('FONT NOT FOUND ERROR')
                    sys.exit()

        qr_img = None
        qr_width = 0
        qr_height = 0
        if self.label_params: # qr code string
            qr_data = self.label_params[0]
            if qr_data is not None:
                qr_img = qrcode.make(qr_data)
                qr_width, qr_height = qr_img.size
                if qr_width < img_dims[0] or qr_height < img_dims[0]:
                    width, height = img_dims
                else:
                    img_dims = (int(qr_width *1.5), int(qr_height *1.5))


        img = Image.new('RGB', img_dims, 'white')
        ruo_text = 'RUO'
        img_draw = ImageDraw.Draw(img)
        img_draw.text((img_dims[0]-150, 10), text=ruo_text, font=myFont, fill=(0, 0, 0))

        if qr_img:
            img.paste(qr_img)

        if self.label_params:
            for line_num, text in enumerate(self.label_params[1:]):
                y_offset = qr_height + 20
                img_draw = ImageDraw.Draw(img)

                if text:
                    if not isinstance(text, str):
                        text = str(text)
                    
                    y_coord = y_offset + line_num * font_size
                    img_draw.text((28, y_coord), text, font=myFont, fill=(0, 0, 0))

        return img
        

    def update_ifd(self, file, offset_adjustment):
        """Updates the SVS file IFDs for the label and macro to correct the offsets.

        Args:
            file (BytesIO): BytesIO image object
            offset_adjustment (int): offset to adjust the IFD

        Returns:
            BytesIO: Label or macro image file with updated IFDs to be inserted into the SVS file
        """
        tiff_data = BigTiffFile(file)
        dir_offsets = tiff_data.next_dir_offsets

        for tag in tiff_data.tiff_info[1].keys():
            ifd_count = tiff_data.tiff_info[1][tag]['ifd_count']
            ifd_type = tiff_data.tiff_info[1][tag]['ifd_type']

            fmt = '<' + str(ifd_count) + FORMAT_CHARACTERS[ifd_type]
            length = struct.calcsize(fmt)
                
            if length > struct.calcsize('<Q') or tag == 273:
                pre_data_offset = tiff_data.tiff_info[1][tag]['pre_data_offset']
                data_offset = tiff_data.tiff_info[1][tag]['data_offset']

                new_offset = data_offset + offset_adjustment - 16                    

                updated_offset = struct.pack('<Q', new_offset)
                file.seek(pre_data_offset)
                file.write(updated_offset)

        # updates the next IFD of the label directory
        if self.file_type == 'label':
            end_of_ifd = dir_offsets[1]['pre_offset_offset']
            file.seek(0, os.SEEK_END)
            end_of_file = file.tell()
            new_next_ifd_offset = end_of_file + offset_adjustment
            new_next_ifd = struct.pack('<Q', new_next_ifd_offset)
            file.seek(end_of_ifd)
            file.write(new_next_ifd)
            self._label_offset_adjustment = new_next_ifd_offset
        
        return file

    @property
    def offset_adjustment(self):
        return self._label_offset_adjustment


class LabelSwitcher():
    def __init__(self, slide_path, remove_original_label_and_macro: bool=True, \
        qrcode:str=None, text_line1:str=None, text_line2:str=None, text_line3:str=None, text_line4:str=None) -> None:
        """WARNING: THIS UTILITY PERFORMS IN PLACE OPERATIONS ON SVS FILES. THE FILES ARE NOT COPIED!
        PLEASE MAKE COPIES PRIOR TO USE.

        Primary utility to switch the SVS label with a custom QR code and up to 3 lines of text.
        By default, the original label and macro images are overwritten with 0s. Because the slides are not
        copied, the process is fast.

        Caveats:
            1. Only tested on GT450 V1.0.0 and V1.0.1 SVS files
            2. Will corrupt files if unexpected data is present or process is terminated early
            3. Unknown performance if label or macro have been previously removed with another program

        Args:
            slide_path (str): full path to SVS file
            remove_original_label_and_macro (bool, optional): flag True to overwrite the original label and macro. Defaults to True.
            text_line1 (str, optional): line of text that appears on label. Defaults to None.
            text_line2 (str, optional): line of text that appears on label. Defaults to None.
            text_line3 (str, optional): line of text that appears on label. Defaults to None.
        """

        self.slide_path = slide_path
        label_params=[qrcode, text_line1, text_line2, text_line3, text_line4]
        self._slide_offset_adjustment = self._get_slide_offset(remove_original_label_and_macro)
        self._next_ifd_offset_adjustment, self._label_img = self._get_label_img(label_params)
        self._macro_img = self._get_macro_img()
    
    def switch_labels(self):
        with open(self.slide_path, 'rb+') as slide:
            
            slide.seek(self._slide_offset_adjustment)

            self._label_img.seek(16)
            label_data = self._label_img.read()
            slide.write(label_data)

            self._macro_img.seek(16)
            macro_data = self._macro_img.read()
            slide.seek(self._next_ifd_offset_adjustment)
            slide.write(macro_data)

    def _get_slide_offset(self, remove_label_and_macro):
        slide = BigTiffFile(self.slide_path)
        if remove_label_and_macro:
            slide.de_identify_slide()
        return slide.label_IFD_offset_adjustment

    def _get_label_img(self, label_params):
        img_creator = SubImage('label', label_params)
        label_image = img_creator.create_image()
        label_image = img_creator.update_ifd(label_image, self._slide_offset_adjustment)

        next_ifd_offset = img_creator.offset_adjustment
        return next_ifd_offset, label_image
    
    def _get_macro_img(self):
        img_creator = SubImage('macro')
        macro_image = img_creator.create_image()
        macro_image = img_creator.update_ifd(macro_image, self._next_ifd_offset_adjustment)
        return macro_image
    


class LabelReplacer(tk.Tk):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.file_path = None
        self.original_label = None
        self.new_label = None
        self.label_parameters = []

        self.title("Hatfield's (Semi)Proven SVS Slide Anonymizer")
        container = tk.Frame(self)

        container.grid_rowconfigure(0, weight = 1)
        container.grid_columnconfigure(0, weight = 1)

        self.parameter_frame = tk.Frame(self, relief=tk.RAISED, bd=2)

        self.help_text = tk.Label(master=self, text='Choose a slide file\nThis program will remove labels and macro images from SVS files.\nIt has only been tested on files created by Leica GT450s.\nThe process modifies the original file and is destructive and irreversible. Make sure you have backups.\nUse at your own risk.')
        self.help_text.grid(row=1, column=0)
        btn_open = tk.Button(text='Open Slide', command=self.open_slide)
        btn_open.grid(row=0, column=0, pady=5, padx=5)
    

    def open_slide(self):
        self.file_path = askopenfilename(filetypes=[('SVS Files', '*.svs')])
        if self.file_path is None or self.file_path == '':
            return
        if 'DigitalPathology' in self.file_path:
            messagebox.showerror('Error', message='This program will NOT run in the DigitalPathology folder. Please move files outside of this folder prior to processing.')
            return
        if self.original_label is not None:
            self.original_label.destroy()
        if self.new_label is not None:
            self.original_label.destroy()

        self.help_text.destroy()
        self._get_original_label()

        self.parameter_frame.grid(row=1, column=0)
        entry_parameters = self._fill_parameter_frame()
        tk.Label(self, text=self.file_path).grid(row=2, column=1)
        btn_generate = tk.Button(master=self.parameter_frame, text='Preview', command=lambda: self._get_new_label(entry_parameters))
        btn_generate.grid(row=5, column=1)

        btn_replace = tk.Button(master=self.parameter_frame, text='Replace',command=self._confirm_switch)
        btn_replace.grid(column=1, row=6)

    def _fill_parameter_frame(self):
        params = []
        tk.Label(master=self.parameter_frame, text='QR').grid(row=0, column=0)
        qr_entry = tk.Entry(self.parameter_frame)
        qr_entry.grid(row=0, column=1, sticky='ew', padx=5, pady=5)
        params.append(qr_entry)

        for i in range(1, 5):
            tk.Label(master=self.parameter_frame, text=f'Line {i}').grid(row=i, column=0)
            line_entry = tk.Entry(self.parameter_frame)
            line_entry.grid(row=i, column=1, sticky='ew', padx=5, pady=5)
            params.append(line_entry)
        
        return params
        
    def _confirm_switch(self):
        response = messagebox.askyesno('Confirm', message='This is an irreversible and potentially destructive process, continue?')
        if response:
            self._replace_label()
            self._get_original_label()

    def _get_original_label(self):
        label_img = BigTiffFile(self.file_path).get_label()
        x, y = label_img.size
        label_img = label_img.resize((x//2, y//2), resample=Image.Resampling.NEAREST)
        label_img = ImageTk.PhotoImage(label_img)
        self.original_label = tk.Label(self, image=label_img)
        self.original_label.image = label_img
        self.original_label.grid(row=1, column=1)
        tk.Label(self, text='Original Label').grid(row=0, column=1)

    def _get_new_label(self, entry_parameters, img_type:str='label'):
        if self.new_label is not None:
            self.new_label.destroy()
        
        self.label_parameters = []
        for entry in entry_parameters:
            if entry.get() == '':
                self.label_parameters.append(None)
            else:
                self.label_parameters.append(entry.get())

        if img_type == 'label':
            img = SubImage('label', self.label_parameters)._create_label()
        elif img_type == 'macro':
            img = SubImage('macro', self.label_parameters)._create_macro()
        else:
            raise ValueError
        x, y = img.size
        img = img.resize((x//2, y//2), resample=Image.Resampling.NEAREST)
        new_img = ImageTk.PhotoImage(img)
        self.new_label = tk.Label(image=new_img)
        self.new_label.image = new_img
        self.new_label.grid(row=1, column=3, padx=5, sticky='w')
        tk.Label(self, text='Proposed Label').grid(row=0, column=3)

    def _replace_label(self):
        if 'DigitalPathology' in self.file_path or 'digitalpathology' in self.file_path:
            exit()
        switcher = LabelSwitcher(
            slide_path=self.file_path,
            remove_original_label_and_macro=True,
            qrcode=self.label_parameters[0],
            text_line1=self.label_parameters[1],
            text_line2=self.label_parameters[2],
            text_line3=self.label_parameters[3],
            text_line4=self.label_parameters[4],
        )
        switcher.switch_labels()
        self.new_label.destroy()
        self.new_label = None


app = LabelReplacer()
app.mainloop()