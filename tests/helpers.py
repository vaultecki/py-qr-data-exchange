# Copyright 2025 ecki
# SPDX-License-Identifier: Apache-2.0

import time


def pump_until(root, condition, timeout=10.0, interval=0.02) -> bool:
    """Repeatedly processes the Tk event loop until condition() is true or timeout elapses."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        root.update()
        if condition():
            return True
        time.sleep(interval)
    return False


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
