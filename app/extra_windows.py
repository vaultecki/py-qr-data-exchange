import logging
import math
import queue
import threading
import tkinter
import io
from tkinter import Toplevel, filedialog, messagebox

import qr_data_class

logger = logging.getLogger(__name__)


class QrWindow(Toplevel):
    def __init__(self, master, qr_code_generated, qr_code_text):
        super().__init__(master)
        logger.info("open qr code display window")
        self.title("Generierter QR-Code")

        tkinter.Label(self, text="Qr Code wurde generiert:").grid(row=0, column=0, padx=5, pady=5)
        var_qr_code_text = tkinter.StringVar(self, qr_code_text)
        tkinter.Entry(self, width=60, textvariable=var_qr_code_text, state="readonly").grid(row=0, column=1,
                                                                                            padx=5, pady=5)

        self.qr_code_generated = qr_code_generated

        maxsize = math.floor((min(self.winfo_screenwidth(), self.winfo_screenheight()))*0.8)
        resize_image = qr_code_generated.resize((maxsize, maxsize))

        output = io.BytesIO()
        resize_image.save(output, format='PNG')

        self.image_qr = tkinter.PhotoImage(data=output.getvalue(), master=self)
        self.tkinter_qr = tkinter.Label(master=self, image=self.image_qr)
        self.tkinter_qr.grid(row=1, column=0, columnspan=2, padx=5, pady=5)

        self.button = tkinter.Button(master=self, text="Save As", command=self.save_file)
        self.button.grid(row=2, column=0, columnspan=2, padx=5, pady=5)

        self.transient(master)
        self.grab_set()

    def save_file(self):
        files = [("PNG files", "*.png"), ("SVG files", "*.svg")]
        file_out = filedialog.asksaveasfilename(filetypes = files, defaultextension = ".png")
        if file_out:
            self.qr_code_generated.save("{}".format(file_out))


class ReadWindow(Toplevel):
    def __init__(self, master, password, qr_text=""):
        super().__init__(master)
        logger.info("open qr read window")
        self.password = password
        self.title("Qr Data Read")

        tkinter.Label(self, text="Text to convert:").grid(row=0, column=0, padx=5, pady=5)
        if qr_text:
            text = tkinter.StringVar(self, qr_text)
            self.text_field = tkinter.Entry(self, textvariable=text, width=60, state="readonly")
        else:
            self.text_field = tkinter.Entry(self, width=60)
        self.text_field.grid(row=0, column=1, padx=5, pady=5)

        self.button =tkinter.Button(self, text="Decrypt and Save as", command=self.on_click_decrypt)
        self.button.grid(row=1, column=1, padx=5, pady=5)

        self.result_queue = queue.Queue()

        self.transient(master)
        self.grab_set()

    def on_click_decrypt(self):
        logger.debug("button pressed")
        self.button.config(state="disabled")
        self.config(cursor="watch")
        input_str = self.text_field.get()
        threading.Thread(
            target=self.on_click_decrypt_thread_worker,
            args=(input_str, self.password, self.result_queue),
            daemon=True
        ).start()
        self.after(250, self.process_queue)

    def on_click_decrypt_thread_worker(self, input_str, password, q):
        try:
            logger.debug("start decryption, decompressing")
            qr_data = qr_data_class.QrDataProcessor.deserialize(input_string=input_str,
                                                                password=password)
            logger.debug("ended decryption, decompressing")
            q.put(("success", qr_data))
        except qr_data_class.DecryptionError as e:
            logger.error(f"can not decrypt string: {e}")
            q.put(("error", e))

    def process_queue(self):
        """Diese Funktion läuft sicher im Main-Thread."""
        try:
            logger.debug("Prüfen, ob etwas in der Queue ist (ohne zu blockieren)")
            message_type, data = self.result_queue.get_nowait()
            if message_type == "success":
                files = [("all files", "*.*")]
                logger.debug("open file dialog")
                file_out = filedialog.asksaveasfilename(filetypes=files)
                if file_out:
                    with (open(file_out, "wb+")) as f_out:
                        f_out.write(data)
            elif message_type == "error":
                logger.debug("Jetzt kann die Fehlermeldung sicher angezeigt werden")
                if isinstance(data, qr_data_class.DecryptionError):
                    messagebox.showerror("Fehler", f"can not decrypt string: {str(data)}")
                else:
                    messagebox.showerror("Unerwarteter Fehler", f"Ein Fehler ist aufgetreten: {data}")

            self.button.config(state="normal")
            self.config(cursor="")
        except queue.Empty:
            # Wenn die Queue leer ist, in 100ms erneut prüfen
            self.after(250, self.process_queue)

if __name__ == "__main__":
    logger.info("main of extra_window.py")
