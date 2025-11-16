# Copyright [2025] [ecki]
# SPDX-License-Identifier: Apache-2.0

import logging
import msgpack
import base64
from typing import List, Tuple
from dataclasses import dataclass

from app import qr_data_class

logger = logging.getLogger(__name__)


@dataclass
class QrPart:
    """Represents a part of a multi-part QR code."""
    part_number: int
    total_parts: int
    data: str
    file_hash: str  # SHA256 hash of original file for validation


class MultiPartQrProcessor:
    """Processes files that need to be split into multiple QR codes."""

    # Reserve 200 bytes for metadata (part_number, total_parts, hash, msgpack overhead)
    METADATA_OVERHEAD = 200

    @staticmethod
    def calculate_file_hash(data: bytes) -> str:
        """Calculates SHA256 hash of data."""
        import hashlib
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def split_data(data: bytes, max_chunk_size: int) -> List[bytes]:
        """Splits data into chunks."""
        chunks = []
        for i in range(0, len(data), max_chunk_size):
            chunks.append(data[i:i + max_chunk_size])
        return chunks

    @staticmethod
    def serialize_multipart(raw_data: bytes, password: str, max_qr_bytes: int) -> List[str]:
        """
        Splits large files into multiple QR codes.

        Args:
            raw_data: The raw file data
            password: Password for encryption
            max_qr_bytes: Maximum size per QR code

        Returns:
            List of QR code strings
        """
        # Compress and encrypt the entire file once
        encrypted_string = qr_data_class.QrDataProcessor.serialize(raw_data, password)
        encrypted_bytes = base64.b64decode(encrypted_string)

        file_hash = MultiPartQrProcessor.calculate_file_hash(raw_data)

        data = msgpack.packb({'d': encrypted_bytes, 'h': file_hash})

        # Calculate maximum chunk size (minus overhead for metadata)
        # Since we use base64, we need to account for overhead
        test_overhead = msgpack.packb({'v': 2, 'p': 100, 't': 100, 'd': b' '})
        max_data_per_qr = max_qr_bytes - len(test_overhead)

        # Split encrypted data into chunks
        chunks = MultiPartQrProcessor.split_data(data, max_data_per_qr)
        total_parts = len(chunks)

        logger.info(f"File will be split into {total_parts} QR codes")

        qr_strings = []
        for i, chunk in enumerate(chunks, start=1):
            # Create metadata structure
            part_data = {
                'v': 2,  # Version
                'p': i,  # part_number
                't': total_parts,  # total_parts
                'd': chunk  # data chunk
            }

            # Pack and encode
            packed = msgpack.packb(part_data)
            qr_string = base64.b64encode(packed).decode('ascii')

            if len(packed) > max_qr_bytes:
                raise ValueError(
                    f"Part {i} is too large at {len(packed)} bytes. "
                    f"Maximum size: {max_qr_bytes} bytes"
                )

            qr_strings.append(qr_string)
            logger.debug(f"Part {i}/{total_parts} created ({len(qr_string)} bytes)")

        return qr_strings

    @staticmethod
    def deserialize_multipart(qr_strings: List[str], password: str) -> bytes:
        """
        Reassembles multiple QR code strings back to original data.

        Args:
            qr_strings: List of QR code strings (can be in any order)
            password: Password for decryption

        Returns:
            The restored raw data
        """
        if not qr_strings:
            raise ValueError("No QR codes provided")

        parts = []

        # Parse all parts
        for qr_string in qr_strings:
            try:
                packed = base64.b64decode(qr_string)
                part_data = msgpack.unpackb(packed)

                parts.append({
                    'part_number': part_data[b'p'],
                    'total_parts': part_data[b't'],
                    'data': part_data[b'd']
                })
            except Exception as e:
                raise ValueError(f"Error parsing QR code part: {e}")

        # Validation
        if not parts:
            raise ValueError("No valid parts found")

        total_parts = parts[0]['total_parts']

        # Check if all parts have same metadata
        for part in parts:
            if part['total_parts'] != total_parts:
                raise ValueError("Inconsistent total_parts in parts")

        # Check if all parts are present
        part_numbers = {part['part_number'] for part in parts}
        expected_parts = set(range(1, total_parts + 1))

        if part_numbers != expected_parts:
            missing = expected_parts - part_numbers
            raise ValueError(f"Missing parts: {sorted(missing)}")

        # Sort parts by part_number
        parts.sort(key=lambda x: x['part_number'])

        # Reassemble data
        data = b''.join(part['data'] for part in parts)
        unpacked_data = msgpack.unpackb(data)
        file_hash = unpacked_data[b'h']
        encrypted_bytes = unpacked_data[b'd']
        encrypted_string = encrypted_bytes.decode('ascii')

        logger.info(f"Assembling {total_parts} parts")

        # Decrypt and decompress
        raw_data = qr_data_class.QrDataProcessor.deserialize(encrypted_string, password)

        # Validate hash
        reconstructed_hash = MultiPartQrProcessor.calculate_file_hash(raw_data)
        if reconstructed_hash != file_hash:
            raise ValueError("Hash validation failed - data is corrupt")

        logger.info("File successfully restored and validated")

        return raw_data

    @staticmethod
    def is_multipart_qr(qr_string: str) -> bool:
        """Checks if a QR string is a multi-part QR."""
        try:
            packed = base64.b64decode(qr_string)
            part_data = msgpack.unpackb(packed)
            # Multi-part QRs have keys 'v', 'p', 't', 'h', 'd'
            return b'v' in part_data and b'p' in part_data and b't' in part_data
        except Exception:
            return False

    @staticmethod
    def get_part_info(qr_string: str) -> Tuple[int, int]:
        """
        Returns information about a multi-part QR.

        Returns:
            (part_number, total_parts)
        """
        try:
            packed = base64.b64decode(qr_string)
            part_data = msgpack.unpackb(packed)
            return part_data[b'p'], part_data[b't']
        except Exception as e:
            raise ValueError(f"Not a valid multi-part QR: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logger.info("Test Multi-Part QR Processor")

    # Test with small data
    password = "test123"
    test_data = b"Hello World! " * 1000  # ~13KB

    logger.info(f"Original data: {len(test_data)} bytes")

    # Split into very small QR codes (for testing only)
    qr_strings = MultiPartQrProcessor.serialize_multipart(test_data, password, max_qr_bytes=500)
    logger.info(f"Created {len(qr_strings)} QR codes")

    # Check if multi-part
    for i, qr in enumerate(qr_strings, 1):
        is_multi = MultiPartQrProcessor.is_multipart_qr(qr)
        part_num, total = MultiPartQrProcessor.get_part_info(qr)
        logger.info(f"QR {i}: Multi-Part={is_multi}, Part {part_num}/{total}")

    # Reassemble
    restored = MultiPartQrProcessor.deserialize_multipart(qr_strings, password)
    logger.info(f"Restored: {len(restored)} bytes")

    # Validation
    assert test_data == restored, "Data doesn't match!"
    logger.info("✓ Test successful!")
