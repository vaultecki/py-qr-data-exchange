# Copyright [2025] [ecki]
# SPDX-License-Identifier: Apache-2.0


def qr_reader_available() -> bool:
    """Whether a real QR-decoding backend (qreader or opencv) is installed."""
    try:
        import cv2  # noqa: F401
        return True
    except ImportError:
        pass
    try:
        import qreader  # noqa: F401
        return True
    except ImportError:
        pass
    return False
