# Copyright 2025 ecki
# SPDX-License-Identifier: Apache-2.0

import io
import os
import random
import tarfile
from pathlib import Path

import pytest

from app.qr_multi_part import DecryptionError, MultiPartQrProcessor


def test_single_small_file_fits_in_one_part(tmp_path, password):
    f = tmp_path / "small.txt"
    f.write_text("hello world")

    qr_strings = MultiPartQrProcessor.serialize_paths([str(f)], password, max_qr_bytes=2953)
    assert len(qr_strings) == 1
    assert MultiPartQrProcessor.is_valid_qr_part(qr_strings[0])

    tar_bytes = MultiPartQrProcessor.deserialize_to_bytes(qr_strings, password)
    extracted = MultiPartQrProcessor.extract_tar(tar_bytes, str(tmp_path / "out"))

    assert len(extracted) == 1
    assert extracted[0].read_text() == "hello world"


def test_is_valid_qr_part_rejects_garbage():
    assert MultiPartQrProcessor.is_valid_qr_part("not a real qr code") is False


def test_multi_part_reassembles_in_any_order(tmp_path, password):
    f = tmp_path / "large.bin"
    f.write_bytes(os.urandom(2_500))

    qr_strings = MultiPartQrProcessor.serialize_paths([str(f)], password, max_qr_bytes=800)
    assert len(qr_strings) > 1

    shuffled = qr_strings.copy()
    random.shuffle(shuffled)

    tar_bytes = MultiPartQrProcessor.deserialize_to_bytes(shuffled, password)
    extracted = MultiPartQrProcessor.extract_tar(tar_bytes, str(tmp_path / "out"))

    assert len(extracted) == 1
    assert extracted[0].read_bytes() == f.read_bytes()


def test_multiple_files_are_bundled_together(tmp_path, password):
    file_a = tmp_path / "a.txt"
    file_b = tmp_path / "b.txt"
    file_a.write_text("file a")
    file_b.write_text("file b")

    qr_strings = MultiPartQrProcessor.serialize_paths(
        [str(file_a), str(file_b)], password, max_qr_bytes=2953
    )

    tar_bytes = MultiPartQrProcessor.deserialize_to_bytes(qr_strings, password)
    extracted = MultiPartQrProcessor.extract_tar(tar_bytes, str(tmp_path / "out"))

    assert {p.name for p in extracted} == {"a.txt", "b.txt"}


def test_whole_folder_preserves_nested_structure(tmp_path, password):
    folder = tmp_path / "myfolder"
    (folder / "subdir").mkdir(parents=True)
    (folder / "root.txt").write_text("root file")
    (folder / "subdir" / "nested.txt").write_text("nested file")

    qr_strings = MultiPartQrProcessor.serialize_paths([str(folder)], password, max_qr_bytes=2953)

    out_dir = tmp_path / "out"
    tar_bytes = MultiPartQrProcessor.deserialize_to_bytes(qr_strings, password)
    extracted = MultiPartQrProcessor.extract_tar(tar_bytes, str(out_dir))

    relnames = {p.relative_to(out_dir) for p in extracted}
    assert relnames == {
        Path("myfolder/root.txt"),
        Path("myfolder/subdir/nested.txt"),
    }


def test_missing_parts_lists_missing_part_numbers(tmp_path, password):
    f = tmp_path / "large.bin"
    f.write_bytes(os.urandom(2_500))
    qr_strings = MultiPartQrProcessor.serialize_paths([str(f)], password, max_qr_bytes=800)
    assert len(qr_strings) > 2

    with pytest.raises(ValueError, match="Missing parts"):
        MultiPartQrProcessor.deserialize_to_bytes(qr_strings[:-1], password)


def test_inconsistent_total_parts_raises(tmp_path, password):
    small = tmp_path / "small.txt"
    small.write_text("x")
    large = tmp_path / "large.bin"
    large.write_bytes(os.urandom(2_500))

    small_parts = MultiPartQrProcessor.serialize_paths([str(small)], password, max_qr_bytes=2953)
    large_parts = MultiPartQrProcessor.serialize_paths([str(large)], password, max_qr_bytes=800)
    assert len(large_parts) > 1

    with pytest.raises(ValueError, match="Inconsistent total_parts"):
        MultiPartQrProcessor.deserialize_to_bytes([small_parts[0], large_parts[0]], password)


def test_wrong_password_raises_decryption_error(tmp_path, password):
    f = tmp_path / "small.txt"
    f.write_text("secret")
    qr_strings = MultiPartQrProcessor.serialize_paths([str(f)], password, max_qr_bytes=2953)

    with pytest.raises(DecryptionError):
        MultiPartQrProcessor.deserialize_to_bytes(qr_strings, "wrong password")


def test_corrupted_qr_text_raises_decryption_error(tmp_path, password):
    f = tmp_path / "small.txt"
    f.write_text("secret")
    qr_strings = MultiPartQrProcessor.serialize_paths([str(f)], password, max_qr_bytes=2953)

    corrupted = qr_strings[0][:-4] + "abcd"
    with pytest.raises(DecryptionError):
        MultiPartQrProcessor.deserialize_to_bytes([corrupted], password)


def test_extract_tar_rejects_path_traversal(tmp_path):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as tar:
        payload = b"pwned"
        info = tarfile.TarInfo(name="../evil.txt")
        info.size = len(payload)
        tar.addfile(info, io.BytesIO(payload))

    out_dir = tmp_path / "out"
    # ValueError on Python < 3.12 (manual check); tarfile.FilterError (3.12+ data filter) otherwise.
    expected_errors = (ValueError, getattr(tarfile, "FilterError", ValueError))
    with pytest.raises(expected_errors):
        MultiPartQrProcessor.extract_tar(buffer.getvalue(), str(out_dir))

    assert not (tmp_path / "evil.txt").exists()
