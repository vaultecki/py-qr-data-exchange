# Copyright [2025] [ecki]
# SPDX-License-Identifier: Apache-2.0

import argparse
import logging
import sys
import getpass
from pathlib import Path
from typing import List

from app import service

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool):
    """Configures logging based on verbose flag."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(levelname)s: %(message)s'
    )


def generate_qr(args):
    """Generates QR code(s) from a file."""
    input_file = Path(args.input)

    if not input_file.exists():
        logger.error(f"Input file not found: {input_file}")
        return 1

    # Request password
    password = args.password or getpass.getpass("Enter password: ")

    if not password:
        logger.error("Password cannot be empty.")
        return 1

    if len(password) > 20:
        logger.error("Password must be at most 20 characters.")
        return 1

    try:
        max_bytes = args.max_size or 2953
        result = service.generate_qr_from_file(
            str(input_file),
            password,
            max_bytes
        )

        qr_images, qr_texts = result

        # Check if single-part or multi-part
        if isinstance(qr_images, list):
            # Multi-part
            logger.info(f"File was split into {len(qr_images)} QR codes")

            if args.output:
                output_base = Path(args.output)
                output_dir = output_base.parent
                output_name = output_base.stem
                output_ext = output_base.suffix or '.png'
            else:
                output_dir = input_file.parent
                output_name = input_file.stem
                output_ext = '.png'

            saved_files = []
            for i, qr_image in enumerate(qr_images, 1):
                filename = f"{output_name}_part{i}_of_{len(qr_images)}{output_ext}"
                filepath = output_dir / filename
                qr_image.save(str(filepath))
                saved_files.append(filepath)
                logger.info(f"QR code {i}/{len(qr_images)} saved: {filepath}")

            # Optional: Save QR texts to file
            if args.save_texts:
                text_file = output_dir / f"{output_name}_qr_texts.txt"
                with open(text_file, 'w') as f:
                    for i, text in enumerate(qr_texts, 1):
                        f.write(f"# Part {i}/{len(qr_texts)}\n")
                        f.write(text + "\n\n")
                logger.info(f"QR texts saved: {text_file}")

        else:
            # Single-part
            output_file = Path(args.output) if args.output else input_file.with_suffix('.png')
            qr_images.save(str(output_file))
            logger.info(f"QR code successfully saved: {output_file}")

            if args.show_text:
                print(f"\nQR code text:\n{qr_texts}\n")

        return 0

    except service.FileTooLargeError as e:
        logger.error(str(e))
        return 1
    except Exception as e:
        logger.error(f"Error generating QR code: {e}")
        if args.verbose:
            logger.exception("Detailed error:")
        return 1


def read_qr(args):
    """Reads one or more QR codes from images."""
    input_files = args.input if isinstance(args.input, list) else [args.input]
    input_paths = [Path(f) for f in input_files]

    # Check if all files exist
    for input_file in input_paths:
        if not input_file.exists():
            logger.error(f"Input file not found: {input_file}")
            return 1

    try:
        if len(input_paths) == 1:
            qr_text = service.read_qr_from_image(str(input_paths[0]))
            qr_texts = [qr_text]
            logger.info("QR code successfully read.")
        else:
            qr_texts = service.read_multiple_qr_from_images([str(p) for p in input_paths])
            logger.info(f"{len(qr_texts)} QR codes successfully read.")

        # Check if multi-part
        is_multipart = service.is_multipart_qr(qr_texts[0])

        if is_multipart:
            part_num, total_parts = service.get_multipart_info(qr_texts[0])
            logger.info(f"Multi-part QR code detected (part {part_num}/{total_parts})")

            if len(qr_texts) < total_parts:
                logger.warning(f"Only {len(qr_texts)} of {total_parts} parts loaded!")

        if args.show_text:
            for i, text in enumerate(qr_texts, 1):
                print(f"\n--- QR Code {i} ---")
                print(text[:200] + "..." if len(text) > 200 else text)

        # If --output provided, decrypt directly
        if args.output:
            password = args.password or getpass.getpass("Enter password: ")

            if not password:
                logger.error("Password cannot be empty.")
                return 1

            try:
                from app import qr_data_class
                raw_data = service.decrypt_qr_data(qr_texts, password)
                output_file = Path(args.output)

                with open(output_file, 'wb') as f:
                    f.write(raw_data)

                logger.info(f"File successfully decrypted and saved: {output_file}")
                return 0

            except qr_data_class.DecryptionError as e:
                logger.error(f"Decryption failed: {e}")
                return 1

        return 0

    except service.QRCodeNotFoundError as e:
        logger.error(str(e))
        return 1
    except Exception as e:
        logger.error(f"Error reading QR code: {e}")
        if args.verbose:
            logger.exception("Detailed error:")
        return 1


def decrypt_text(args):
    """Decrypts one or more QR code texts directly."""
    if args.text_file:
        # Read texts from file
        text_file = Path(args.text_file)
        if not text_file.exists():
            logger.error(f"Text file not found: {text_file}")
            return 1

        with open(text_file, 'r') as f:
            content = f.read()

        # Parse multi-part text file (with # Part markers)
        qr_texts = []
        current_text = []
        for line in content.split('\n'):
            if line.startswith('# Part '):
                if current_text:
                    qr_texts.append(''.join(current_text).strip())
                    current_text = []
            elif line.strip():
                current_text.append(line)

        if current_text:
            qr_texts.append(''.join(current_text).strip())

        logger.info(f"{len(qr_texts)} QR texts loaded from file")
    else:
        # Single text
        qr_texts = [args.text]

    if not args.output:
        logger.error("Output file must be specified (--output).")
        return 1

    password = args.password or getpass.getpass("Enter password: ")

    if not password:
        logger.error("Password cannot be empty.")
        return 1

    try:
        from app import qr_data_class
        raw_data = service.decrypt_qr_data(qr_texts, password)
        output_file = Path(args.output)

        with open(output_file, 'wb') as f:
            f.write(raw_data)

        logger.info(f"File successfully decrypted and saved: {output_file}")
        return 0

    except qr_data_class.DecryptionError as e:
        logger.error(f"Decryption failed: {e}")
        return 1
    except Exception as e:
        logger.error(f"Error during decryption: {e}")
        if args.verbose:
            logger.exception("Detailed error:")
        return 1


def main():
    """Main function for CLI."""
    parser = argparse.ArgumentParser(
        description='QR Data Exchange - Encrypted file transfer via QR codes (Multi-Part Support)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate single-part QR code
  %(prog)s generate -i small_file.txt -o qrcode.png

  # Generate multi-part QR codes (large file)
  %(prog)s generate -i large_file.pdf

  # Read single QR code
  %(prog)s read -i qrcode.png -o restored.txt

  # Read multiple QR codes (multi-part)
  %(prog)s read -i qr_part1.png qr_part2.png qr_part3.png -o file.pdf

  # Decrypt text directly
  %(prog)s decrypt -t "BASE64STRING..." -o file.txt

  # Multi-part from text file
  %(prog)s decrypt --text-file qr_texts.txt -o file.pdf
        """
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output (debug mode)'
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Generate Command
    generate_parser = subparsers.add_parser(
        'generate',
        help='Generates QR code(s) from a file'
    )
    generate_parser.add_argument(
        '-i', '--input',
        required=True,
        help='Input file'
    )
    generate_parser.add_argument(
        '-o', '--output',
        help='Output file/prefix for QR code(s) (default: <input>_partX.png)'
    )
    generate_parser.add_argument(
        '-p', '--password',
        help='Password (will be requested interactively if not provided)'
    )
    generate_parser.add_argument(
        '--max-size',
        type=int,
        help='Maximum size per QR code in bytes (default: 2953)'
    )
    generate_parser.add_argument(
        '--show-text',
        action='store_true',
        help='Show QR code text'
    )
    generate_parser.add_argument(
        '--save-texts',
        action='store_true',
        help='Save QR texts to text file (for multi-part)'
    )

    # Read Command
    read_parser = subparsers.add_parser(
        'read',
        help='Reads one or more QR codes from images'
    )
    read_parser.add_argument(
        '-i', '--input',
        required=True,
        nargs='+',
        help='QR code image file(s)'
    )
    read_parser.add_argument(
        '-o', '--output',
        help='Output file (automatically decrypts if provided)'
    )
    read_parser.add_argument(
        '-p', '--password',
        help='Password (will be requested interactively if not provided)'
    )
    read_parser.add_argument(
        '--show-text',
        action='store_true',
        help='Show QR code texts'
    )

    # Decrypt Command
    decrypt_parser = subparsers.add_parser(
        'decrypt',
        help='Decrypts QR code text(s) directly'
    )
    text_group = decrypt_parser.add_mutually_exclusive_group(required=True)
    text_group.add_argument(
        '-t', '--text',
        help='QR code text (base64 encoded)'
    )
    text_group.add_argument(
        '--text-file',
        help='File with QR texts (for multi-part)'
    )
    decrypt_parser.add_argument(
        '-o', '--output',
        required=True,
        help='Output file'
    )
    decrypt_parser.add_argument(
        '-p', '--password',
        help='Password (will be requested interactively if not provided)'
    )

    args = parser.parse_args()

    setup_logging(args.verbose)

    if not args.command:
        parser.print_help()
        return 1

    # Execute the corresponding command
    if args.command == 'generate':
        return generate_qr(args)
    elif args.command == 'read':
        return read_qr(args)
    elif args.command == 'decrypt':
        return decrypt_text(args)

    return 0


if __name__ == '__main__':
    sys.exit(main())
