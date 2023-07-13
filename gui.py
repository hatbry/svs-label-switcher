import tkinter as tk
from tkinter.filedialog import askopenfilename
import time

import sys
import os

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from PIL import Image, ImageTk
from label_switcher import SubImage, BigTiffFile

def get_file_path():
    fp = entry.get()

def open_slide_file():
    filepath = askopenfilename(
        filetypes=[('SVS Files', '*.svs')]
    )
    label_img = BigTiffFile(filepath).get_label()
    if filepath is None:
        return
    fp_text = tk.Label(text=filepath)
    fp_text.grid(row=0, column=0)
    
    label_img = ImageTk.PhotoImage(label_img)
    label = tk.Label(image=label_img)
    label.image = label_img
    label.grid(row=1, column=1)


def configure_custom_image(img_type: str='label', data: list=None):
    data = [
        qr_entry.get(),
        line1_entry.get(),
        line2_entry.get(),
        line3_entry.get(),
        line4_entry.get(),
    ]
    if img_type == 'label':
        img = SubImage('label', data)._create_label()
    elif img_type == 'macro':
        img = SubImage('macro', data)._create_macro()
    else:
        raise ValueError
    new_img = ImageTk.PhotoImage(img)
    new_label = tk.Label(image=new_img)
    new_label.image = new_img
    new_label.grid(row=1, column=2)



window = tk.Tk()
window.title('SVS Label Remover - Research Use Only')
window.columnconfigure([0, 1, 2], weight=1, minsize=75)
window.rowconfigure([0, 1, 2], weight=1, minsize=75)





#new_slide_label = SubImage('label')._create_label()
##new_macro_image = SubImage('macro')._create_macro()
#new_slide_label = ImageTk.PhotoImage(new_slide_label)
#new_macro_image = ImageTk.PhotoImage(new_macro_image)


#new_label = tk.Label(image=new_slide_label)



#btn_submit = tk.Button(text='Submit', command=get_file_path)


#new_label.grid(row=2, column=2)

frm_entry = tk.Frame(window, relief=tk.RAISED, bd=2)
qr_entry = tk.Entry(frm_entry)
line1_entry = tk.Entry(frm_entry)
line2_entry = tk.Entry(frm_entry)
line3_entry = tk.Entry(frm_entry)
line4_entry = tk.Entry(frm_entry)

qr_lbl = tk.Label(master=frm_entry, text='QR')
line1_lbl = tk.Label(master=frm_entry, text='Line 1')
line2_lbl = tk.Label(master=frm_entry, text='Line 2')
line3_lbl = tk.Label(master=frm_entry, text='Line 3')
line4_lbl = tk.Label(master=frm_entry, text='Line 4')

qr_entry.grid(row=0, column=1, sticky='ew', padx=5, pady=5)
line1_entry.grid(row=1, column=1, sticky='ew', padx=5, pady=5)
line2_entry.grid(row=2, column=1, sticky='ew', padx=5, pady=5)
line3_entry.grid(row=3, column=1, sticky='ew', padx=5, pady=5)
line4_entry.grid(row=4, column=1, sticky='ew', padx=5, pady=5)

qr_lbl.grid(row=0, column=0)
line1_lbl.grid(row=1, column=0)
line2_lbl.grid(row=2, column=0)
line3_lbl.grid(row=3, column=0)
line4_lbl.grid(row=4, column=0, pady=5)


btn_open = tk.Button(text='Open', command=open_slide_file)
btn_generate = tk.Button(text='Generate Label', command=configure_custom_image)
#entry.grid(row=1, column=0)

#btn_submit.grid(row=2, column=0)
frm_entry.grid(row=1, column=0, sticky='ns')

btn_open.grid(row=0, column=0)
btn_generate.grid(row=2, column=0)


window.mainloop()