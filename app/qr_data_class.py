# Copyright [2025] [ecki]
# SPDX-License-Identifier: Apache-2.0

import base64
import logging
import msgpack
import nacl.exceptions
import pyzstd

from app import crypt_utils

logger = logging.getLogger(__name__)


class QrDataProcessor:
    @staticmethod
    def serialize(raw_data: bytes, password: str) -> str:
        """Nimmt Rohdaten und ein Passwort und gibt den QR-String zurück."""
        salt = crypt_utils.CryptoUtils.generate_salt()
        key = crypt_utils.CryptoUtils.derive_key(password=password, salt=salt)

        compressed_dat = pyzstd.compress(raw_data, 16)
        enc_msg = crypt_utils.CryptoUtils.encrypt(data=compressed_dat, key=key)

        packed_data = msgpack.packb([salt, enc_msg])
        return base64.b64encode(packed_data).decode("ascii")

    @staticmethod
    def deserialize(input_string: str, password: str) -> bytes:
        """Nimmt einen QR-String und ein Passwort und gibt die Rohdaten zurück."""
        try:
            unpacked_data = msgpack.unpackb(base64.b64decode(input_string))
            salt = unpacked_data[0]

            key = crypt_utils.CryptoUtils.derive_key(password=password, salt=salt)
            dec_msg = crypt_utils.CryptoUtils.decrypt(encrypted_data=unpacked_data[1],
                                                      key=key)
            return pyzstd.decompress(dec_msg)
        except (msgpack.UnpackException, nacl.exceptions.CryptoError, ValueError) as e:
            # Fange spezifische Fehler ab und werfe eine eigene, klare Exception
            raise DecryptionError("Entschlüsselung fehlgeschlagen. Falsches Passwort oder korrupte Daten.") from e

class DecryptionError(Exception):
    pass

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logger.info("main of file qr_data_class")
    password = "test"
    raw_data = b"moin"
    logger.debug(f"raw data is: {raw_data}")
    qr_data = QrDataProcessor.serialize(raw_data, password)
    logger.debug(f"packed and encrypted data: {qr_data}")

    input_str = qr_data
    qr_data_read = QrDataProcessor.deserialize(input_str, password)
    logger.debug(f"unpacked and decrypted data: {qr_data_read}")
