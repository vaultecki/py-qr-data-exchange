# Copyright [2025] [ecki]
# SPDX-License-Identifier: Apache-2.0

import pytest
from PIL import Image

from app import service
from helpers import qr_reader_available


def test_generate_qr_from_paths_returns_matching_lists(tmp_path, password):
    f = tmp_path / "file.txt"
    f.write_text("hello")

    images, texts = service.generate_qr_from_paths([str(f)], password, max_bytes=2953)
    assert len(images) == len(texts) == 1


def test_generate_and_decrypt_roundtrip(tmp_path, password):
    f = tmp_path / "file.txt"
    f.write_text("hello service roundtrip")

    _, texts = service.generate_qr_from_paths([str(f)], password, max_bytes=2953)
    extracted = service.decrypt_qr_data(texts, password, str(tmp_path / "out"))

    assert len(extracted) == 1
    assert extracted[0].read_text() == "hello service roundtrip"


def test_decrypt_qr_data_rejects_empty_list(tmp_path, password):
    with pytest.raises(ValueError):
        service.decrypt_qr_data([], password, str(tmp_path / "out"))


def test_is_valid_qr_part(tmp_path, password):
    f = tmp_path / "file.txt"
    f.write_text("x")
    _, texts = service.generate_qr_from_paths([str(f)], password, max_bytes=2953)

    assert service.is_valid_qr_part(texts[0]) is True
    assert service.is_valid_qr_part("garbage") is False


@pytest.mark.skipif(not qr_reader_available(), reason="no QR reader backend (qreader/opencv) installed")
def test_read_qr_from_image_roundtrip(tmp_path, password):
    f = tmp_path / "file.txt"
    f.write_text("image round trip")

    images, texts = service.generate_qr_from_paths([str(f)], password, max_bytes=2953)
    qr_path = tmp_path / "qr.png"
    images[0].save(qr_path)

    assert service.read_qr_from_image(str(qr_path)) == texts[0]


@pytest.mark.skipif(not qr_reader_available(), reason="no QR reader backend (qreader/opencv) installed")
def test_read_qr_from_image_without_qr_raises(tmp_path):
    blank = Image.new("RGB", (200, 200), color="white")
    path = tmp_path / "blank.png"
    blank.save(path)

    with pytest.raises(service.QRCodeNotFoundError):
        service.read_qr_from_image(str(path))
