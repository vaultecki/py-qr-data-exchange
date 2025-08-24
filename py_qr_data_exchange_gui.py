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
        self.root.geometry("900x300")
        self.root.minsize(width=900, height=300)
        #self.root.maxsize(width=1200, height=800)
        #self.root.resizable(width=False, height=False)

        label = tkinter.Label(self.root, text=" ")
        label.grid(row=0, column=0, columnspan=4)

        self.label_password = tkinter.Label(self.root, text="Password [1-20]:")
        self.label_password.grid(row=1, column=0, padx=5, pady=5, sticky=tkinter.E)

        self.password = tkinter.StringVar(self.root, '')
        reg = self.root.register(self.entry_password_validate)
        self.entry_password = tkinter.Entry(self.root, width=21, validate='key',
                                            validatecommand=(reg, '%P'),
                                            textvariable=self.password)
        self.entry_password.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="nw")

        self.label_filename = tkinter.Label(self.root, text="Filename:")
        self.label_filename.grid(row=2, column=0, padx=5, pady=5, sticky=tkinter.E)

        self.entry_filename = tkinter.Entry(self.root, width=30)
        self.entry_filename.grid(row=2, column=1, columnspan=2, padx=5, pady=5, sticky="nw")

        self.button_filemanager = tkinter.Button(self.root, text="Filemanager", command=self.click_button_filemanager)
        self.button_filemanager.grid(row=2, column=4)

        label2 = tkinter.Label(self.root, text=" ")
        label2.grid(row=3, column=0, columnspan=4)

        self.button_generate = tkinter.Button(self.root, text="Generate QR", command=self.click_button_generate)
        self.button_generate.grid(row=4, column=1)

        self.button_read = tkinter.Button(self.root, text="Read QR", command=self.click_button_read)
        self.button_read.grid(row=4, column=2)

    def run(self):
        self.root.mainloop()

    @staticmethod
    def entry_password_validate(password):
        max_length = 20
        if len(password) <= max_length:
            return True
        return False

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
