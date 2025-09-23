# Copyright [2025] [ecki]
# SPDX-License-Identifier: Apache-2.0

import cv2
import logging
import qrcode

from app import qr_data_class

logger = logging.getLogger(__name__)


# Eigene Fehlerklassen für besseres Feedback
class FileTooLargeError(Exception):
    pass


class QRCodeNotFoundError(Exception):
    pass


def generate_qr_from_file(filepath: str, password: str, max_bytes: int):
    """Liest eine Datei, verschlüsselt sie und gibt ein QR-Code-Bildobjekt zurück."""
    with open(filepath, "rb") as f_in:
        raw_data = f_in.read()

    encoded_string = qr_data_class.QrDataProcessor.serialize(raw_data=raw_data, password=password)

    if len(encoded_string) >= max_bytes:
        raise FileTooLargeError(f"Die Datei ist mit {len(encoded_string)} Bytes zu groß.")

    image = qrcode.make(encoded_string, error_correction=1)
    return image, encoded_string


def read_qr_from_image(filepath: str) -> str:
    """Liest ein QR-Code-Bild und gibt den enthaltenen Text zurück."""
    image = cv2.imread(filepath)
    if image is None:
        raise cv2.error("Bild konnte nicht gelesen werden.")  # OpenCV gibt None zurück, nicht immer einen Error

    detector = cv2.QRCodeDetector()
    decoded_text, _, _ = detector.detectAndDecode(image)

    if not decoded_text:
        raise QRCodeNotFoundError("Im Bild wurde kein QR-Code gefunden.")

    return decoded_text


if __name__ == "__main__":
    logger.info("main of extra_window.py")
