import cv2
import qrcode
#from PIL import Image, ImageTk
import tkinter
from tkinter import filedialog

import qr_data_class


class GuiClass:
    def __init__(self):
        self.root = tkinter.Tk()
        self.root.title("PyQrDataExchange")
        self.root.geometry("800x400")
        self.root.minsize(width=400, height=400)
        #self.root.maxsize(width=1200, height=800)
        #self.root.resizable(width=False, height=False)

        self.label_password = tkinter.Label(self.root, text="Password [0-20 Zeichen]:")
        self.label_password.pack()

        self.entry_password = tkinter.Entry(self.root, width=21)
        self.entry_password.pack()

        self.label_filename = tkinter.Label(self.root, text="Filename")
        self.label_filename.pack()

        self.entry_filename = tkinter.Entry(self.root, width=40)
        self.entry_filename.pack()

        self.button_filemanager = tkinter.Button(self.root, text="Filemanager", command=self.click_button_filemanager)
        self.button_filemanager.pack()

        self.button_generate = tkinter.Button(self.root, text="Generate QR", command=self.click_button_generate)
        self.button_generate.pack()

        self.button_read = tkinter.Button(self.root, text="Read QR", command=self.click_button_read)
        self.button_read.pack()

    def run(self):
        self.root.mainloop()

    def click_button_generate(self):
        if not self.entry_password.get():
            print("no password")
            return
        if not self.entry_filename.get():
            print("filename")
            return
        with (open(self.entry_filename.get(), "rb")) as f_in:
            raw_data = f_in.read()
            qr_data = qr_data_class.QrData(raw_data)
            data_for_img = qr_data.get_string(password=self.entry_password.get())
            print(data_for_img)
            qr_code_generated = qrcode.make(data_for_img, error_correction=1)
            file_out = filedialog.asksaveasfilename()
            qr_code_generated.save("{}".format(file_out))
            return

    def click_button_filemanager(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            self.entry_filename.insert(0, str(file_path))

    def click_button_read(self):
        if not self.entry_password.get():
            print("no password")
            return
        if not self.entry_filename.get():
            print("filename")
            return
        image = cv2.imread(self.entry_filename.get())
        # initialize the cv2 QRCode detector
        detector = cv2.QRCodeDetector()
        # detect and decode
        input_str, vertices_array, binary_qrcode = detector.detectAndDecode(image)
        if vertices_array is None:
            #logger.error("There was some error")
            return
        print(input_str)
        qr_data = qr_data_class.QrData()
        qr_data.set_string(input_str, password=self.entry_password.get())
        print(qr_data.get_data())
        file_out = filedialog.asksaveasfilename()
        if file_out:
            with (open(file_out, "wb+")) as f_out:
                f_out.write(qr_data.get_data())


if __name__ == "__main__":
    print("moin")
    # tkinter._test()
    test = GuiClass()
    test.run()
