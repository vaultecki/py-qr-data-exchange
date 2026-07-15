# Copyright [2025] [ecki]
# SPDX-License-Identifier: Apache-2.0

import nacl.pwhash
import pytest

from app.crypt_utils import CryptoUtils


@pytest.fixture(scope="session", autouse=True)
def fast_argon2i():
    """
    Uses libsodium's minimum Argon2i cost parameters for the whole test session.

    Production code always uses MODERATE params, and every part in the current
    format runs its own full Argon2i derivation -- leaving MODERATE on would
    make a multi-part test suite take minutes instead of seconds for no benefit,
    since the KDF logic being tested is identical either way.
    """
    original_ops = CryptoUtils.DEFAULT_OPSLIMIT
    original_mem = CryptoUtils.DEFAULT_MEMLIMIT
    CryptoUtils.DEFAULT_OPSLIMIT = nacl.pwhash.argon2i.OPSLIMIT_MIN
    CryptoUtils.DEFAULT_MEMLIMIT = nacl.pwhash.argon2i.MEMLIMIT_MIN
    yield
    CryptoUtils.DEFAULT_OPSLIMIT = original_ops
    CryptoUtils.DEFAULT_MEMLIMIT = original_mem


@pytest.fixture
def password():
    return "test-password123"
