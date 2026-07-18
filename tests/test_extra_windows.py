# Copyright 2025 ecki
# SPDX-License-Identifier: Apache-2.0

import os
import tkinter

import pytest
from helpers import pump_until

from app import extra_windows, service


@pytest.fixture
def tk_root():
    try:
        root = tkinter.Tk()
    except tkinter.TclError as e:
        pytest.skip(f"no display available for Tk: {e}")
    root.withdraw()
    yield root
    root.destroy()


@pytest.fixture(autouse=True)
def stub_messageboxes(monkeypatch):
    # Real modal dialogs would block waiting for a human to click OK.
    monkeypatch.setattr(extra_windows.messagebox, "showinfo", lambda *a, **k: None)
    monkeypatch.setattr(extra_windows.messagebox, "showerror", lambda *a, **k: None)
    monkeypatch.setattr(extra_windows.messagebox, "showwarning", lambda *a, **k: None)


def _multi_part_texts(tmp_path, password, size=2500, max_qr_bytes=800):
    f = tmp_path / "large.bin"
    f.write_bytes(os.urandom(size))
    _, texts = service.generate_qr_from_paths([str(f)], password, max_bytes=max_qr_bytes)
    assert len(texts) > 1
    return texts


def test_try_add_part_tracks_progress_and_gates_decrypt_button(tk_root, tmp_path, password):
    texts = _multi_part_texts(tmp_path, password)
    rw = extra_windows.ReadWindow(tk_root, password)

    for text in texts[:-1]:
        assert rw._try_add_part(text) == ""
    rw._update_status()
    assert rw.decrypt_button.cget("state") == "disabled"
    assert rw.status_label.cget("text") == f"{len(texts) - 1}/{len(texts)} parts loaded"

    assert rw._try_add_part(texts[-1]) == ""
    rw._update_status()
    assert rw.decrypt_button.cget("state") == "normal"
    assert rw.status_label.cget("text") == f"{len(texts)}/{len(texts)} parts loaded"

    rw.destroy()


def test_try_add_part_ignores_exact_duplicate(tk_root, tmp_path, password):
    texts = _multi_part_texts(tmp_path, password)
    rw = extra_windows.ReadWindow(tk_root, password)

    assert rw._try_add_part(texts[0]) == ""
    assert rw._try_add_part(texts[0]) == ""  # re-adding the same part is a silent no-op
    assert len(rw.parts_by_number) == 1

    rw.destroy()


def test_try_add_part_rejects_same_number_different_content(tk_root, tmp_path, password):
    # Two independent single-part (t=1, p=1) transfers -- same numbering, unrelated content.
    file_a = tmp_path / "a.txt"
    file_a.write_text("content A")
    file_b = tmp_path / "b.txt"
    file_b.write_text("content B, totally different")

    _, texts_a = service.generate_qr_from_paths([str(file_a)], password, max_bytes=2953)
    _, texts_b = service.generate_qr_from_paths([str(file_b)], password, max_bytes=2953)
    assert texts_a[0] != texts_b[0]

    rw = extra_windows.ReadWindow(tk_root, password)
    assert rw._try_add_part(texts_a[0]) == ""

    error = rw._try_add_part(texts_b[0])
    assert error
    assert "different transfer" in error
    assert len(rw.parts_by_number) == 1  # the conflicting part must not silently overwrite/merge

    rw.destroy()


def test_try_add_part_rejects_inconsistent_total_parts(tk_root, tmp_path, password):
    small = tmp_path / "small.txt"
    small.write_text("x")
    large = tmp_path / "large.bin"
    large.write_bytes(os.urandom(2500))

    _, small_texts = service.generate_qr_from_paths([str(small)], password, max_bytes=2953)
    _, large_texts = service.generate_qr_from_paths([str(large)], password, max_bytes=800)
    assert len(large_texts) > 1

    rw = extra_windows.ReadWindow(tk_root, password)
    assert rw._try_add_part(small_texts[0]) == ""

    error = rw._try_add_part(large_texts[0])
    assert "different transfer" in error

    rw.destroy()


def test_try_add_part_rejects_wrong_password_and_garbage(tk_root, tmp_path, password):
    f = tmp_path / "file.txt"
    f.write_text("secret")
    _, texts = service.generate_qr_from_paths([str(f)], password, max_bytes=2953)

    rw = extra_windows.ReadWindow(tk_root, "wrong-password")
    assert rw._try_add_part(texts[0]) != ""
    assert rw._try_add_part("not a real qr string") != ""

    rw.destroy()


def test_read_qr_text_from_file_handles_txt_files(tmp_path, password):
    f = tmp_path / "file.txt"
    f.write_text("save-all roundtrip")
    _, texts = service.generate_qr_from_paths([str(f)], password, max_bytes=2953)

    txt_path = tmp_path / "qr_part_1_of_1.txt"
    txt_path.write_text(texts[0])

    assert extra_windows.ReadWindow._read_qr_text_from_file(str(txt_path)) == texts[0]


def test_clear_qr_list_resets_state(tk_root, tmp_path, password):
    texts = _multi_part_texts(tmp_path, password)
    rw = extra_windows.ReadWindow(tk_root, password)
    rw._try_add_part(texts[0])
    rw._update_status()
    assert rw.parts_by_number

    rw.clear_qr_list()
    assert rw.parts_by_number == {}
    assert rw.total_parts is None
    assert rw.decrypt_button.cget("state") == "disabled"
    assert rw.status_label.cget("text") == "0 parts loaded"

    rw.destroy()


def test_click_add_text_runs_in_background_and_updates_ui(tk_root, tmp_path, password):
    texts = _multi_part_texts(tmp_path, password)
    rw = extra_windows.ReadWindow(tk_root, password)

    rw.text_field.insert(0, texts[0])
    rw.click_add_text()
    assert rw.add_text_button.cget("state") == "disabled"  # busy immediately after click

    assert pump_until(tk_root, lambda: rw.add_text_button.cget("state") == "normal")
    assert rw.status_label.cget("text") == f"1/{len(texts)} parts loaded"
    assert rw.text_field.get() == ""  # field is cleared after adding

    rw.destroy()


def test_add_qr_image_reads_txt_files_via_file_dialog(tk_root, tmp_path, monkeypatch, password):
    texts = _multi_part_texts(tmp_path, password)

    txt_paths = []
    for i, text in enumerate(texts, 1):
        p = tmp_path / f"qr_part_{i}_of_{len(texts)}.txt"
        p.write_text(text)
        txt_paths.append(str(p))

    monkeypatch.setattr(
        extra_windows.filedialog, "askopenfilenames", lambda **kwargs: tuple(txt_paths)
    )

    rw = extra_windows.ReadWindow(tk_root, password)
    rw.add_qr_image()
    assert rw.add_files_button.cget("state") == "disabled"

    assert pump_until(tk_root, lambda: rw.add_files_button.cget("state") == "normal")
    assert rw.status_label.cget("text") == f"{len(texts)}/{len(texts)} parts loaded"
    assert rw.decrypt_button.cget("state") == "normal"

    rw.destroy()
