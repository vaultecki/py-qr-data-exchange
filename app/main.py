# Copyright 2025 ecki
# SPDX-License-Identifier: Apache-2.0

import logging
import tkinter
from tkinter import ttk

from app import extra_windows

logger = logging.getLogger(__name__)
MAX_QR_CODE_BYTES = 2953

try:
    from tkinterdnd2 import TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False


class GuiClass:
    def __init__(self):
        logger.debug("init gui")
        self.root = TkinterDnD.Tk() if DND_AVAILABLE else tkinter.Tk()
        self.root.title("PyQrDataExchange")
        self.root.minsize(640, 320)
        self.root.geometry("680x380")

        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        # Some Tk builds/themes leave TEntry's fieldbackground unset, which makes
        # entry fields visually blend into the surrounding frame. Set it explicitly.
        style.configure("TEntry", fieldbackground="white", foreground="black")
        style.map(
            "TEntry",
            fieldbackground=[("readonly", "#e8e8e8"), ("disabled", "#e8e8e8")],
            foreground=[("disabled", "#888888")],
        )

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tkinter.BOTH, expand=True)

        self.generate_tab = extra_windows.GenerateTab(notebook, MAX_QR_CODE_BYTES)
        self.read_tab = extra_windows.ReadTab(notebook)

        notebook.add(self.generate_tab, text="QR erstellen")
        notebook.add(self.read_tab, text="QR einlesen")

    def run(self):
        self.root.mainloop()


def run_app():
    logging.info("start py-qr-data-exchange")
    GuiClass().run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    run_app()
