# Copyright [2025] [ecki]
# SPDX-License-Identifier: Apache-2.0

# controller.py
import threading
import logging
from typing import Callable, Union, List
from PIL import Image

from app import service
from app.qr_data_class import DecryptionError

logger = logging.getLogger(__name__)


class QrExchangeController:
    """
    Mediates between GUI and business logic.
    GUI calls controller methods and receives callbacks for success/errors.
    """

    def __init__(self, max_qr_bytes: int = 2953):
        self.max_qr_bytes = max_qr_bytes

    def generate_qr_async(self, filepath: str, password: str,
                          on_success: Callable[[Union[Image.Image, List[Image.Image]],
                                                Union[str, List[str]]], None],
                          on_error: Callable[[Exception], None]):
        """
        Starts a worker thread that reads file and generates QR code(s).

        on_success receives either:
        - (single_image, single_text) for single-part
        - ([images], [texts]) for multi-part
        """

        def worker():
            try:
                result = service.generate_qr_from_file(
                    filepath, password, self.max_qr_bytes
                )
                qr_image, qr_text = result
                on_success(qr_image, qr_text)
            except Exception as e:
                on_error(e)

        threading.Thread(target=worker, daemon=True).start()

    @staticmethod
    def read_qr_from_image_async(filepath: str,
                                 on_success: Callable[[str], None],
                                 on_error: Callable[[Exception], None]):
        """
        Asynchronously reads a QR code from an image.
        """

        def worker():
            try:
                text = service.read_qr_from_image(filepath)
                on_success(text)
            except Exception as e:
                on_error(e)

        threading.Thread(target=worker, daemon=True).start()

    @staticmethod
    def read_multiple_qr_from_images_async(filepaths: List[str],
                                           on_success: Callable[[List[str]], None],
                                           on_error: Callable[[Exception], None]):
        """
        Asynchronously reads multiple QR codes from images.
        """

        def worker():
            try:
                texts = service.read_multiple_qr_from_images(filepaths)
                on_success(texts)
            except Exception as e:
                on_error(e)

        threading.Thread(target=worker, daemon=True).start()

    @staticmethod
    def decrypt_qr_data(qr_texts: Union[str, List[str]], password: str) -> bytes:
        """
        Pure business logic: no thread needed, called from UI thread.
        Supports single-part and multi-part QR codes.
        """
        try:
            return service.decrypt_qr_data(qr_texts, password)
        except DecryptionError as e:
            raise e
        except Exception as e:
            raise Exception(f"Unexpected error during decryption: {e}")

    @staticmethod
    def is_multipart_qr(qr_text: str) -> bool:
        """Checks if a QR text is a multi-part QR."""
        return service.is_multipart_qr(qr_text)

    @staticmethod
    def get_multipart_info(qr_text: str):
        """Returns information about a multi-part QR."""
        return service.get_multipart_info(qr_text)
