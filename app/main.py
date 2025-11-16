# Copyright [2025] [ecki]
# SPDX-License-Identifier: Apache-2.0

import logging
import tkinter
from tkinter import filedialog, messagebox

from app.controller import QrExchangeController
from app import extra_windows

logger = logging.getLogger(__name__)
MAX_QR_CODE_BYTES = 2953


class GuiClass:
    def __init__(self):
        logger.debug("init gui")
        self.root = tkinter.Tk()
        self.root.title("PyQrDataExchange")
        self.root.geometry("400x150")

        self.controller = QrExchangeController(MAX_QR_CODE_BYTES)

        label = tkinter.Label(self.root, text=" ")
        label.grid(row=0, column=0, columnspan=4)

        self.label_password = tkinter.Label(self.root, text="Password [1-20]:")
        self.label_password.grid(row=1, column=0, padx=5, pady=5, sticky=tkinter.E)

        self.password_var = tkinter.StringVar(self.root, "")
        reg = self.root.register(self.entry_password_validate)
        self.entry_password = tkinter.Entry(
            self.root, width=21, validate="key",
            validatecommand=(reg, '%P'),
            show='*',
            textvariable=self.password_var
        )
        self.entry_password.grid(row=1, column=1, padx=5, pady=5, sticky="nw")

        self.label_filename = tkinter.Label(self.root, text="Filename:")
        self.label_filename.grid(row=2, column=0, padx=5, pady=5, sticky=tkinter.E)

        self.entry_filename = tkinter.Entry(self.root, width=30)
        self.entry_filename.grid(row=2, column=1, padx=5, pady=5, sticky="nw")

        self.button_filemanager = tkinter.Button(
            self.root, text="Browse",
            command=self.click_button_filemanager
        )
        self.button_filemanager.grid(row=2, column=2)

        label2 = tkinter.Label(self.root, text=" ")
        label2.grid(row=3, column=0, columnspan=3)

        self.button_generate = tkinter.Button(
            self.root, text="Generate QR",
            command=self.click_button_generate
        )
        self.button_generate.grid(row=4, column=2)

        self.button_read = tkinter.Button(
            self.root, text="Read QR",
            command=self.click_button_read_qr
        )
        self.button_read.grid(row=4, column=0)

        self.button_read = tkinter.Button(
            self.root, text="Read String",
            command=self.click_button_read_string
        )
        self.button_read.grid(row=4, column=1)

    @staticmethod
    def entry_password_validate(password):
        return len(password) <= 20

    def _validate_inputs(self, check_filename=True):
        if not self.password_var.get():
            messagebox.showerror("Error", "Please enter a password.")
            return False
        if check_filename and not self.entry_filename.get():
            messagebox.showerror("Error", "Please select a file.")
            return False
        return True

    def click_button_generate(self):
        if not self._validate_inputs():
            return

        filepath = self.entry_filename.get()
        password = self.password_var.get()

        self._disable_ui()

        self.controller.generate_qr_async(
            filepath,
            password,
            on_success=self._on_generate_success,
            on_error=self._on_generate_error,
        )

    def _on_generate_success(self, qr_image, qr_text):
        self._enable_ui()
        extra_windows.QrWindow(self.root, qr_image, qr_text)

    def _on_generate_error(self, error: Exception):
        self._enable_ui()
        messagebox.showerror("Error", str(error))

    def click_button_filemanager(self):
        filetypes = [("all files", "*.*"), ("PNG files", "*.png")]
        fp = filedialog.askopenfilename(filetypes=filetypes)
        if fp:
            self.entry_filename.delete(0, tkinter.END)
            self.entry_filename.insert(0, fp)

    def click_button_read_qr(self):
        if not self._validate_inputs(check_filename=True):
            return

        filepath = self.entry_filename.get()
        password = self.password_var.get()

        self.controller.read_qr_from_image_async(
            filepath,
            on_success=lambda text: extra_windows.ReadWindow(self.root, password, text),
            on_error=lambda err: messagebox.showerror("Error", str(err))
        )

    def click_button_read_string(self):
        if not self._validate_inputs(check_filename=False):
            return
        extra_windows.ReadWindow(self.root, self.password_var.get())

    def _disable_ui(self):
        self.button_generate.config(state="disabled")
        self.root.config(cursor="watch")

    def _enable_ui(self):
        self.button_generate.config(state="normal")
        self.root.config(cursor="")

    def run(self):
        self.root.mainloop()


def run_app():
    logging.info("start py-qr-data-exchange")
    GuiClass().run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    run_app()
