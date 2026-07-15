# Copyright [2025] [ecki]
# SPDX-License-Identifier: Apache-2.0

import logging
import qrcode
from pathlib import Path
from typing import List, Sequence, Tuple
from PIL import Image

from app import qr_multi_part

logger = logging.getLogger(__name__)


# Custom error classes for better feedback
class QRCodeNotFoundError(Exception):
    pass


def generate_qr_from_paths(paths: Sequence[str], password: str, max_bytes: int) -> Tuple[List[Image.Image], List[str]]:
    """
    Packs one or more files/directories, encrypts them and returns QR code image(s).

    Args:
        paths: Files and/or directories to bundle and encrypt.
        password: Password for encryption.
        max_bytes: Maximum size (base64 chars) per QR code.

    Returns:
        (images, texts) -- always lists, length 1 if everything fits in one QR code.
    """
    qr_strings = qr_multi_part.MultiPartQrProcessor.serialize_paths(list(paths), password, max_bytes)

    images = []
    for i, qr_string in enumerate(qr_strings, 1):
        image = qrcode.make(qr_string, error_correction=1)
        images.append(image)
        logger.debug(f"QR code {i}/{len(qr_strings)} created")

    logger.info(f"{len(images)} QR code(s) created")
    return images, qr_strings


def read_qr_from_image(filepath: str) -> str:
    """
    Reads a QR code image and returns the contained text.

    Uses qreader library for better detection and robustness.
    Falls back to OpenCV if qreader is not available.
    """
    # Try qreader first (more robust)
    try:
        from qreader import QReader

        logger.debug(f"Reading QR code with qreader: {filepath}")
        qreader_instance = QReader()

        # Read image with PIL
        image = Image.open(filepath)

        # Detect and decode QR code
        decoded_text = qreader_instance.detect_and_decode(image=image)

        # qreader returns a tuple with detected QR codes
        if decoded_text and len(decoded_text) > 0:
            # Take first QR code if multiple detected
            result = decoded_text[0] if isinstance(decoded_text, tuple) else decoded_text

            if result:
                logger.info(f"QR code successfully read with qreader")
                return result

        logger.warning("qreader: No QR code detected, trying OpenCV fallback")

    except ImportError:
        logger.debug("qreader not available, using OpenCV")
    except Exception as e:
        logger.warning(f"qreader failed: {e}, trying OpenCV fallback")

    # Fallback to OpenCV
    try:
        import cv2

        logger.debug(f"Reading QR code with OpenCV: {filepath}")
        image = cv2.imread(filepath)

        if image is None:
            raise QRCodeNotFoundError("Image could not be read.")

        detector = cv2.QRCodeDetector()
        decoded_text, _, _ = detector.detectAndDecode(image)

        if not decoded_text:
            raise QRCodeNotFoundError("No QR code found in image.")

        logger.info("QR code successfully read with OpenCV")
        return decoded_text

    except ImportError:
        raise QRCodeNotFoundError(
            "No QR code reader available. Install either 'qreader' or 'opencv-python'."
        )


def read_multiple_qr_from_images(filepaths: List[str]) -> List[str]:
    """
    Reads multiple QR code images.

    Args:
        filepaths: List of image paths

    Returns:
        List of QR code texts
    """
    qr_texts = []
    for filepath in filepaths:
        try:
            text = read_qr_from_image(filepath)
            qr_texts.append(text)
        except Exception as e:
            logger.error(f"Error reading {filepath}: {e}")
            raise

    return qr_texts


def is_valid_qr_part(qr_text: str) -> bool:
    """Structural check only (no password needed): does this look like one of our QR codes?"""
    return qr_multi_part.MultiPartQrProcessor.is_valid_qr_part(qr_text)


def get_part_info(qr_text: str, password: str) -> Tuple[int, int]:
    """
    Decrypts a single QR part and returns (part_number, total_parts).

    Requires the correct password, since this info lives inside the ciphertext.
    Raises qr_multi_part.DecryptionError on a wrong password or corrupted part.
    """
    inner = qr_multi_part.MultiPartQrProcessor.decrypt_part(qr_text, password)
    return inner["p"], inner["t"]


def decrypt_qr_data(qr_texts: Sequence[str], password: str, output_dir: str) -> List[Path]:
    """
    Decrypts QR data and extracts the resulting archive into output_dir.

    Args:
        qr_texts: QR code strings (one or more, any order).
        password: Password for decryption.
        output_dir: Directory to extract the recovered files/folders into.

    Returns:
        List of extracted file paths.
    """
    if not qr_texts:
        raise ValueError("No QR texts provided")

    tar_bytes = qr_multi_part.MultiPartQrProcessor.deserialize_to_bytes(list(qr_texts), password)
    return qr_multi_part.MultiPartQrProcessor.extract_tar(tar_bytes, output_dir)


if __name__ == "__main__":
    import shutil
    import tempfile

    logging.basicConfig(level=logging.DEBUG)
    logger.info("main of service.py")

    test_password = "test123"
    workdir = tempfile.mkdtemp()
    try:
        test_file = Path(workdir) / "test.txt"
        test_file.write_bytes(b"Test " * 2000)  # ~10KB

        # Generate
        images, texts = generate_qr_from_paths([str(test_file)], test_password, max_bytes=500)
        logger.info(f"{len(images)} QR code(s) created")

        # Save first QR code and test reading it back
        test_qr_path = Path(workdir) / "test_qr.png"
        images[0].save(test_qr_path)

        read_text = read_qr_from_image(str(test_qr_path))
        logger.info(f"QR read test: {'OK' if read_text == texts[0] else 'FAILED'}")

        # Decrypt
        out_dir = Path(workdir) / "out"
        extracted = decrypt_qr_data(texts, test_password, str(out_dir))
        assert len(extracted) == 1
        assert extracted[0].read_bytes() == test_file.read_bytes()
        logger.info("Round-trip test successful!")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
