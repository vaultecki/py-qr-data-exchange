# Copyright [2025] [ecki]
# SPDX-License-Identifier: Apache-2.0

import threading
import logging
from pathlib import Path
from typing import Callable, List, Tuple
from PIL import Image

from app import service
from app.qr_multi_part import DecryptionError

logger = logging.getLogger(__name__)


class QrExchangeController:
    """
    Mediates between GUI and business logic.
    GUI calls controller methods and receives callbacks for success/errors.
    """

    def __init__(self, max_qr_bytes: int = 2953):
        self.max_qr_bytes = max_qr_bytes

    def generate_qr_async(self, paths: List[str], password: str,
                          on_success: Callable[[List[Image.Image], List[str]], None],
                          on_error: Callable[[Exception], None]):
        """
        Starts a worker thread that packs the given files/directories and generates QR code(s).

        on_success receives (images, texts) -- always lists.
        """

        def worker():
            try:
                images, texts = service.generate_qr_from_paths(
                    paths, password, self.max_qr_bytes
                )
                logger.info(f"QR generation complete. {len(images)} QR code(s)")
                on_success(images, texts)
            except Exception as e:
                logger.error(f"QR generation error: {e}")
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
    def decrypt_qr_data(qr_texts: List[str], password: str, output_dir: str) -> List[Path]:
        """
        Pure business logic: no thread needed, called from UI thread.

        Decrypts and extracts the recovered files/folders into output_dir.

        Returns:
            List of extracted file paths.
        """
        try:
            return service.decrypt_qr_data(qr_texts, password, output_dir)
        except DecryptionError as e:
            raise e
        except Exception as e:
            raise Exception(f"Unexpected error during decryption: {e}")

    @staticmethod
    def is_valid_qr_part(qr_text: str) -> bool:
        """Structural check only: does this look like one of our QR codes?"""
        return service.is_valid_qr_part(qr_text)

    @staticmethod
    def get_part_info(qr_text: str, password: str) -> Tuple[int, int]:
        """
        Decrypts a single QR part just enough to learn its part number and
        total-part count. Requires the correct password (this info is encrypted).
        """
        try:
            return service.get_part_info(qr_text, password)
        except DecryptionError as e:
            raise e
        except Exception as e:
            raise Exception(f"Unexpected error while reading part info: {e}")
