# Copyright 2025 ecki
# SPDX-License-Identifier: Apache-2.0

import argparse
import getpass
import logging
import sys
from pathlib import Path

from app import qr_multi_part, service

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool):
    """Configures logging based on verbose flag."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(levelname)s: %(message)s'
    )


def generate_qr(args):
    """Generates QR code(s) from one or more files/directories."""
    input_paths = [Path(p) for p in args.input]

    for input_path in input_paths:
        if not input_path.exists():
            logger.error(f"Input path not found: {input_path}")
            return 1

    # Request password
    password = args.password or getpass.getpass("Enter password: ")

    if not password:
        logger.error("Password cannot be empty.")
        return 1

    try:
        max_bytes = args.max_size or 2953
        images, texts = service.generate_qr_from_paths(
            [str(p) for p in input_paths],
            password,
            max_bytes
        )

        if args.output:
            output_base = Path(args.output)
            output_dir = output_base.parent
            output_name = output_base.stem
            output_ext = output_base.suffix or '.png'
        else:
            output_dir = input_paths[0].parent
            output_name = input_paths[0].stem if len(input_paths) == 1 else "archive"
            output_ext = '.png'

        if len(images) == 1:
            filepath = output_dir / f"{output_name}{output_ext}"
            images[0].save(str(filepath))
            logger.info(f"QR code successfully saved: {filepath}")

            if args.show_text:
                print(f"\nQR code text:\n{texts[0]}\n")
        else:
            logger.info(f"Content was split into {len(images)} QR codes")

            for i, qr_image in enumerate(images, 1):
                filename = f"{output_name}_part{i}_of_{len(images)}{output_ext}"
                filepath = output_dir / filename
                qr_image.save(str(filepath))
                logger.info(f"QR code {i}/{len(images)} saved: {filepath}")

        # Optional: Save QR texts to file
        if args.save_texts:
            text_file = output_dir / f"{output_name}_qr_texts.txt"
            with text_file.open('w') as f:
                for i, text in enumerate(texts, 1):
                    f.write(f"# Part {i}/{len(texts)}\n")
                    f.write(text + "\n\n")
            logger.info(f"QR texts saved: {text_file}")

        return 0

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

        if args.show_text:
            for i, text in enumerate(qr_texts, 1):
                print(f"\n--- QR Code {i} ---")
                print(text[:200] + "..." if len(text) > 200 else text)

        # If --output provided, decrypt and extract directly
        if args.output:
            password = args.password or getpass.getpass("Enter password: ")

            if not password:
                logger.error("Password cannot be empty.")
                return 1

            try:
                extracted = service.decrypt_qr_data(qr_texts, password, args.output)
                logger.info(f"{len(extracted)} file(s) extracted to: {args.output}")
                for path in extracted:
                    logger.info(f"  {path}")
                return 0

            except qr_multi_part.DecryptionError as e:
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

        with text_file.open() as f:
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
        logger.error("Output directory must be specified (--output).")
        return 1

    password = args.password or getpass.getpass("Enter password: ")

    if not password:
        logger.error("Password cannot be empty.")
        return 1

    try:
        extracted = service.decrypt_qr_data(qr_texts, password, args.output)
        logger.info(f"{len(extracted)} file(s) extracted to: {args.output}")
        for path in extracted:
            logger.info(f"  {path}")
        return 0

    except qr_multi_part.DecryptionError as e:
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
  # Generate QR code(s) from a single file
  %(prog)s generate -i small_file.txt -o qrcode.png

  # Generate QR code(s) from multiple files and/or a folder
  %(prog)s generate -i file_a.txt file_b.pdf some_folder/

  # Read QR code(s) and extract to a folder
  %(prog)s read -i qrcode.png -o restored/

  # Read multiple QR codes (multi-part)
  %(prog)s read -i qr_part1.png qr_part2.png qr_part3.png -o restored/

  # Decrypt text directly
  %(prog)s decrypt -t "BASE64STRING..." -o restored/

  # Multi-part from text file
  %(prog)s decrypt --text-file qr_texts.txt -o restored/
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
        help='Generates QR code(s) from one or more files/directories'
    )
    generate_parser.add_argument(
        '-i', '--input',
        required=True,
        nargs='+',
        help='Input file(s) and/or directory(ies)'
    )
    generate_parser.add_argument(
        '-o', '--output',
        help='Output file/prefix for QR code(s) (default: derived from input)'
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
        help='Output directory (automatically decrypts and extracts here if provided).'
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
        help='Output directory to extract the recovered files/folders into.'
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
    if args.command == 'read':
        return read_qr(args)
    if args.command == 'decrypt':
        return decrypt_text(args)

    return 0


if __name__ == '__main__':
    sys.exit(main())
