# Copyright 2025 ecki
# SPDX-License-Identifier: Apache-2.0

import time

import pytest

from app import service
from app.controller import QrExchangeController
from app.qr_multi_part import DecryptionError


def _wait_for(condition, timeout=5.0, interval=0.02) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if condition():
            return True
        time.sleep(interval)
    return False


def test_generate_qr_async_calls_on_success(tmp_path, password):
    f = tmp_path / "file.txt"
    f.write_text("controller generate test")
    controller = QrExchangeController(max_qr_bytes=2953)

    results = {}
    controller.generate_qr_async(
        [str(f)], password,
        on_success=lambda images, texts: results.update(images=images, texts=texts),
        on_error=lambda e: results.update(error=e),
    )

    assert _wait_for(lambda: results)
    assert "error" not in results
    assert len(results["images"]) == len(results["texts"]) == 1


def test_generate_qr_async_calls_on_error_for_missing_path(tmp_path, password):
    controller = QrExchangeController(max_qr_bytes=2953)

    results = {}
    controller.generate_qr_async(
        [str(tmp_path / "does-not-exist.txt")], password,
        on_success=lambda images, texts: results.update(images=images, texts=texts),
        on_error=lambda e: results.update(error=e),
    )

    assert _wait_for(lambda: results)
    assert "error" in results


def test_decrypt_qr_data_roundtrip(tmp_path, password):
    f = tmp_path / "file.txt"
    f.write_text("controller decrypt test")
    _, texts = service.generate_qr_from_paths([str(f)], password, max_bytes=2953)

    extracted = QrExchangeController.decrypt_qr_data(texts, password, str(tmp_path / "out"))

    assert len(extracted) == 1
    assert extracted[0].read_text() == "controller decrypt test"


def test_decrypt_qr_data_wrong_password_raises_decryption_error(tmp_path, password):
    f = tmp_path / "file.txt"
    f.write_text("secret")
    _, texts = service.generate_qr_from_paths([str(f)], password, max_bytes=2953)

    with pytest.raises(DecryptionError):
        QrExchangeController.decrypt_qr_data(texts, "wrong-password", str(tmp_path / "out"))


def test_is_valid_qr_part(tmp_path, password):
    f = tmp_path / "file.txt"
    f.write_text("x")
    _, texts = service.generate_qr_from_paths([str(f)], password, max_bytes=2953)

    assert QrExchangeController.is_valid_qr_part(texts[0]) is True
    assert QrExchangeController.is_valid_qr_part("garbage") is False


def test_get_part_info_single_part(tmp_path, password):
    f = tmp_path / "file.txt"
    f.write_text("part info test")
    _, texts = service.generate_qr_from_paths([str(f)], password, max_bytes=2953)
    assert len(texts) == 1

    assert QrExchangeController.get_part_info(texts[0], password) == (1, 1)


def test_get_part_info_wrong_password_raises_decryption_error(tmp_path, password):
    f = tmp_path / "file.txt"
    f.write_text("secret")
    _, texts = service.generate_qr_from_paths([str(f)], password, max_bytes=2953)

    with pytest.raises(DecryptionError):
        QrExchangeController.get_part_info(texts[0], "wrong-password")
