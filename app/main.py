import logging
import queue
import threading
import tkinter
from tkinter import filedialog, messagebox

import service
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
                                            show='*',
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

        self.result_queue = queue.Queue()

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
        if not self._validate_inputs():
            return
        logger.debug("button generate qr code clicked")
        logger.info("1. UI-Feedback geben und Interaktionen sperren")
        self.button_generate.config(state="disabled")
        self.root.config(cursor="watch")
        logger.debug("get filepath and password")
        filepath = self.entry_filename.get()
        password = self.entry_password.get()
        logger.info("2. Worker-Thread starten und ihm die Queue übergeben")
        threading.Thread(
            target=self.click_button_generate_thread_worker,
            args=(filepath, password, self.result_queue),
            daemon=True
        ).start()
        logger.info("3. Den Main-Thread anweisen, die Queue regelmäßig zu prüfen")
        self.root.after(250, self.process_queue)

    def click_button_generate_thread_worker(self, filepath, password, q):
        logger.debug("try generate qr code thread")
        try:
            logger.debug("start compress, encrypt")
            qr_image, qr_text = service.generate_qr_from_file(filepath, password, MAX_QR_CODE_BYTES)
            logger.debug("ended compress, encrypt -> open next window")
            q.put(("success", (qr_image, qr_text)))
        except FileNotFoundError:
            q.put(("error", FileNotFoundError))
        except service.FileTooLargeError as e:
            q.put(("error", e))
        except Exception as e:
            q.put(("error", e))

    def process_queue(self):
        """Diese Funktion läuft sicher im Main-Thread."""
        try:
            logger.debug("Prüfen, ob etwas in der Queue ist (ohne zu blockieren)")
            message_type, data = self.result_queue.get_nowait()
            if message_type == "success":
                qr_image, qr_text = data
                QrWindow(self.root, qr_image, qr_text)
            elif message_type == "error":
                logger.debug("Jetzt kann die Fehlermeldung sicher angezeigt werden")
                if isinstance(data, FileNotFoundError):
                    messagebox.showerror("Fehler", f"Datei nicht gefunden.")
                elif isinstance(data, service.FileTooLargeError):
                    messagebox.showerror("Fehler", str(data))
                else:
                    messagebox.showerror("Unerwarteter Fehler", f"Ein Fehler ist aufgetreten: {data}")

            logger.info("4. UI-Feedback zurücksetzen, egal ob Erfolg oder Fehler")
            self.button_generate.config(state="normal")
            self.root.config(cursor="")
        except queue.Empty:
            # Wenn die Queue leer ist, in 100ms erneut prüfen
            self.root.after(250, self.process_queue)

    def click_button_filemanager(self):
        logger.debug("open filemanager to chose file")
        files = [("all files", "*.*"), ("PNG files", "*.png"), ("SVG files", "*.svg")]
        file_path = filedialog.askopenfilename(filetypes = files)
        if file_path:
            self.entry_filename.delete(0, tkinter.END)
            self.entry_filename.insert(0, str(file_path))

    def click_button_read_qr(self):
        if not self._validate_inputs(check_filename=True):
            return
        filepath = self.entry_filename.get()
        logger.debug(f"read file {filepath}")
        try:
            input_str = service.read_qr_from_image(filepath)
            ReadWindow(self.root, self.entry_password.get(), input_str)
        except FileNotFoundError:
            messagebox.showerror("Fehler", f"Datei nicht gefunden: {filepath}")
        except service.QRCodeNotFoundError as e:
            messagebox.showerror("Fehler", str(e))
        except Exception as e:
            messagebox.showerror("Unerwarteter Fehler", f"Ein Fehler ist aufgetreten: {e}")

    def click_button_read_string(self):
        if not self._validate_inputs(check_filename=False):
            return
        logger.debug(f"open read window without qr text sting")
        ReadWindow(self.root, self.entry_password.get())


def run_app():
    logger.info("start py-qr-data-exchange")
    py_qr_data_gui = GuiClass()
    py_qr_data_gui.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logger.info("start py-qr-data-exchange")
    run_app()
