# Copyright [2025] [ecki]
# SPDX-License-Identifier: Apache-2.0

import base64
import logging
from typing import Optional

import nacl.secret
import nacl.utils
import nacl.pwhash
import nacl.exceptions

logger = logging.getLogger(__name__)


class CryptoError(Exception):
    """Allgemeine Crypto-Fehler, die von diesem Modul geworfen werden."""
    pass


class CryptoUtils:
    # Default security parameters (sane defaults)
    DEFAULT_OPSLIMIT = nacl.pwhash.argon2i.OPSLIMIT_MODERATE
    DEFAULT_MEMLIMIT = nacl.pwhash.argon2i.MEMLIMIT_MODERATE

    @staticmethod
    def generate_salt() -> bytes:
        """
        Erzeuge ein sicheres Salt mit der Länge, die Argon2i erwartet.
        Returns:
            salt (bytes): salt mit Länge nacl.pwhash.argon2i.SALTBYTES
        """
        logger.debug("generate salt")
        return nacl.utils.random(nacl.pwhash.argon2i.SALTBYTES)

    @staticmethod
    def validate_salt(salt: bytes) -> None:
        if not isinstance(salt, (bytes, bytearray)):
            raise ValueError("Salt muss vom Typ 'bytes' sein.")
        if len(salt) != nacl.pwhash.argon2i.SALTBYTES:
            raise ValueError(f"Salt muss {nacl.pwhash.argon2i.SALTBYTES} Bytes lang sein.")

    @staticmethod
    def derive_key(password: str, salt: bytes,
                   opslimit: Optional[int] = None,
                   memlimit: Optional[int] = None) -> bytes:
        """
        Leitet einen symmetrischen Schlüssel aus einem Passwort und Salt ab.

        Args:
            password: Das Nutzer-Passwort als str.
            salt: Salt (bytes) mit Länge nacl.pwhash.argon2i.SALTBYTES.
            opslimit: Optional. Argon2 opslimit (tuning).
            memlimit: Optional. Argon2 memlimit (tuning).

        Returns:
            key (bytes): Schlüssel in Länge nacl.secret.SecretBox.KEY_SIZE

        Raises:
            ValueError: bei falschen Argumenten.
            CryptoError: bei Fehlern des KDF.
        """

        logger.debug("derive key begin")
        if not isinstance(password, str) or not password:
            raise ValueError("Password must be a non-empty string.")

        CryptoUtils.validate_salt(salt)

        ops = opslimit if opslimit is not None else CryptoUtils.DEFAULT_OPSLIMIT
        mem = memlimit if memlimit is not None else CryptoUtils.DEFAULT_MEMLIMIT

        password_bytes = password.encode("utf-8")
        try:
            kdf = nacl.pwhash.argon2i.kdf
            key = kdf(
                nacl.secret.SecretBox.KEY_SIZE,
                password_bytes,
                salt,
                opslimit=ops,
                memlimit=mem
            )
            logger.debug("derive key success")
            return key
        except Exception as e:
            logger.exception("derive_key failed")
            raise CryptoError(f"Key derivation failed: {e}") from e
        finally:
            # attempt to reduce lifetime of sensitive data
            try:
                # overwrite if mutable
                if isinstance(password_bytes, bytearray):
                    for i in range(len(password_bytes)):
                        password_bytes[i] = 0
            except Exception:
                pass
            try:
                del password_bytes
            except Exception:
                pass

    @staticmethod
    def encrypt(data: bytes, key: bytes) -> bytes:
        """
        Verschlüsselt rohe Bytes mit secretbox(key).

        Args:
            data: Rohbytes (z. B. aus Datei)
            key: Schlüssel, wie von derive_key erzeugt.

        Returns:
            bytes: die von SecretBox erzeugte verschlüsselte Nachricht (nonce + ciphertext)

        Raises:
            ValueError, CryptoError
        """
        logger.debug("encrypt data")
        if not isinstance(data, (bytes, bytearray)):
            raise ValueError("data must be bytes-like")
        if not isinstance(key, (bytes, bytearray)) or len(key) != nacl.secret.SecretBox.KEY_SIZE:
            raise ValueError("invalid key length")

        try:
            box = nacl.secret.SecretBox(key)
            encrypted = box.encrypt(bytes(data))
            logger.debug("encrypt success")
            return encrypted
        except Exception as e:
            logger.exception("encrypt failed")
            raise CryptoError(f"Encryption failed: {e}") from e

    @staticmethod
    def decrypt(encrypted_data: bytes, key: bytes) -> bytes:
        """
        Entschlüsselt Daten, die mit `encrypt` erzeugt wurden.

        Args:
            encrypted_data: bytes (nonce + ciphertext)
            key: Schlüssel

        Returns:
            bytes: entschlüsselte rohe Bytes

        Raises:
            CryptoError bei Problemen (inkl. WrongKey)
        """
        logger.debug("decrypt data")
        if not isinstance(encrypted_data, (bytes, bytearray)):
            raise ValueError("encrypted_data must be bytes-like")
        if not isinstance(key, (bytes, bytearray)) or len(key) != nacl.secret.SecretBox.KEY_SIZE:
            raise ValueError("invalid key length")

        try:
            box = nacl.secret.SecretBox(key)
            plaintext = box.decrypt(bytes(encrypted_data))
            logger.debug("decrypt success")
            return plaintext
        except nacl.exceptions.CryptoError as e:
            logger.warning("decrypt failed - crypto error")
            raise CryptoError("Decryption failed (bad key or corrupted data).") from e
        except Exception as e:
            logger.exception("decrypt failed - unexpected")
            raise CryptoError(f"Decryption failed: {e}") from e

    @staticmethod
    def encode_base64(data: bytes) -> str:
        """
        Encodiert bytes -> base64 ascii string.
        """
        if not isinstance(data, (bytes, bytearray)):
            raise ValueError("data must be bytes")
        return base64.b64encode(data).decode("ascii")

    @staticmethod
    def decode_base64(data_str: str) -> bytes:
        """
        Dekodiert base64 string -> bytes.
        """
        if not isinstance(data_str, str):
            raise ValueError("data_str must be str")
        return base64.b64decode(data_str)

    @staticmethod
    def encrypt_and_encode(data: bytes, key: bytes) -> str:
        """
        Combines encrypt() and base64 encoding in one call.
        Returns ASCII-safe base64 string.
        """
        enc = CryptoUtils.encrypt(data, key)
        return CryptoUtils.encode_base64(enc)

    @staticmethod
    def decode_and_decrypt(b64_str: str, key: bytes) -> bytes:
        enc = CryptoUtils.decode_base64(b64_str)
        return CryptoUtils.decrypt(enc, key)


if __name__ == "__main__":
    # Quick demo (not a full test)
    import logging
    logging.basicConfig(level=logging.DEBUG)

    password = "moin"
    data = b"Das sind geheime bytes."

    salt = CryptoUtils.generate_salt()
    logger.info(f"salt len: {len(salt)}")

    key = CryptoUtils.derive_key(password=password, salt=salt)
    logger.info(f"derived key len: {len(key)}")

    enc = CryptoUtils.encrypt(data, key)
    logger.info(f"encrypted len: {len(enc)}")

    b64 = CryptoUtils.encode_base64(enc)
    logger.info(f"b64 len: {len(b64)}")

    dec = CryptoUtils.decode_base64(b64)
    plaintext = CryptoUtils.decrypt(dec, key)
    logger.info(f"plaintext: {plaintext}")
