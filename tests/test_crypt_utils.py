# Copyright 2025 ecki
# SPDX-License-Identifier: Apache-2.0

import nacl.pwhash
import nacl.secret
import pytest

from app.crypt_utils import CryptoError, CryptoUtils


def test_generate_salt_has_expected_length():
    salt = CryptoUtils.generate_salt()
    assert len(salt) == nacl.pwhash.argon2i.SALTBYTES


def test_generate_salt_is_random():
    assert CryptoUtils.generate_salt() != CryptoUtils.generate_salt()


def test_derive_key_has_expected_length(password):
    key = CryptoUtils.derive_key(password, CryptoUtils.generate_salt())
    assert len(key) == nacl.secret.SecretBox.KEY_SIZE


def test_derive_key_is_deterministic_for_same_salt(password):
    salt = CryptoUtils.generate_salt()
    assert CryptoUtils.derive_key(password, salt) == CryptoUtils.derive_key(password, salt)


def test_derive_key_differs_per_salt(password):
    key1 = CryptoUtils.derive_key(password, CryptoUtils.generate_salt())
    key2 = CryptoUtils.derive_key(password, CryptoUtils.generate_salt())
    assert key1 != key2


def test_derive_key_rejects_empty_password():
    with pytest.raises(ValueError):
        CryptoUtils.derive_key("", CryptoUtils.generate_salt())


def test_derive_key_rejects_wrong_salt_length(password):
    with pytest.raises(ValueError):
        CryptoUtils.derive_key(password, b"too short")


def test_encrypt_decrypt_roundtrip(password):
    key = CryptoUtils.derive_key(password, CryptoUtils.generate_salt())
    data = b"some secret bytes"

    encrypted = CryptoUtils.encrypt(data, key)

    assert encrypted != data
    assert CryptoUtils.decrypt(encrypted, key) == data


def test_decrypt_with_wrong_key_raises_crypto_error(password):
    key1 = CryptoUtils.derive_key(password, CryptoUtils.generate_salt())
    key2 = CryptoUtils.derive_key(password, CryptoUtils.generate_salt())
    encrypted = CryptoUtils.encrypt(b"data", key1)

    with pytest.raises(CryptoError):
        CryptoUtils.decrypt(encrypted, key2)


def test_encrypt_rejects_wrong_key_length():
    with pytest.raises(ValueError):
        CryptoUtils.encrypt(b"data", b"too short")


def test_base64_roundtrip():
    data = b"\x00\x01binary\xffdata"
    assert CryptoUtils.decode_base64(CryptoUtils.encode_base64(data)) == data


def test_encrypt_and_encode_decode_and_decrypt_roundtrip(password):
    key = CryptoUtils.derive_key(password, CryptoUtils.generate_salt())
    data = b"round trip me"

    b64 = CryptoUtils.encrypt_and_encode(data, key)

    assert CryptoUtils.decode_and_decrypt(b64, key) == data
