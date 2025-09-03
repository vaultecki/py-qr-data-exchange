import cv2
import logging
import qrcode
import tkinter
from tkinter import filedialog, messagebox

import qr_data_class
from extra_windows import QrWindow, ReadWindow


logger = logging.getLogger(__name__)
MAX_QR_CODE_BYTES = 2953


class GuiClass:
    def __init__(self):
        logger.debug("init the gui for py qr data exchange")
        self.root = tkinter.Tk()
        self.root.title("PyQrDataExchange")
        self.root.geometry("400x150")
        # to play around with display geometry
        # self.root.minsize(width=400, height=250)
        # self.root.maxsize(width=1200, height=800)
        # self.root.resizable(width=False, height=False)

        label = tkinter.Label(self.root, text=" ")
        label.grid(row=0, column=0, columnspan=4)

        self.label_password = tkinter.Label(self.root, text="Password [1-20]:")
        self.label_password.grid(row=1, column=0, padx=5, pady=5, sticky=tkinter.E)

        self.password = tkinter.StringVar(self.root, '')
        reg = self.root.register(self.entry_password_validate)
        self.entry_password = tkinter.Entry(self.root, width=21, validate='key',
                                            validatecommand=(reg, '%P'),
                                            textvariable=self.password)
        self.entry_password.grid(row=1, column=1, padx=5, pady=5, sticky="nw")

        self.label_filename = tkinter.Label(self.root, text="Filename:")
        self.label_filename.grid(row=2, column=0, padx=5, pady=5, sticky=tkinter.E)

        self.entry_filename = tkinter.Entry(self.root, width=30)
        self.entry_filename.grid(row=2, column=1, padx=5, pady=5, sticky="nw")

        self.button_filemanager = tkinter.Button(self.root, text="Filemanager", command=self.click_button_filemanager)
        self.button_filemanager.grid(row=2, column=2)

        label2 = tkinter.Label(self.root, text=" ")
        label2.grid(row=3, column=0, columnspan=3)

        self.button_generate = tkinter.Button(self.root, text="Generate QR", command=self.click_button_generate)
        self.button_generate.grid(row=4, column=2)

        self.button_read = tkinter.Button(self.root, text="Read QR", command=self.click_button_read_qr)
        self.button_read.grid(row=4, column=0)

        self.button_read = tkinter.Button(self.root, text="Read String", command=self.click_button_read_string)
        self.button_read.grid(row=4, column=1)

    def run(self):
        self.root.mainloop()

    @staticmethod
    def entry_password_validate(password):
        max_length = 20
        if len(password) <= max_length:
            return True
        return False

    def _validate_inputs(self, check_filename=True):
        """Überprüft, ob ein Passwort und optional ein Dateiname eingegeben wurden."""
        if not self.password.get():
            logger.error("no password found")
            messagebox.showerror("Fehler", "Bitte gib ein Passwort ein.")
            return False
        if check_filename and not self.entry_filename.get():
            logger.error("no filename found")
            messagebox.showerror("Fehler", "Bitte wähle eine Datei aus.")
            return False
        return True

    def click_button_generate(self):
        if not self._validate_inputs(check_filename=True):
            return
        logger.debug(f"read file {self.entry_filename.get()}")
        try:
            with (open(self.entry_filename.get(), "rb")) as f_in:
                raw_data = f_in.read()
                logger.debug(f"raw file size: {len(raw_data)} Bytes")
                logger.debug("generate qr code")
                qr_data = qr_data_class.QrData(raw_data)
                data_for_img = qr_data.serialize(password=self.entry_password.get())
                logger.debug(f"size of data for qr code: {len(data_for_img)} Byte")
                if len(data_for_img) >= MAX_QR_CODE_BYTES:
                    logger.error(f"max size {MAX_QR_CODE_BYTES} for qr code surpassed")
                    messagebox.showerror("Fehler", f"Die Datei ist mit {len(data_for_img)} Bytes ist zu groß. Maximum: {MAX_QR_CODE_BYTES} Bytes.")
                    return
                qr_code_generated = qrcode.make(data_for_img, error_correction=1)
                logger.debug("open qr code window")
                QrWindow(self.root, qr_code_generated, data_for_img)
        except FileNotFoundError:
            logger.error(f"file {self.entry_filename.get()} not found")
            messagebox.showerror("Fehler", f"file {self.entry_filename.get()} not found")
        return

    def click_button_filemanager(self):
        logger.debug("open filemanager to chode file")
        files = [("all files", "*.*"), ("PNG files", "*.png"), ("SVG files", "*.svg")]
        file_path = filedialog.askopenfilename(filetypes = files)
        if file_path:
            self.entry_filename.delete(0, tkinter.END)
            self.entry_filename.insert(0, str(file_path))

    def click_button_read_qr(self):
        if not self._validate_inputs(check_filename=True):
            return
        logger.debug(f"read file {self.entry_filename.get()}")
        try:
            image = cv2.imread(self.entry_filename.get())
            logger.debug("initialize the cv2 QRCode detector")
            detector = cv2.QRCodeDetector()
            logger.debug("cv2 - detect and decode")
            input_str, vertices_array, binary_qrcode = detector.detectAndDecode(image)
        except cv2.error:
            logger.error(f"opencv can not read image {self.entry_filename.get()}")
            messagebox.showerror("Fehler", f"opencv can not open image {self.entry_filename.get()}")
            return
        if vertices_array is None:
            logger.error("no data found in qr code")
            messagebox.showerror("Fehler", "no data found in qr code")
            return
        logger.debug(f"open read window with qr text sting {input_str}")
        ReadWindow(self.root, self.entry_password.get(), input_str)
        return

    def click_button_read_string(self):
        if not self._validate_inputs(check_filename=False):
            return
        logger.debug(f"open read window without qr text sting")
        ReadWindow(self.root, self.entry_password.get())
        return


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logger.info("start py-qr-data-exchange")
    py_qr_data_gui = GuiClass()
    py_qr_data_gui.run()
