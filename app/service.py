# Copyright [2025] [ecki]
# SPDX-License-Identifier: Apache-2.0

import logging
import qrcode
import os
from typing import List, Tuple, Union, Optional
from PIL import Image

from app import qr_data_class
from app import qr_multi_part

logger = logging.getLogger(__name__)


# Custom error classes for better feedback
class FileTooLargeError(Exception):
    pass


class QRCodeNotFoundError(Exception):
    pass


def generate_qr_from_file(filepath: str, password: str, max_bytes: int) -> Union[
    Tuple[Image.Image, str],
    Tuple[List[Image.Image], List[str]]
]:
    """
    Reads a file, encrypts it and returns QR code image(s).

    Returns:
        Either (single_image, single_text) or ([images], [texts]) for multi-part
    """
    with open(filepath, "rb") as f_in:
        raw_data = f_in.read()

    # Try single-part first
    try:
        encoded_string = qr_data_class.QrDataProcessor.serialize(raw_data=raw_data, password=password)

        if len(encoded_string) < max_bytes:
            # Single QR code is sufficient
            image = qrcode.make(encoded_string, error_correction=1)
            logger.info(f"Single QR code created ({len(encoded_string)} bytes)")
            return image, encoded_string
    except Exception as e:
        logger.debug(f"Single-part failed: {e}")

    # File is too large -> multi-part
    logger.info("File too large for single QR code, using multi-part")

    # Extract filename from filepath
    file_name = os.path.basename(filepath)

    qr_strings = qr_multi_part.MultiPartQrProcessor.serialize_multipart(
        raw_data, password, max_bytes, file_name=file_name
    )

    images = []
    for i, qr_string in enumerate(qr_strings, 1):
        image = qrcode.make(qr_string, error_correction=1)
        images.append(image)
        logger.debug(f"Multi-part QR {i}/{len(qr_strings)} created")

    logger.info(f"Multi-part: {len(images)} QR codes created")
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


def is_multipart_qr(qr_text: str) -> bool:
    """Checks if a QR text is a multi-part QR."""
    return qr_multi_part.MultiPartQrProcessor.is_multipart_qr(qr_text)


def get_multipart_info(qr_text: str) -> Tuple[int, int]:
    """
    Returns information about a multi-part QR.

    Returns:
        (part_number, total_parts)
    """
    return qr_multi_part.MultiPartQrProcessor.get_part_info(qr_text)


def decrypt_qr_data(qr_texts: Union[str, List[str]], password: str) -> Tuple[bytes, Optional[str], Optional[float]]:
    """
    Decrypts QR data (single-part or multi-part).

    Args:
        qr_texts: Either a single QR string or a list of QR strings
        password: Password for decryption

    Returns:
        Tuple of (raw_data, filename, timestamp)
        For single-part QR codes, filename and timestamp will be None
    """
    # Normalize input to list
    if isinstance(qr_texts, str):
        qr_texts = [qr_texts]

    if not qr_texts:
        raise ValueError("No QR texts provided")

    # Check if multi-part
    if is_multipart_qr(qr_texts[0]):
        logger.info("Multi-part QR code detected")
        return qr_multi_part.MultiPartQrProcessor.deserialize_multipart(qr_texts, password)
    else:
        # Single-part
        if len(qr_texts) > 1:
            logger.warning(f"Multiple QR codes provided, but first is not multi-part. Using only the first.")

        logger.info("Single-part QR code detected")
        raw_data = qr_data_class.QrDataProcessor.deserialize(qr_texts[0], password)
        return raw_data, None, None


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logger.info("main of service.py")

    # Test multi-part
    test_password = "test123"
    test_data = b"Test " * 2000  # ~10KB

    import tempfile

    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.txt') as f:
        f.write(test_data)
        temp_path = f.name

    try:
        # Generate
        result = generate_qr_from_file(temp_path, test_password, max_bytes=500)

        if isinstance(result[0], list):
            images, texts = result
            logger.info(f"Multi-part: {len(images)} QR codes created")

            # Save first QR code for testing
            test_qr_path = tempfile.mktemp(suffix='.png')
            images[0].save(test_qr_path)
            logger.info(f"Test QR saved to: {test_qr_path}")

            # Test reading
            try:
                read_text = read_qr_from_image(test_qr_path)
                logger.info(f"QR read test: {'✓ SUCCESS' if read_text == texts[0] else '✗ FAILED'}")
            except Exception as e:
                logger.error(f"QR read test failed: {e}")
            finally:
                import os

                os.unlink(test_qr_path)

            # Decrypt
            restored, filename, timestamp = decrypt_qr_data(texts, test_password)
            assert restored == test_data
            logger.info(f"✓ Multi-part test successful! Filename: {filename}")
        else:
            logger.info("Single-part QR code created")
    finally:
        import os
        os.unlink(temp_path)
