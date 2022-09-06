# svs-label-switcher
Utility to remove the label and macro images from whole-slide SVS images. The label can include custom QR codes and 3 lines of text around 25 characters each. Additionally, the original label and macro are overwritten with zeroes prior to new image creation. 

## Warning
All operations are performed on the file "in place". This makes the process extremely fast, but also destructive and irreversible. Make sure that you have copies in place prior to running this.

## Command Line Utility
Batch label switching using a csv or xlsx file
``` shell 
python label_switcher.py multiple -mf csv_file_with_filenames.csv -hd "File Names"
```

Single file switching
```shell
python label_switcher.py single -sf path/to/slide.svs -qr "study no 12141" -l1 "subject a121" -l2 "stomach" l3 "resection"
```
## Simple Label Removal
```python
btf = BigTiffFile("path/to/file.svs")
btf.de_identify_slide()
```

## Simple Label Saver
Note: Must be run before removing the label

```python
btf = BigTiffFile('path/to/file.svs')
btf.save_label('my_label.jpg')
```

## Switch Label
```python
switcher = LabelSwitcher('path/to/slide', qrcode='custom text', text_line1='sample text 1', text_line2='sample text 2', text_line3='sample text 3')
switcher.switch_labels()
```
## Pre-requisites
Tested using: Python (3.10.4), qrcode (7.3.1), numpy (1.22.3), pandas (1.4.2), and Pillow (9.1.0) 