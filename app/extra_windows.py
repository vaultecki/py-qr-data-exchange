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
from app import service
from app.controller import QrExchangeController

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
    def __init__(self, master, password):
        super().__init__(master)
        logger.info("open qr read window")
        self.password = password
        self.parts_by_number = {}  # part_number -> qr_text, for parts confirmed to belong to this transfer
        self.total_parts = None  # only known once at least one part decrypts successfully

        self.title("QR Data Read")

        # Text input
        tkinter.Label(self, text="Text to add:").grid(row=0, column=0, padx=5, pady=5)
        self.text_field = tkinter.Entry(self, width=60)
        self.text_field.grid(row=0, column=1, padx=5, pady=5)
        self.add_text_button = tkinter.Button(self, text="Add", command=self.click_add_text)
        self.add_text_button.grid(row=0, column=2, padx=5, pady=5)

        # Multi-part section
        multipart_frame = tkinter.LabelFrame(self, text="Loaded Parts", padx=5, pady=5)
        multipart_frame.grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky="ew")

        self.add_files_button = tkinter.Button(multipart_frame, text="Add QR Code File(s)",
                                               command=self.add_qr_image)
        self.add_files_button.pack(side=tkinter.LEFT, padx=5)

        self.status_label = tkinter.Label(multipart_frame, text="0 parts loaded")
        self.status_label.pack(side=tkinter.LEFT, padx=10)

        self.clear_button = tkinter.Button(multipart_frame, text="Clear List",
                                           command=self.clear_qr_list)
        self.clear_button.pack(side=tkinter.LEFT, padx=5)

        # Decrypt button -- stays disabled until every part of the transfer is loaded
        self.decrypt_button = tkinter.Button(
            self, text="Decrypt and Extract to Folder", command=self.on_click_decrypt, state="disabled"
        )
        self.decrypt_button.grid(row=2, column=2, padx=5, pady=5)

        self.decrypt_result_queue = queue.Queue()
        self.text_add_queue = queue.Queue()
        self.file_add_queue = queue.Queue()

        self.transient(master)
        self.grab_set()

    def _try_add_part(self, qr_text: str) -> str:
        """
        Attempts to decrypt and record a single QR part. Runs the (comparatively
        expensive, full-Argon2i) decryption, so call this off the main thread.

        Returns an empty string on success (including a harmless re-add of an
        already-loaded part), or an error message describing why the part was
        rejected.
        """
        qr_text = qr_text.strip()
        if not qr_text:
            return "Empty text"

        try:
            part_number, total_parts = QrExchangeController.get_part_info(qr_text, self.password)
        except qr_multi_part.DecryptionError as e:
            return f"Cannot decrypt: {e}"
        except Exception as e:
            return f"Not a valid QR code for this application: {e}"

        existing_text = self.parts_by_number.get(part_number)
        if existing_text is not None:
            if existing_text == qr_text:
                logger.info(f"Part {part_number} already loaded, ignoring duplicate")
                return ""
            return (
                f"Part {part_number} was already loaded with different content -- this looks "
                f"like a different transfer. Click 'Clear List' first if you want to start over."
            )

        if self.total_parts is not None and total_parts != self.total_parts:
            return (
                f"This part claims {total_parts} total part(s), but previously loaded parts "
                f"claim {self.total_parts} -- it's likely from a different transfer"
            )

        self.total_parts = total_parts
        self.parts_by_number[part_number] = qr_text
        return ""

    def _update_status(self):
        """Refreshes the status label and the decrypt button's enabled state."""
        if self.total_parts is None:
            self.status_label.config(text="0 parts loaded")
            complete = False
        else:
            loaded = len(self.parts_by_number)
            self.status_label.config(text=f"{loaded}/{self.total_parts} parts loaded")
            complete = set(self.parts_by_number.keys()) == set(range(1, self.total_parts + 1))

        self.decrypt_button.config(state="normal" if complete else "disabled")

    def _set_busy(self, busy: bool):
        """Disables/enables the add/clear controls while a background add or decrypt is running."""
        state = "disabled" if busy else "normal"
        self.add_text_button.config(state=state)
        self.add_files_button.config(state=state)
        self.clear_button.config(state=state)
        self.config(cursor="watch" if busy else "")
        if busy:
            self.decrypt_button.config(state="disabled")

    def click_add_text(self):
        """Adds the QR text currently typed/pasted into the text field (decrypted in the background)."""
        text = self.text_field.get().strip()
        if not text:
            return

        # Support pasting multiple concatenated QR texts at once (base64 blobs end with '==').
        if len(text) > 2953 and "==" in text:
            candidates = [part.strip() + "==" for part in text.split("==") if part.strip()]
        else:
            candidates = [text]

        self.text_field.delete(0, tkinter.END)
        self._set_busy(True)

        threading.Thread(
            target=self._add_text_worker,
            args=(candidates, self.text_add_queue),
            daemon=True
        ).start()
        self.after(100, self._poll_text_add_result)

    def _add_text_worker(self, candidates, q):
        errors = [error for error in (self._try_add_part(c) for c in candidates) if error]
        q.put(errors)

    def _poll_text_add_result(self):
        try:
            errors = self.text_add_queue.get_nowait()
        except queue.Empty:
            self.after(100, self._poll_text_add_result)
            return

        self._set_busy(False)
        self._update_status()
        if errors:
            messagebox.showerror("Error", "\n".join(errors))

    @staticmethod
    def _read_qr_text_from_file(filepath: str) -> str:
        """
        Reads a QR code's text either from a QR text file (as saved by "Save All",
        one raw base64 string per file) or by decoding an image.
        """
        if filepath.lower().endswith(".txt"):
            with open(filepath, "r") as f:
                return f.read().strip()
        return service.read_qr_from_image(filepath)

    def add_qr_image(self):
        """Adds one or multiple QR code images or QR text files to the list (in the background)."""
        filetypes = [
            ("QR code files", "*.png *.jpg *.jpeg *.txt"),
            ("Image files", "*.png *.jpg *.jpeg"),
            ("Text files", "*.txt"),
            ("All files", "*.*"),
        ]
        filepaths = filedialog.askopenfilenames(filetypes=filetypes)

        if not filepaths:
            return

        self._set_busy(True)
        self.status_label.config(text=f"Loading {len(filepaths)} file(s)...")

        threading.Thread(
            target=self._add_files_worker,
            args=(list(filepaths), self.file_add_queue),
            daemon=True
        ).start()
        self.after(100, self._poll_file_add_result)

    def _add_files_worker(self, filepaths, q):
        loaded_count = 0
        errors = []

        for filepath in filepaths:
            try:
                logger.info(f"Reading QR code: {filepath}")
                qr_text = self._read_qr_text_from_file(filepath)

                error = self._try_add_part(qr_text)
                if error:
                    raise ValueError(error)

                loaded_count += 1
                logger.info(f"QR code added: {filepath}")

            except Exception as e:
                errors.append(f"{filepath}: {e}")
                logger.error(f"Could not read QR code from {filepath}: {e}")

        q.put((loaded_count, len(filepaths), errors))

    def _poll_file_add_result(self):
        try:
            loaded_count, total_files, errors = self.file_add_queue.get_nowait()
        except queue.Empty:
            self.after(100, self._poll_file_add_result)
            return

        self._set_busy(False)
        self._update_status()

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
        """Clears the list of loaded parts."""
        self.parts_by_number = {}
        self.total_parts = None
        self._update_status()
        logger.info("QR code list cleared")

    def on_click_decrypt(self):
        logger.debug("button pressed")
        if not self.parts_by_number:
            return

        output_dir = filedialog.askdirectory(title="Select output folder")
        if not output_dir:
            return

        self._set_busy(True)

        threading.Thread(
            target=self.on_click_decrypt_thread_worker,
            args=(list(self.parts_by_number.values()), self.password, output_dir, self.decrypt_result_queue),
            daemon=True
        ).start()
        self.after(250, self.process_queue)

    def on_click_decrypt_thread_worker(self, input_data, password, output_dir, q):
        try:
            logger.debug("start decryption, decompressing, extracting")
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
            message_type, data = self.decrypt_result_queue.get_nowait()
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

            self._set_busy(False)
            self._update_status()
        except queue.Empty:
            # If queue is empty, check again in 250ms
            self.after(250, self.process_queue)


if __name__ == "__main__":
    logger.info("main of extra_window.py")
