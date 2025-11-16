# Copyright [2025] [ecki]
# SPDX-License-Identifier: Apache-2.0

import logging
import math
import queue
import threading
import tkinter
import io
from tkinter import Toplevel, filedialog, messagebox, ttk
from typing import List, Union
from PIL import Image

from app import qr_data_class

logger = logging.getLogger(__name__)


class QrWindow(Toplevel):
    def __init__(self, master, qr_code_generated: Union[Image.Image, List[Image.Image]],
                 qr_code_text: Union[str, List[str]]):
        super().__init__(master)
        logger.info("open qr code display window")

        # Check if multi-part
        self.is_multipart = isinstance(qr_code_generated, list)

        if self.is_multipart:
            self.title(f"Generated QR Codes ({len(qr_code_generated)} parts)")
            self.qr_codes = qr_code_generated
            self.qr_texts = qr_code_text
            self._setup_multipart_ui()
        else:
            self.title("Generated QR Code")
            self.qr_codes = [qr_code_generated]
            self.qr_texts = [qr_code_text]
            self._setup_single_ui()

        self.transient(master)
        self.grab_set()

    def _setup_single_ui(self):
        """UI for single-part QR code."""
        tkinter.Label(self, text="QR code has been generated:").grid(row=0, column=0, padx=5, pady=5)
        var_qr_code_text = tkinter.StringVar(self, self.qr_texts[0])
        tkinter.Entry(self, width=60, textvariable=var_qr_code_text, state="readonly").grid(
            row=0, column=1, padx=5, pady=5
        )

        self._display_qr_image(self.qr_codes[0], row=1)

        self.button = tkinter.Button(master=self, text="Save As", command=self.save_single_file)
        self.button.grid(row=2, column=0, columnspan=2, padx=5, pady=5)

    def _setup_multipart_ui(self):
        """UI for multi-part QR codes."""
        # Info label
        info_text = f"File was split into {len(self.qr_codes)} QR codes"
        tkinter.Label(self, text=info_text, font=('Arial', 10, 'bold')).grid(
            row=0, column=0, columnspan=2, padx=5, pady=5
        )

        # Navigation
        nav_frame = tkinter.Frame(self)
        nav_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5)

        self.current_index = 0

        self.prev_button = tkinter.Button(nav_frame, text="◄ Previous",
                                          command=self.show_previous)
        self.prev_button.pack(side=tkinter.LEFT, padx=5)

        self.part_label = tkinter.Label(nav_frame, text=f"Part {self.current_index + 1}/{len(self.qr_codes)}")
        self.part_label.pack(side=tkinter.LEFT, padx=10)

        self.next_button = tkinter.Button(nav_frame, text="Next ►",
                                          command=self.show_next)
        self.next_button.pack(side=tkinter.LEFT, padx=5)

        # QR code display (container)
        self.qr_container = tkinter.Frame(self)
        self.qr_container.grid(row=2, column=0, columnspan=2, padx=5, pady=5)

        # Text display
        text_frame = tkinter.Frame(self)
        text_frame.grid(row=3, column=0, columnspan=2, padx=5, pady=5)

        tkinter.Label(text_frame, text="QR text:").pack(side=tkinter.LEFT)
        self.text_var = tkinter.StringVar(self, "")
        self.text_entry = tkinter.Entry(text_frame, width=50, textvariable=self.text_var,
                                        state="readonly")
        self.text_entry.pack(side=tkinter.LEFT, padx=5)

        # Buttons
        button_frame = tkinter.Frame(self)
        button_frame.grid(row=4, column=0, columnspan=2, padx=5, pady=10)

        tkinter.Button(button_frame, text="Save All",
                       command=self.save_all_files).pack(side=tkinter.LEFT, padx=5)
        tkinter.Button(button_frame, text="Save Current",
                       command=self.save_current_file).pack(side=tkinter.LEFT, padx=5)

        # Show first QR code
        self.show_qr(0)
        self.update_navigation()

    def show_qr(self, index: int):
        """Displays a specific QR code."""
        # Clear old content
        for widget in self.qr_container.winfo_children():
            widget.destroy()

        # Show new QR code
        self._display_qr_image(self.qr_codes[index], parent=self.qr_container, row=0)

        # Update text
        self.text_var.set(self.qr_texts[index][:50] + "..." if len(self.qr_texts[index]) > 50 else self.qr_texts[index])

    def show_previous(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.show_qr(self.current_index)
            self.update_navigation()

    def show_next(self):
        if self.current_index < len(self.qr_codes) - 1:
            self.current_index += 1
            self.show_qr(self.current_index)
            self.update_navigation()

    def update_navigation(self):
        """Updates navigation buttons."""
        self.prev_button.config(state="normal" if self.current_index > 0 else "disabled")
        self.next_button.config(state="normal" if self.current_index < len(self.qr_codes) - 1 else "disabled")
        self.part_label.config(text=f"Part {self.current_index + 1}/{len(self.qr_codes)}")

    def _display_qr_image(self, qr_image: Image.Image, row: int = 0, parent=None):
        """Displays a QR code image."""
        if parent is None:
            parent = self

        maxsize = math.floor((min(self.winfo_screenwidth(), self.winfo_screenheight())) * 0.6)
        resize_image = qr_image.resize((maxsize, maxsize))

        output = io.BytesIO()
        resize_image.save(output, format='PNG')

        photo = tkinter.PhotoImage(data=output.getvalue(), master=parent)
        label = tkinter.Label(master=parent, image=photo)
        label.image = photo  # Keep reference
        label.grid(row=row, column=0, columnspan=2, padx=5, pady=5)

    def save_single_file(self):
        """Saves a single QR code."""
        files = [("PNG files", "*.png"), ("SVG files", "*.svg")]
        file_out = filedialog.asksaveasfilename(filetypes=files, defaultextension=".png")
        if file_out:
            self.qr_codes[0].save(file_out)
            messagebox.showinfo("Success", f"QR code saved: {file_out}")

    def save_current_file(self):
        """Saves the currently displayed QR code."""
        files = [("PNG files", "*.png"), ("SVG files", "*.svg")]
        default_name = f"qr_part_{self.current_index + 1}_of_{len(self.qr_codes)}.png"
        file_out = filedialog.asksaveasfilename(
            filetypes=files,
            defaultextension=".png",
            initialfile=default_name
        )
        if file_out:
            self.qr_codes[self.current_index].save(file_out)
            messagebox.showinfo("Success", f"QR code saved: {file_out}")

    def save_all_files(self):
        """Saves all QR codes to a directory."""
        directory = filedialog.askdirectory(title="Select folder for QR codes")
        if directory:
            import os
            for i, qr_image in enumerate(self.qr_codes, 1):
                filename = f"qr_part_{i}_of_{len(self.qr_codes)}.png"
                filepath = os.path.join(directory, filename)
                qr_image.save(filepath)

            messagebox.showinfo("Success",
                                f"{len(self.qr_codes)} QR codes saved to:\n{directory}")


class ReadWindow(Toplevel):
    def __init__(self, master, password, qr_text=""):
        super().__init__(master)
        logger.info("open qr read window")
        self.password = password
        self.qr_texts = []  # List for multi-part QR codes

        self.title("QR Data Read")

        # Text input
        tkinter.Label(self, text="Text to convert:").grid(row=0, column=0, padx=5, pady=5)
        if qr_text:
            text = tkinter.StringVar(self, qr_text)
            self.text_field = tkinter.Entry(self, textvariable=text, width=60, state="readonly")
            self.qr_texts = [qr_text]
        else:
            self.text_field = tkinter.Entry(self, width=60)
        self.text_field.grid(row=0, column=1, padx=5, pady=5)

        # Multi-part section
        multipart_frame = tkinter.LabelFrame(self, text="Multi-Part QR Codes", padx=5, pady=5)
        multipart_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

        tkinter.Button(multipart_frame, text="Add QR Code Image",
                       command=self.add_qr_image).pack(side=tkinter.LEFT, padx=5)

        self.multipart_label = tkinter.Label(multipart_frame, text="0 QR codes loaded")
        self.multipart_label.pack(side=tkinter.LEFT, padx=10)

        tkinter.Button(multipart_frame, text="Clear List",
                       command=self.clear_qr_list).pack(side=tkinter.LEFT, padx=5)

        # Decrypt button
        self.button = tkinter.Button(self, text="Decrypt and Save as", command=self.on_click_decrypt)
        self.button.grid(row=2, column=1, padx=5, pady=5)

        self.result_queue = queue.Queue()

        self.transient(master)
        self.grab_set()

    def add_qr_image(self):
        """Adds a QR code image to the list."""
        filetypes = [("Image files", "*.png *.jpg *.jpeg"), ("All files", "*.*")]
        filepath = filedialog.askopenfilename(filetypes=filetypes)

        if filepath:
            try:
                from app import service
                qr_text = service.read_qr_from_image(filepath)
                self.qr_texts.append(qr_text)

                # Check if multi-part
                from app.controller import QrExchangeController
                if QrExchangeController.is_multipart_qr(qr_text):
                    part_num, total = QrExchangeController.get_multipart_info(qr_text)
                    info = f"Part {part_num}/{total}"
                else:
                    info = "Single-part"

                self.multipart_label.config(
                    text=f"{len(self.qr_texts)} QR codes loaded (last: {info})"
                )
                logger.info(f"QR code added: {info}")

            except Exception as e:
                messagebox.showerror("Error", f"Could not read QR code:\n{e}")

    def clear_qr_list(self):
        """Clears the list of QR codes."""
        self.qr_texts = []
        self.multipart_label.config(text="0 QR codes loaded")
        logger.info("QR code list cleared")

    def on_click_decrypt(self):
        logger.debug("button pressed")
        self.button.config(state="disabled")
        self.config(cursor="watch")

        # Use either text input or loaded QR codes
        if self.qr_texts:
            input_data = self.qr_texts
        else:
            input_str = self.text_field.get()
            if not input_str:
                messagebox.showerror("Error", "Please enter text or load QR codes")
                self.button.config(state="normal")
                self.config(cursor="")
                return
            input_data = input_str

        threading.Thread(
            target=self.on_click_decrypt_thread_worker,
            args=(input_data, self.password, self.result_queue),
            daemon=True
        ).start()
        self.after(250, self.process_queue)

    def on_click_decrypt_thread_worker(self, input_data, password, q):
        try:
            logger.debug("start decryption, decompressing")
            from app.controller import QrExchangeController
            qr_data = QrExchangeController.decrypt_qr_data(
                qr_texts=input_data,
                password=password
            )
            logger.debug("ended decryption, decompressing")
            q.put(("success", qr_data))
        except qr_data_class.DecryptionError as e:
            logger.error(f"cannot decrypt string: {e}")
            q.put(("error", e))
        except Exception as e:
            logger.error(f"unexpected error: {e}")
            q.put(("error", e))

    def process_queue(self):
        """This function runs safely in the main thread."""
        try:
            logger.debug("Checking if something is in the queue (non-blocking)")
            message_type, data = self.result_queue.get_nowait()
            if message_type == "success":
                files = [("all files", "*.*")]
                logger.debug("open file dialog")
                file_out = filedialog.asksaveasfilename(filetypes=files)
                if file_out:
                    with open(file_out, "wb+") as f_out:
                        f_out.write(data)
                    messagebox.showinfo("Success", f"File saved: {file_out}")
            elif message_type == "error":
                logger.debug("Now the error message can be displayed safely")
                if isinstance(data, qr_data_class.DecryptionError):
                    messagebox.showerror("Error", f"Cannot decrypt: {str(data)}")
                else:
                    messagebox.showerror("Unexpected Error", f"An error occurred: {data}")

            self.button.config(state="normal")
            self.config(cursor="")
        except queue.Empty:
            # If queue is empty, check again in 250ms
            self.after(250, self.process_queue)


if __name__ == "__main__":
    logger.info("main of extra_window.py")
