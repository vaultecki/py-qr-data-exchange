# Copyright [2025] [ecki]
# SPDX-License-Identifier: Apache-2.0

import tkinter

import pytest

from app import main as main_module
from app.main import GuiClass
from helpers import pump_until


@pytest.fixture
def gui():
    try:
        instance = GuiClass()
    except tkinter.TclError as e:
        pytest.skip(f"no display available for Tk: {e}")
    instance.root.withdraw()
    yield instance
    instance.root.destroy()


@pytest.fixture(autouse=True)
def stub_messageboxes(monkeypatch):
    # Real modal dialogs would block waiting for a human to click OK.
    monkeypatch.setattr(main_module.messagebox, "showinfo", lambda *a, **k: None)
    monkeypatch.setattr(main_module.messagebox, "showerror", lambda *a, **k: None)
    monkeypatch.setattr(main_module.messagebox, "showwarning", lambda *a, **k: None)


def test_read_qr_button_was_removed():
    # Regression guard: the single-image "Read QR" button/handler was intentionally
    # removed once ReadWindow could add QR images itself.
    assert not hasattr(GuiClass, "click_button_read_qr")


def test_validate_inputs_requires_password(gui):
    assert gui._validate_inputs() is False


def test_validate_inputs_requires_selected_paths_for_generate(gui):
    gui.password_var.set("pw123")
    assert gui._validate_inputs() is False

    gui.selected_paths = ["/some/file.txt"]
    assert gui._validate_inputs() is True


def test_validate_inputs_read_flow_does_not_require_paths(gui):
    gui.password_var.set("pw123")
    assert gui._validate_inputs(check_filename=False) is True


def test_browse_files_updates_selection_and_display(gui, monkeypatch, tmp_path):
    file_a = tmp_path / "a.txt"
    file_b = tmp_path / "b.txt"
    file_a.write_text("a")
    file_b.write_text("b")
    monkeypatch.setattr(main_module.filedialog, "askopenfilenames", lambda **kwargs: (str(file_a), str(file_b)))

    gui.click_button_browse_files()

    assert gui.selected_paths == [str(file_a), str(file_b)]
    assert gui.entry_filename.get() == "2 items selected"


def test_browse_single_file_shows_full_path(gui, monkeypatch, tmp_path):
    file_a = tmp_path / "a.txt"
    file_a.write_text("a")
    monkeypatch.setattr(main_module.filedialog, "askopenfilenames", lambda **kwargs: (str(file_a),))

    gui.click_button_browse_files()

    assert gui.selected_paths == [str(file_a)]
    assert gui.entry_filename.get() == str(file_a)


def test_browse_folder_updates_selection_and_display(gui, monkeypatch, tmp_path):
    monkeypatch.setattr(main_module.filedialog, "askdirectory", lambda **kwargs: str(tmp_path))

    gui.click_button_browse_folder()

    assert gui.selected_paths == [str(tmp_path)]
    assert gui.entry_filename.get() == str(tmp_path)


def test_click_button_generate_opens_qr_window_on_success(gui, monkeypatch, tmp_path, password):
    f = tmp_path / "file.txt"
    f.write_text("gui generate test")
    gui.password_var.set(password)
    gui.selected_paths = [str(f)]

    opened = {}
    monkeypatch.setattr(
        main_module.extra_windows, "QrWindow",
        lambda master, images, texts: opened.update(master=master, images=images, texts=texts)
    )

    gui.click_button_generate()

    assert pump_until(gui.root, lambda: bool(opened))
    assert opened["master"] is gui.root
    assert len(opened["images"]) == len(opened["texts"]) == 1
    assert gui.button_generate.cget("state") == "normal"  # re-enabled after success


def test_click_button_generate_shows_error_on_failure(gui, monkeypatch, tmp_path, password):
    gui.password_var.set(password)
    gui.selected_paths = [str(tmp_path / "does-not-exist.txt")]

    shown = {}
    monkeypatch.setattr(main_module.messagebox, "showerror", lambda title, msg: shown.update(title=title, msg=msg))

    gui.click_button_generate()

    assert pump_until(gui.root, lambda: bool(shown))
    assert gui.button_generate.cget("state") == "normal"  # re-enabled after error too


def test_click_button_read_string_opens_read_window(gui, monkeypatch, password):
    gui.password_var.set(password)

    opened = {}
    monkeypatch.setattr(
        main_module.extra_windows, "ReadWindow",
        lambda master, pw: opened.update(master=master, password=pw)
    )

    gui.click_button_read_string()

    assert opened == {"master": gui.root, "password": password}
