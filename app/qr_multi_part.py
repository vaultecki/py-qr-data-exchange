# Copyright [2025] [ecki]
# SPDX-License-Identifier: Apache-2.0

import base64
import io
import logging
import lzma
import math
import os
import tarfile
from pathlib import Path
from typing import List, Sequence

import msgpack
import nacl.exceptions
import nacl.secret
import nacl.utils

from app import crypt_utils

logger = logging.getLogger(__name__)

# Aggressive preset for best compression ratio (this is done once per generation, not per part).
LZMA_PRESET = 9 | lzma.PRESET_EXTREME


class DecryptionError(Exception):
    """Raised when a part cannot be decrypted (wrong password or corrupted data)."""
    pass


class MultiPartQrProcessor:
    """
    Packs one or more files/directories into a set of QR-code strings and back.

    Every QR code is fully self-contained: its own random salt, its own
    independently derived Argon2i key, its own NaCl SecretBox encryption.
    The part/total-part bookkeeping ('v', 'p', 't', 'd') lives *inside* the
    ciphertext, not next to it, so nothing about the split is visible without
    the password. A single-file, single-part transfer is simply the case
    where t == 1 -- there's no separate "single-part" format anymore.
    """

    @staticmethod
    def _build_tar(paths: Sequence[str]) -> bytes:
        """Bundles the given files/directories into an in-memory tar archive."""
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w") as tar:
            for path in paths:
                p = Path(path)
                tar.add(str(p), arcname=p.name)
        return buffer.getvalue()

    @staticmethod
    def _max_chunk_size(max_qr_bytes: int) -> int:
        """
        Computes how many raw (compressed) bytes fit into a single QR code's
        'd' field, accounting for msgpack + NaCl + base64 overhead.

        Uses a throwaway key only to measure ciphertext size (SecretBox
        overhead only depends on key length, not its value) -- no Argon2i
        needed just for this estimate.
        """
        dummy_key = nacl.utils.random(nacl.secret.SecretBox.KEY_SIZE)
        dummy_salt = crypt_utils.CryptoUtils.generate_salt()
        # Worst-case placeholder p/t so msgpack's int encoding overhead isn't underestimated.
        placeholder_inner = msgpack.packb({"v": 1, "p": 999_999_999, "t": 999_999_999, "d": b""})
        dummy_encrypted = crypt_utils.CryptoUtils.encrypt(data=placeholder_inner, key=dummy_key)
        dummy_outer = msgpack.packb({"s": dummy_salt, "e": dummy_encrypted})
        overhead_b64_len = len(base64.b64encode(dummy_outer))

        budget = max_qr_bytes - overhead_b64_len
        if budget <= 0:
            raise ValueError(f"max_qr_bytes={max_qr_bytes} is too small to fit even an empty part")

        # base64 expands raw bytes ~4/3; leave a safety margin rather than
        # solving the exact byte boundary.
        max_chunk = math.floor(budget * 0.70)
        if max_chunk <= 0:
            raise ValueError(f"max_qr_bytes={max_qr_bytes} is too small to fit any data")
        return max_chunk

    @classmethod
    def serialize_paths(cls, paths: Sequence[str], password: str, max_qr_bytes: int) -> List[str]:
        """
        Packs the given files/directories into one or more QR code strings.

        Args:
            paths: Files and/or directories to bundle.
            password: Password for encryption.
            max_qr_bytes: Maximum size (base64 chars) per QR code.

        Returns:
            List of QR code strings (length 1 if everything fits in one QR code).
        """
        if not paths:
            raise ValueError("No input paths provided")

        tar_bytes = cls._build_tar(paths)
        compressed = lzma.compress(tar_bytes, preset=LZMA_PRESET)
        logger.info(f"Packed {len(paths)} path(s): {len(tar_bytes)} bytes tar -> {len(compressed)} bytes (lzma)")

        max_chunk = cls._max_chunk_size(max_qr_bytes)
        total_parts = max(1, math.ceil(len(compressed) / max_chunk))

        qr_strings = []
        for i in range(total_parts):
            chunk = compressed[i * max_chunk:(i + 1) * max_chunk]
            part_number = i + 1

            inner = msgpack.packb({"v": 1, "p": part_number, "t": total_parts, "d": chunk})

            salt = crypt_utils.CryptoUtils.generate_salt()
            key = crypt_utils.CryptoUtils.derive_key(password=password, salt=salt)
            encrypted = crypt_utils.CryptoUtils.encrypt(data=inner, key=key)
            outer = msgpack.packb({"s": salt, "e": encrypted})

            qr_string = base64.b64encode(outer).decode("ascii")
            if len(qr_string) > max_qr_bytes:
                raise ValueError(
                    f"Part {part_number} is too large at {len(qr_string)} bytes. "
                    f"Maximum size: {max_qr_bytes} bytes"
                )

            qr_strings.append(qr_string)
            logger.debug(f"Part {part_number}/{total_parts} created ({len(qr_string)} bytes)")

        logger.info(f"Created {total_parts} QR code(s)")
        return qr_strings

    @staticmethod
    def is_valid_qr_part(qr_string: str) -> bool:
        """Structural check only (no password needed): does this look like one of our QR codes?"""
        try:
            outer = msgpack.unpackb(base64.b64decode(qr_string))
            return isinstance(outer, dict) and "s" in outer and "e" in outer
        except Exception:
            return False

    @staticmethod
    def _decrypt_part(qr_string: str, password: str) -> dict:
        """Decrypts a single QR code string, returning its inner {'v', 'p', 't', 'd'} dict."""
        try:
            outer = msgpack.unpackb(base64.b64decode(qr_string))
            salt = outer["s"]
            key = crypt_utils.CryptoUtils.derive_key(password=password, salt=salt)
            inner_bytes = crypt_utils.CryptoUtils.decrypt(encrypted_data=outer["e"], key=key)
            return msgpack.unpackb(inner_bytes)
        except (msgpack.exceptions.UnpackException, KeyError, TypeError,
                nacl.exceptions.CryptoError, crypt_utils.CryptoError, ValueError) as e:
            raise DecryptionError("Decryption failed. Wrong password or corrupted data.") from e

    @classmethod
    def deserialize_to_bytes(cls, qr_texts: Sequence[str], password: str) -> bytes:
        """
        Reassembles QR code strings (in any order) back into the original tar bytes.

        Args:
            qr_texts: List of QR code strings.
            password: Password for decryption.

        Returns:
            The decompressed tar archive bytes.
        """
        if not qr_texts:
            raise ValueError("No QR codes provided")

        parts = []
        for qr_text in qr_texts:
            inner = cls._decrypt_part(qr_text, password)
            try:
                parts.append({
                    "part_number": inner["p"],
                    "total_parts": inner["t"],
                    "data": inner["d"],
                })
            except KeyError as e:
                raise DecryptionError(f"Malformed part data: missing {e}")

        total_parts = parts[0]["total_parts"]
        for part in parts:
            if part["total_parts"] != total_parts:
                raise ValueError("Inconsistent total_parts across parts")

        part_numbers = {part["part_number"] for part in parts}
        expected_parts = set(range(1, total_parts + 1))
        if part_numbers != expected_parts:
            missing = sorted(expected_parts - part_numbers)
            raise ValueError(f"Missing parts: {missing}")

        parts.sort(key=lambda part: part["part_number"])
        compressed = b"".join(part["data"] for part in parts)

        logger.info(f"Assembled {total_parts} part(s)")

        try:
            return lzma.decompress(compressed)
        except lzma.LZMAError as e:
            raise DecryptionError(
                "Decompression failed. Parts may be corrupted or come from different encryption runs."
            ) from e

    @staticmethod
    def extract_tar(tar_bytes: bytes, output_dir: str) -> List[Path]:
        """
        Safely extracts a tar archive into output_dir.

        Returns:
            List of extracted file paths (directories are created but not listed).
        """
        os.makedirs(output_dir, exist_ok=True)
        extracted = []
        with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r") as tar:
            members = tar.getmembers()
            if hasattr(tarfile, "data_filter"):
                # Python 3.12+: sandboxes extraction against path traversal, device files, etc.
                tar.extractall(output_dir, filter="data")
            else:
                base = Path(output_dir).resolve()
                for member in members:
                    member_path = (base / member.name).resolve()
                    if member_path != base and base not in member_path.parents:
                        raise ValueError(f"Unsafe path in archive: {member.name}")
                tar.extractall(output_dir)

            for member in members:
                if member.isfile():
                    extracted.append(Path(output_dir) / member.name)

        logger.info(f"Extracted {len(extracted)} file(s) to {output_dir}")
        return extracted


if __name__ == "__main__":
    import random
    import shutil
    import tempfile

    logging.basicConfig(level=logging.DEBUG)
    logger.info("Test MultiPartQrProcessor")

    password = "test123"
    workdir = tempfile.mkdtemp()
    try:
        # Single small file -> should fit in one QR code
        small_file = os.path.join(workdir, "small.txt")
        with open(small_file, "w") as f:
            f.write("hello world")

        qr_strings = MultiPartQrProcessor.serialize_paths([small_file], password, max_qr_bytes=2953)
        assert len(qr_strings) == 1, f"expected 1 part, got {len(qr_strings)}"
        assert all(MultiPartQrProcessor.is_valid_qr_part(q) for q in qr_strings)

        out_dir = os.path.join(workdir, "out_single")
        tar_bytes = MultiPartQrProcessor.deserialize_to_bytes(qr_strings, password)
        extracted = MultiPartQrProcessor.extract_tar(tar_bytes, out_dir)
        assert len(extracted) == 1
        with open(extracted[0]) as f:
            assert f.read() == "hello world"
        logger.info("Single small file: OK")

        # Large file -> multi-part, shuffled reassembly.
        # Kept deliberately small: every part runs its own full Argon2i
        # derivation (~0.3s each), so a part count in the single digits is
        # plenty to exercise the multi-part path without a slow self-test.
        large_file = os.path.join(workdir, "large.bin")
        with open(large_file, "wb") as f:
            f.write(os.urandom(2_500))

        qr_strings = MultiPartQrProcessor.serialize_paths([large_file], password, max_qr_bytes=800)
        assert len(qr_strings) > 1, "expected multiple parts for a large file"

        shuffled = qr_strings.copy()
        random.shuffle(shuffled)

        out_dir = os.path.join(workdir, "out_large")
        tar_bytes = MultiPartQrProcessor.deserialize_to_bytes(shuffled, password)
        extracted = MultiPartQrProcessor.extract_tar(tar_bytes, out_dir)
        assert len(extracted) == 1
        with open(large_file, "rb") as f_in, open(extracted[0], "rb") as f_out:
            assert f_in.read() == f_out.read()
        logger.info(f"Large file ({len(qr_strings)} parts, shuffled): OK")

        # Multiple files at once
        file_a = os.path.join(workdir, "a.txt")
        file_b = os.path.join(workdir, "b.txt")
        with open(file_a, "w") as f:
            f.write("file a")
        with open(file_b, "w") as f:
            f.write("file b")

        qr_strings = MultiPartQrProcessor.serialize_paths([file_a, file_b], password, max_qr_bytes=2953)
        out_dir = os.path.join(workdir, "out_multi")
        tar_bytes = MultiPartQrProcessor.deserialize_to_bytes(qr_strings, password)
        extracted = MultiPartQrProcessor.extract_tar(tar_bytes, out_dir)
        assert {p.name for p in extracted} == {"a.txt", "b.txt"}
        logger.info("Multiple files: OK")

        # A whole folder (nested structure)
        folder = os.path.join(workdir, "myfolder")
        os.makedirs(os.path.join(folder, "subdir"))
        with open(os.path.join(folder, "root.txt"), "w") as f:
            f.write("root file")
        with open(os.path.join(folder, "subdir", "nested.txt"), "w") as f:
            f.write("nested file")

        qr_strings = MultiPartQrProcessor.serialize_paths([folder], password, max_qr_bytes=2953)
        out_dir = os.path.join(workdir, "out_folder")
        tar_bytes = MultiPartQrProcessor.deserialize_to_bytes(qr_strings, password)
        extracted = MultiPartQrProcessor.extract_tar(tar_bytes, out_dir)
        extracted_relnames = {str(p.relative_to(out_dir)) for p in extracted}
        assert extracted_relnames == {
            os.path.join("myfolder", "root.txt"),
            os.path.join("myfolder", "subdir", "nested.txt"),
        }
        logger.info("Whole folder (nested): OK")

        # Missing parts should raise a clear error
        qr_strings = MultiPartQrProcessor.serialize_paths([large_file], password, max_qr_bytes=800)
        try:
            MultiPartQrProcessor.deserialize_to_bytes(qr_strings[:-1], password)
            assert False, "expected ValueError for missing parts"
        except ValueError as e:
            assert "Missing parts" in str(e)
        logger.info("Missing-parts detection: OK")

        # Wrong password should raise DecryptionError
        try:
            MultiPartQrProcessor.deserialize_to_bytes(qr_strings, "wrong password")
            assert False, "expected DecryptionError for wrong password"
        except DecryptionError:
            pass
        logger.info("Wrong-password detection: OK")

        logger.info("All MultiPartQrProcessor self-tests passed!")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
