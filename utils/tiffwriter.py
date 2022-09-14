from .constants import FORMAT_CHARACTERS
import io
import numpy as np
from PIL import Image
import struct

TIFF_LABEL_IFD_TAG_VALUES = {
    254: {'type': 4, 'count': 1, 'value': (1,)},
    256: {'type': 3, 'count': 1, 'value': None}, #width
    257: {'type': 3, 'count': 1, 'value': None}, #height
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
        TIFF_LABEL_IFD_TAG_VALUES[258]['data'] = bits_per_sample
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
            fmt = '<' + str(values['count']) + FORMAT_CHARACTERS[values['type']]

            # If the size of the data is greater than 'L', the data is too large to fit in the IFD
            # and must be placed elsewhere
            if struct.calcsize(fmt) > struct.calcsize('L'):
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
                self.img.write(struct.pack('<L', *values['value']))
        
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
            self.tiff_template.popitem(270)
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

        extra_data_offset = num_entries * 20 + 16 + 16

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
                distance_to_move = struct.calcsize('Q')
                current_position = self.img.tell()
                self.img.write(struct.pack(fmt, *tag_info['value']))
                self.img.seek(current_position + distance_to_move)
        if self.label_or_macro == 'macro':
            self.img.write(struct.pack('<Q', 0))
        self.img.seek(self.tiff_template[273]['value'][0])
        self.img.write(self.img_data)
        self.img.seek(0)