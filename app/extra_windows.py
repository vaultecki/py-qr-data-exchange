# Copyright [2025] [ecki]
# SPDX-License-Identifier: Apache-2.0

import logging
import math
import queue
import threading
import tkinter
import io
from tkinter import Toplevel, filedialog, messagebox
from typing import List
from PIL import Image

from app import qr_multi_part

logger = logging.getLogger(__name__)


class QrWindow(Toplevel):
    def __init__(self, master, qr_codes: List[Image.Image], qr_texts: List[str]):
        super().__init__(master)
        logger.info("open qr code display window")

        self.qr_codes = qr_codes
        self.qr_texts = qr_texts

        suffix = "s" if len(qr_codes) > 1 else ""
        self.title(f"Generated QR Code{suffix} ({len(qr_codes)} part{suffix})")
        logger.info(f"Setting up QR display UI with {len(qr_codes)} part(s)")
        self._setup_ui()

        self.transient(master)
        self.grab_set()

    def _setup_ui(self):
        """UI for the generated QR code(s), with navigation (works for 1 part too)."""
        info_text = f"{len(self.qr_codes)} QR code(s) generated"
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
            for i, qr_string in enumerate(self.qr_texts, 1):
                filename = f"qr_part_{i}_of_{len(self.qr_codes)}.txt"
                filepath = os.path.join(directory, filename)
                with open(filepath, "w") as text_file:
                    text_file.write(qr_string)
                    text_file.close()

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

        tkinter.Button(multipart_frame, text="Add QR Code Image(s)",
                       command=self.add_qr_image).pack(side=tkinter.LEFT, padx=5)

        self.multipart_label = tkinter.Label(multipart_frame, text="0 QR codes loaded")
        self.multipart_label.pack(side=tkinter.LEFT, padx=10)

        tkinter.Button(multipart_frame, text="Clear List",
                       command=self.clear_qr_list).pack(side=tkinter.LEFT, padx=5)

        # Decrypt button
        self.button = tkinter.Button(self, text="Decrypt and Extract to Folder", command=self.on_click_decrypt)
        self.button.grid(row=2, column=1, padx=5, pady=5)

        self.result_queue = queue.Queue()

        self.transient(master)
        self.grab_set()

    def add_qr_image(self):
        """Adds one or multiple QR code images to the list."""
        filetypes = [("Image files", "*.png *.jpg *.jpeg"), ("All files", "*.*")]
        filepaths = filedialog.askopenfilenames(filetypes=filetypes)

        if not filepaths:
            return

        # Show progress for multiple files
        total_files = len(filepaths)
        if total_files > 1:
            self.config(cursor="watch")
            self.multipart_label.config(text=f"Loading {total_files} files...")
            self.update()

        loaded_count = 0
        errors = []

        for idx, filepath in enumerate(filepaths, 1):
            try:
                from app import service
                logger.info(f"Reading QR code {idx}/{total_files}: {filepath}")
                qr_text = service.read_qr_from_image(filepath)

                if not service.is_valid_qr_part(qr_text):
                    raise ValueError("Not a recognized QR code format for this application")

                self.qr_texts.append(qr_text)
                loaded_count += 1
                logger.info(f"QR code {idx}/{total_files} added")

                # Update progress for multiple files
                if total_files > 1:
                    self.multipart_label.config(
                        text=f"Loading {idx}/{total_files}... ({loaded_count} successful)"
                    )
                    self.update()

            except Exception as e:
                error_msg = f"{filepath}: {str(e)}"
                errors.append(error_msg)
                logger.error(f"Could not read QR code from {filepath}: {e}")

        # Reset cursor
        if total_files > 1:
            self.config(cursor="")

        # Update final status
        if loaded_count > 0:
            self.multipart_label.config(text=f"{len(self.qr_texts)} QR codes loaded")

        # Show errors if any
        if errors:
            error_summary = f"Successfully loaded {loaded_count}/{total_files} files.\n\nErrors:\n"
            error_summary += "\n".join(errors[:5])  # Show max 5 errors
            if len(errors) > 5:
                error_summary += f"\n... and {len(errors) - 5} more errors"
            messagebox.showwarning("Some files could not be read", error_summary)
        elif loaded_count > 1:
            messagebox.showinfo("Success", f"Successfully loaded {loaded_count} QR codes!")
        elif loaded_count == 0:
            messagebox.showerror("Error", "Could not read any QR codes from the selected files.")

    def clear_qr_list(self):
        """Clears the list of QR codes."""
        self.qr_texts = []
        self.multipart_label.config(text="0 QR codes loaded")
        logger.info("QR code list cleared")

    def on_click_decrypt(self):
        logger.debug("button pressed")

        # Use either loaded QR codes or text input
        if self.qr_texts:
            input_data = self.qr_texts
        else:
            input_str = self.text_field.get()
            if not input_str:
                messagebox.showerror("Error", "Please enter text or load QR codes")
                return

            if len(input_str) > 2953 and "==" in input_str:
                logger.debug("probably multipart string")
                input_array = input_str.lstrip().rstrip().split("==")
                self.qr_texts = [part.lstrip().rstrip() + "==" for part in input_array]
                input_data = self.qr_texts
            else:
                input_data = [input_str]

        output_dir = filedialog.askdirectory(title="Select output folder")
        if not output_dir:
            return

        self.button.config(state="disabled")
        self.config(cursor="watch")

        threading.Thread(
            target=self.on_click_decrypt_thread_worker,
            args=(input_data, self.password, output_dir, self.result_queue),
            daemon=True
        ).start()
        self.after(250, self.process_queue)

    def on_click_decrypt_thread_worker(self, input_data, password, output_dir, q):
        try:
            logger.debug("start decryption, decompressing, extracting")
            from app.controller import QrExchangeController
            extracted = QrExchangeController.decrypt_qr_data(
                qr_texts=input_data,
                password=password,
                output_dir=output_dir
            )
            logger.debug(f"decryption/extraction done. {len(extracted)} file(s)")
            q.put(("success", (extracted, output_dir)))
        except qr_multi_part.DecryptionError as e:
            logger.error(f"cannot decrypt: {e}")
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
                extracted, output_dir = data

                preview = "\n".join(str(p) for p in extracted[:10])
                if len(extracted) > 10:
                    preview += f"\n... and {len(extracted) - 10} more"

                messagebox.showinfo(
                    "Success",
                    f"{len(extracted)} file(s) extracted to:\n{output_dir}\n\n{preview}"
                )
            elif message_type == "error":
                logger.debug("Now the error message can be displayed safely")
                if isinstance(data, qr_multi_part.DecryptionError):
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
