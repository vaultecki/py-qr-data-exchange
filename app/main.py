# Copyright 2025 ecki
# SPDX-License-Identifier: Apache-2.0

import logging
import queue
import tkinter
from tkinter import filedialog, messagebox
from typing import List

from app import extra_windows
from app.controller import QrExchangeController

logger = logging.getLogger(__name__)
MAX_QR_CODE_BYTES = 2953


class GuiClass:
    def __init__(self):
        logger.debug("init gui")
        self.root = tkinter.Tk()
        self.root.title("PyQrDataExchange")
        self.root.geometry("480x150")

        self.controller = QrExchangeController(MAX_QR_CODE_BYTES)
        self.selected_paths: List[str] = []

        label = tkinter.Label(self.root, text=" ")
        label.grid(row=0, column=0, columnspan=4)

        self.label_password = tkinter.Label(self.root, text="Password:")
        self.label_password.grid(row=1, column=0, padx=5, pady=5, sticky=tkinter.E)

        self.password_var = tkinter.StringVar(self.root, "")
        self.entry_password = tkinter.Entry(
            self.root, width=21,
            show='*',
            textvariable=self.password_var
        )
        self.entry_password.grid(row=1, column=1, padx=5, pady=5, sticky="nw")

        self.label_filename = tkinter.Label(self.root, text="Files/Folder:")
        self.label_filename.grid(row=2, column=0, padx=5, pady=5, sticky=tkinter.E)

        self.entry_filename = tkinter.Entry(self.root, width=30, state="readonly")
        self.entry_filename.grid(row=2, column=1, padx=5, pady=5, sticky="nw")

        self.button_browse_files = tkinter.Button(
            self.root, text="Browse Files",
            command=self.click_button_browse_files
        )
        self.button_browse_files.grid(row=2, column=2)

        self.button_browse_folder = tkinter.Button(
            self.root, text="Browse Folder",
            command=self.click_button_browse_folder
        )
        self.button_browse_folder.grid(row=2, column=3)

        label2 = tkinter.Label(self.root, text=" ")
        label2.grid(row=3, column=0, columnspan=3)

        self.button_generate = tkinter.Button(
            self.root, text="Generate QR",
            command=self.click_button_generate
        )
        self.button_generate.grid(row=4, column=2)

        self.button_read_string = tkinter.Button(
            self.root, text="Read QR Code(s)",
            command=self.click_button_read_string
        )
        self.button_read_string.grid(row=4, column=0)

    def _validate_inputs(self, check_filename=True):
        if not self.password_var.get():
            messagebox.showerror("Error", "Please enter a password.")
            return False
        if check_filename and not self.selected_paths:
            messagebox.showerror("Error", "Please select file(s) or a folder.")
            return False
        return True

    def click_button_generate(self):
        if not self._validate_inputs():
            return

        password = self.password_var.get()

        self._disable_ui()

        # generate_qr_async's on_success/on_error run on its background worker
        # thread -- Tk/Tcl calls (including .after()) are not safe from there,
        # so only a thread-safe queue.Queue.put() happens in the callbacks, and
        # the actual UI update happens via polling from the main thread below.
        result_queue = queue.Queue()
        self.controller.generate_qr_async(
            self.selected_paths,
            password,
            on_success=lambda images, texts: result_queue.put(("success", (images, texts))),
            on_error=lambda error: result_queue.put(("error", error)),
        )
        self.root.after(100, self._poll_generate_result, result_queue)

    def _poll_generate_result(self, result_queue):
        """Runs safely on the main thread."""
        try:
            message_type, data = result_queue.get_nowait()
        except queue.Empty:
            self.root.after(100, self._poll_generate_result, result_queue)
            return

        self._enable_ui()

        if message_type == "success":
            qr_images, qr_texts = data
            logger.info(f"Generate success. {len(qr_images)} QR code(s)")
            try:
                extra_windows.QrWindow(self.root, qr_images, qr_texts)
            except Exception as e:
                logger.error(f"Error creating QrWindow: {e}")
                logger.exception("Full traceback:")
                messagebox.showerror("Error", f"Could not display QR window: {e}")
        else:
            logger.error(f"Generate error: {data}")
            messagebox.showerror("Error", str(data))

    def click_button_browse_files(self):
        filepaths = filedialog.askopenfilenames(filetypes=[("all files", "*.*")])
        if filepaths:
            self.selected_paths = list(filepaths)
            self._update_filename_display()

    def click_button_browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.selected_paths = [folder]
            self._update_filename_display()

    def _update_filename_display(self):
        if len(self.selected_paths) == 1:
            text = self.selected_paths[0]
        else:
            text = f"{len(self.selected_paths)} items selected"
        self.entry_filename.config(state="normal")
        self.entry_filename.delete(0, tkinter.END)
        self.entry_filename.insert(0, text)
        self.entry_filename.config(state="readonly")

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
