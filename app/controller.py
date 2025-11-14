# controller.py
import threading
import logging
from typing import Callable

from app import service
from app.qr_data_class import DecryptionError

logger = logging.getLogger(__name__)


class QrExchangeController:
    """
    Vermittelt zwischen der GUI und der Business-Logik.
    Die GUI ruft Methoden des Controllers auf und bekommt Callbacks für Erfolge/Fehler.
    """

    def __init__(self, max_qr_bytes: int = 2953):
        self.max_qr_bytes = max_qr_bytes

    def generate_qr_async(self, filepath: str, password: str,
                          on_success: Callable[[object, str], None],
                          on_error: Callable[[Exception], None]):
        """
        Startet einen Worker-Thread, der Datei liest + QR erzeugt.
        """

        def worker():
            try:
                qr_image, qr_text = service.generate_qr_from_file(
                    filepath, password, self.max_qr_bytes
                )
                on_success(qr_image, qr_text)
            except Exception as e:
                on_error(e)

        threading.Thread(target=worker, daemon=True).start()

    @staticmethod
    def read_qr_from_image_async(filepath: str,
                                 on_success: Callable[[str], None],
                                 on_error: Callable[[Exception], None]):
        """
        Asynchrones Auslesen eines QR-Codes aus einem Bild.
        """

        def worker():
            try:
                text = service.read_qr_from_image(filepath)
                on_success(text)
            except Exception as e:
                on_error(e)

        threading.Thread(target=worker, daemon=True).start()

    @staticmethod
    def decrypt_qr_string(input_string: str, password: str) -> bytes:
        """
        Reine Business-Logik: kein Thread nötig, wird vom UI-Thread aufgerufen.
        """
        try:
            from app.qr_data_class import QrDataProcessor
            return QrDataProcessor.deserialize(input_string, password)
        except DecryptionError as e:
            raise e
        except Exception as e:
            raise Exception(f"Unerwarteter Fehler beim Entschlüsseln: {e}")
