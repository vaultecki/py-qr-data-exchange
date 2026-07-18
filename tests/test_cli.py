# Copyright 2025 ecki
# SPDX-License-Identifier: Apache-2.0

import sys

import pytest
from helpers import qr_reader_available

from app import cli


def run_cli(monkeypatch, args):
    monkeypatch.setattr(sys, "argv", ["app.cli"] + args)
    return cli.main()


def test_generate_accepts_long_password(tmp_path, monkeypatch):
    # No length cap: a long passphrase must work end-to-end, not just a short password.
    long_password = "correct horse battery staple " * 5
    f = tmp_path / "input.txt"
    f.write_text("long password roundtrip")
    out = tmp_path / "out.png"

    rc = run_cli(monkeypatch, [
        "generate", "-i", str(f), "-o", str(out), "-p", long_password, "--save-texts",
    ])
    assert rc == 0
    text_file = tmp_path / "out_qr_texts.txt"

    restored = tmp_path / "restored"
    rc = run_cli(monkeypatch, [
        "decrypt", "--text-file", str(text_file), "-o", str(restored), "-p", long_password,
    ])
    assert rc == 0
    assert (restored / "input.txt").read_text() == "long password roundtrip"


def test_generate_creates_single_qr_file(tmp_path, monkeypatch, password):
    f = tmp_path / "input.txt"
    f.write_text("cli test data")
    out = tmp_path / "out.png"

    rc = run_cli(monkeypatch, ["generate", "-i", str(f), "-o", str(out), "-p", password])

    assert rc == 0
    assert out.exists()


def test_generate_accepts_multiple_paths_and_a_folder(tmp_path, monkeypatch, password):
    file_a = tmp_path / "a.txt"
    file_b = tmp_path / "b.txt"
    folder = tmp_path / "sub"
    folder.mkdir()
    file_a.write_text("a")
    file_b.write_text("b")
    (folder / "c.txt").write_text("c")
    out = tmp_path / "out.png"

    rc = run_cli(monkeypatch, [
        "generate", "-i", str(file_a), str(file_b), str(folder),
        "-o", str(out), "-p", password,
    ])

    assert rc == 0
    assert list(tmp_path.glob("out*.png"))


def test_generate_rejects_missing_input_path(tmp_path, monkeypatch, password):
    rc = run_cli(monkeypatch, ["generate", "-i", str(tmp_path / "nope.txt"), "-p", password])
    assert rc == 1


def test_generate_then_decrypt_text_file_roundtrip(tmp_path, monkeypatch, password):
    file_a = tmp_path / "a.txt"
    file_b = tmp_path / "b.txt"
    file_a.write_text("first file")
    file_b.write_text("second file")
    out = tmp_path / "out.png"

    rc = run_cli(monkeypatch, [
        "generate", "-i", str(file_a), str(file_b),
        "-o", str(out), "-p", password, "--max-size", "600", "--save-texts",
    ])
    assert rc == 0

    text_file = tmp_path / "out_qr_texts.txt"
    assert text_file.exists()

    restored = tmp_path / "restored"
    rc = run_cli(monkeypatch, [
        "decrypt", "--text-file", str(text_file), "-o", str(restored), "-p", password,
    ])

    assert rc == 0
    assert (restored / "a.txt").read_text() == "first file"
    assert (restored / "b.txt").read_text() == "second file"


def test_decrypt_wrong_password_returns_error(tmp_path, monkeypatch, password):
    f = tmp_path / "a.txt"
    f.write_text("secret")
    out = tmp_path / "out.png"

    rc = run_cli(monkeypatch, [
        "generate", "-i", str(f), "-o", str(out), "-p", password, "--save-texts",
    ])
    assert rc == 0
    text_file = tmp_path / "out_qr_texts.txt"

    restored = tmp_path / "restored"
    rc = run_cli(monkeypatch, [
        "decrypt", "--text-file", str(text_file), "-o", str(restored), "-p", "wrong-password",
    ])

    assert rc == 1
    assert not restored.exists()


def test_decrypt_requires_output_argument(monkeypatch, password):
    # argparse itself enforces -o/--output as required for `decrypt` and exits(2)
    # before app logic ever runs.
    with pytest.raises(SystemExit):
        run_cli(monkeypatch, ["decrypt", "-t", "irrelevant", "-p", password])


@pytest.mark.skipif(
    not qr_reader_available(), reason="no QR reader backend (qreader/opencv) installed"
)
def test_generate_then_read_image_roundtrip(tmp_path, monkeypatch, password):
    f = tmp_path / "input.txt"
    f.write_text("read command roundtrip")
    out = tmp_path / "out.png"

    rc = run_cli(monkeypatch, ["generate", "-i", str(f), "-o", str(out), "-p", password])
    assert rc == 0

    restored = tmp_path / "restored"
    rc = run_cli(monkeypatch, ["read", "-i", str(out), "-o", str(restored), "-p", password])

    assert rc == 0
    assert (restored / "input.txt").read_text() == "read command roundtrip"
