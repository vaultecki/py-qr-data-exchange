# Copyright 2025 ecki
# SPDX-License-Identifier: Apache-2.0

import io
import logging
import math
import queue
import threading
import tkinter
from pathlib import Path
from tkinter import Toplevel, filedialog, messagebox, ttk
from typing import List

from PIL import Image

from app import qr_multi_part, service
from app.controller import QrExchangeController

logger = logging.getLogger(__name__)

try:
    from tkinterdnd2 import DND_FILES
    DND_SUPPORTED = True
except ImportError:
    DND_FILES = None
    DND_SUPPORTED = False


class GenerateTab(ttk.Frame):
    """Tab content for building and generating QR code(s) from files/folders."""

    def __init__(self, master, max_qr_bytes: int = 2953):
        super().__init__(master, padding=10)
        logger.debug("init generate tab")

        self.controller = QrExchangeController(max_qr_bytes)
        self.selected_paths: List[str] = []

        self.label_password = ttk.Label(self, text="Password:")
        self.label_password.grid(row=0, column=0, padx=5, pady=5, sticky=tkinter.E)

        self.password_var = tkinter.StringVar(self, "")
        self.entry_password = ttk.Entry(
            self, width=25,
            show='*',
            textvariable=self.password_var
        )
        self.entry_password.grid(row=0, column=1, padx=5, pady=5, sticky="we")

        self.label_filename = ttk.Label(self, text="Files/Folder:")
        self.label_filename.grid(row=1, column=0, padx=5, pady=5, sticky=tkinter.E)

        self.entry_filename = ttk.Entry(self, width=35, state="readonly")
        self.entry_filename.grid(row=1, column=1, padx=5, pady=5, sticky="we")

        button_frame = ttk.Frame(self)
        button_frame.grid(row=1, column=2, padx=5, pady=5)

        self.button_browse_files = ttk.Button(
            button_frame, text="Browse Files",
            command=self.click_button_browse_files
        )
        self.button_browse_files.pack(side=tkinter.LEFT, padx=2)

        self.button_browse_folder = ttk.Button(
            button_frame, text="Browse Folder",
            command=self.click_button_browse_folder
        )
        self.button_browse_folder.pack(side=tkinter.LEFT, padx=2)

        hint_text = (
            "...or drag & drop files/folders onto the field above"
            if DND_SUPPORTED else ""
        )
        self.dnd_hint_label = ttk.Label(self, text=hint_text, foreground="gray")
        self.dnd_hint_label.grid(row=2, column=1, padx=5, sticky="w")

        self.button_generate = ttk.Button(
            self, text="Generate QR",
            command=self.click_button_generate
        )
        self.button_generate.grid(row=3, column=2, padx=5, pady=15, sticky="e")

        self.columnconfigure(1, weight=1, minsize=140)

        self._setup_dnd()

    def _setup_dnd(self):
        if not DND_SUPPORTED:
            return
        self.entry_filename.drop_target_register(DND_FILES)
        self.entry_filename.dnd_bind('<<Drop>>', self._on_drop)

    def _on_drop(self, event):
        paths = self.tk.splitlist(event.data)
        if paths:
            self.selected_paths = list(paths)
            self._update_filename_display()

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
        self.after(100, self._poll_generate_result, result_queue)

    def _poll_generate_result(self, result_queue):
        """Runs safely on the main thread."""
        try:
            message_type, data = result_queue.get_nowait()
        except queue.Empty:
            self.after(100, self._poll_generate_result, result_queue)
            return

        self._enable_ui()

        if message_type == "success":
            qr_images, qr_texts = data
            logger.info(f"Generate success. {len(qr_images)} QR code(s)")
            try:
                QrWindow(self.winfo_toplevel(), qr_images, qr_texts)
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

    def _disable_ui(self):
        self.button_generate.config(state="disabled")
        self.winfo_toplevel().config(cursor="watch")

    def _enable_ui(self):
        self.button_generate.config(state="normal")
        self.winfo_toplevel().config(cursor="")


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

        self.part_label = tkinter.Label(
            nav_frame, text=f"Part {self.current_index + 1}/{len(self.qr_codes)}"
        )
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
        text = self.qr_texts[index]
        self.text_var.set(text[:50] + "..." if len(text) > 50 else text)

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
        is_last = self.current_index >= len(self.qr_codes) - 1
        self.next_button.config(state="disabled" if is_last else "normal")
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
        label.image = photo  # type: ignore[attr-defined]  # keep reference, prevents GC
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
            directory = Path(directory)
            for i, qr_image in enumerate(self.qr_codes, 1):
                filename = f"qr_part_{i}_of_{len(self.qr_codes)}.png"
                filepath = directory / filename
                qr_image.save(str(filepath))
            for i, qr_string in enumerate(self.qr_texts, 1):
                filename = f"qr_part_{i}_of_{len(self.qr_codes)}.txt"
                filepath = directory / filename
                with filepath.open("w") as text_file:
                    text_file.write(qr_string)

            messagebox.showinfo("Success",
                                f"{len(self.qr_codes)} QR codes saved to:\n{directory}")


class ReadTab(ttk.Frame):
    """Tab content for loading QR code part(s) and decrypting/extracting them."""

    def __init__(self, master):
        super().__init__(master, padding=10)
        logger.info("init read tab")
        # part_number -> qr_text, for parts confirmed to belong to this transfer
        self.parts_by_number = {}
        self.total_parts = None  # only known once at least one part decrypts successfully

        # Password
        ttk.Label(self, text="Password:").grid(row=0, column=0, padx=5, pady=5, sticky=tkinter.E)
        self.password_var = tkinter.StringVar(self, "")
        self.entry_password = ttk.Entry(
            self, width=25, show='*', textvariable=self.password_var
        )
        self.entry_password.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # Text input
        ttk.Label(self, text="Text to add:").grid(row=1, column=0, padx=5, pady=5, sticky=tkinter.E)
        self.text_field = ttk.Entry(self, width=50)
        self.text_field.grid(row=1, column=1, padx=5, pady=5, sticky="we")
        self.add_text_button = ttk.Button(self, text="Add", command=self.click_add_text)
        self.add_text_button.grid(row=1, column=2, padx=5, pady=5)

        # Multi-part section
        self.multipart_frame = ttk.Labelframe(self, text="Loaded Parts", padding=8)
        self.multipart_frame.grid(row=2, column=0, columnspan=3, padx=5, pady=10, sticky="we")

        self.add_files_button = ttk.Button(self.multipart_frame, text="Add QR Code File(s)",
                                           command=self.add_qr_image)
        self.add_files_button.pack(side=tkinter.LEFT, padx=5)

        self.status_label = ttk.Label(self.multipart_frame, text="0 parts loaded")
        self.status_label.pack(side=tkinter.LEFT, padx=10)

        self.clear_button = ttk.Button(self.multipart_frame, text="Clear List",
                                       command=self.clear_qr_list)
        self.clear_button.pack(side=tkinter.LEFT, padx=5)

        dnd_hint_text = "...or drag & drop QR image/text files here" if DND_SUPPORTED else ""
        self.dnd_hint_label = ttk.Label(self, text=dnd_hint_text, foreground="gray")
        self.dnd_hint_label.grid(row=3, column=1, padx=5, sticky="w")

        # Decrypt button -- stays disabled until every part of the transfer is loaded
        self.decrypt_button = ttk.Button(
            self, text="Decrypt and Extract to Folder",
            command=self.on_click_decrypt, state="disabled"
        )
        self.decrypt_button.grid(row=4, column=2, padx=5, pady=10)

        self.columnconfigure(1, weight=1, minsize=140)

        self.decrypt_result_queue = queue.Queue()
        self.text_add_queue = queue.Queue()
        self.file_add_queue = queue.Queue()
        self._destroyed = False

        self._setup_dnd()

    def _setup_dnd(self):
        if not DND_SUPPORTED:
            return
        self.multipart_frame.drop_target_register(DND_FILES)
        self.multipart_frame.dnd_bind('<<Drop>>', self._on_drop_files)

    def _on_drop_files(self, event):
        filepaths = self.tk.splitlist(event.data)
        if filepaths:
            self._start_adding_files(list(filepaths))

    def destroy(self):
        # Background add/decrypt workers keep running after the tab's window closes
        # and schedule self.after(...) poll callbacks; this flag lets those callbacks
        # bail out instead of touching widgets that no longer exist.
        self._destroyed = True
        super().destroy()

    def _try_add_part(self, qr_text: str, password: str) -> str:
        """
        Attempts to decrypt and record a single QR part. Runs the (comparatively
        expensive, full-Argon2i) decryption, so call this off the main thread.

        `password` must be captured on the main thread beforehand (StringVar.get()
        is a Tk/Tcl call and isn't safe from a background thread).

        Returns an empty string on success (including a harmless re-add of an
        already-loaded part), or an error message describing why the part was
        rejected.
        """
        qr_text = qr_text.strip()
        if not qr_text:
            return "Empty text"

        try:
            part_number, total_parts = QrExchangeController.get_part_info(qr_text, password)
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
        self.winfo_toplevel().config(cursor="watch" if busy else "")
        if busy:
            self.decrypt_button.config(state="disabled")

    def click_add_text(self):
        """Adds the QR text typed/pasted into the text field (decrypted in the background)."""
        text = self.text_field.get().strip()
        if not text:
            return

        # Support pasting multiple concatenated QR texts at once (base64 blobs end with '==').
        if len(text) > 2953 and "==" in text:
            candidates = [part.strip() + "==" for part in text.split("==") if part.strip()]
        else:
            candidates = [text]

        password = self.password_var.get()

        self.text_field.delete(0, tkinter.END)
        self._set_busy(True)

        threading.Thread(
            target=self._add_text_worker,
            args=(candidates, password, self.text_add_queue),
            daemon=True
        ).start()
        self.after(100, self._poll_text_add_result)

    def _add_text_worker(self, candidates, password, q):
        errors = [error for error in (self._try_add_part(c, password) for c in candidates) if error]
        q.put(errors)

    def _poll_text_add_result(self):
        if self._destroyed:
            return
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
            with Path(filepath).open() as f:
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

        self._start_adding_files(list(filepaths))

    def _start_adding_files(self, filepaths: List[str]):
        """Kicks off the background worker that reads/decrypts the given files."""
        password = self.password_var.get()

        self._set_busy(True)
        self.status_label.config(text=f"Loading {len(filepaths)} file(s)...")

        threading.Thread(
            target=self._add_files_worker,
            args=(filepaths, password, self.file_add_queue),
            daemon=True
        ).start()
        self.after(100, self._poll_file_add_result)

    def _add_files_worker(self, filepaths, password, q):
        loaded_count = 0
        errors = []

        for filepath in filepaths:
            try:
                logger.info(f"Reading QR code: {filepath}")
                qr_text = self._read_qr_text_from_file(filepath)

                error = self._try_add_part(qr_text, password)
                if error:
                    raise ValueError(error)

                loaded_count += 1
                logger.info(f"QR code added: {filepath}")

            except Exception as e:
                errors.append(f"{filepath}: {e}")
                logger.error(f"Could not read QR code from {filepath}: {e}")

        q.put((loaded_count, len(filepaths), errors))

    def _poll_file_add_result(self):
        if self._destroyed:
            return
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
            args=(
                list(self.parts_by_number.values()),
                self.password_var.get(), output_dir, self.decrypt_result_queue,
            ),
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
        if self._destroyed:
            return
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
