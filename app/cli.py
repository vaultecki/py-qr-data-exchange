# Copyright [2025] [ecki]
# SPDX-License-Identifier: Apache-2.0

import argparse
import logging
import sys
import getpass
from pathlib import Path

from app import service
from app import qr_data_class

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool):
    """Konfiguriert das Logging basierend auf Verbose-Flag."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(levelname)s: %(message)s'
    )


def generate_qr(args):
    """Generiert einen QR-Code aus einer Datei."""
    input_file = Path(args.input)

    if not input_file.exists():
        logger.error(f"Eingabedatei nicht gefunden: {input_file}")
        return 1

    # Passwort abfragen
    password = args.password or getpass.getpass("Passwort eingeben: ")

    if not password:
        logger.error("Passwort darf nicht leer sein.")
        return 1

    if len(password) > 20:
        logger.error("Passwort darf maximal 20 Zeichen lang sein.")
        return 1

    try:
        max_bytes = args.max_size or 2953
        qr_image, qr_text = service.generate_qr_from_file(
            str(input_file),
            password,
            max_bytes
        )

        # QR-Code speichern
        output_file = Path(args.output) if args.output else input_file.with_suffix('.png')
        qr_image.save(str(output_file))
        logger.info(f"QR-Code erfolgreich gespeichert: {output_file}")

        # Optional: QR-Text ausgeben
        if args.show_text:
            print(f"\nQR-Code Text:\n{qr_text}\n")

        return 0

    except service.FileTooLargeError as e:
        logger.error(str(e))
        return 1
    except Exception as e:
        logger.error(f"Fehler beim Generieren des QR-Codes: {e}")
        return 1


def read_qr(args):
    """Liest einen QR-Code aus einem Bild."""
    input_file = Path(args.input)

    if not input_file.exists():
        logger.error(f"Eingabedatei nicht gefunden: {input_file}")
        return 1

    try:
        qr_text = service.read_qr_from_image(str(input_file))
        logger.info("QR-Code erfolgreich gelesen.")

        if args.show_text:
            print(f"\nQR-Code Text:\n{qr_text}\n")

        # Wenn --output angegeben, direkt entschlüsseln
        if args.output:
            password = args.password or getpass.getpass("Passwort eingeben: ")

            if not password:
                logger.error("Passwort darf nicht leer sein.")
                return 1

            try:
                raw_data = qr_data_class.QrDataProcessor.deserialize(qr_text, password)
                output_file = Path(args.output)

                with open(output_file, 'wb') as f:
                    f.write(raw_data)

                logger.info(f"Datei erfolgreich entschlüsselt und gespeichert: {output_file}")
                return 0

            except qr_data_class.DecryptionError as e:
                logger.error(f"Entschlüsselung fehlgeschlagen: {e}")
                return 1

        return 0

    except service.QRCodeNotFoundError as e:
        logger.error(str(e))
        return 1
    except Exception as e:
        logger.error(f"Fehler beim Lesen des QR-Codes: {e}")
        return 1


def decrypt_text(args):
    """Entschlüsselt einen QR-Code-Text direkt."""
    qr_text = args.text

    if not args.output:
        logger.error("Ausgabedatei muss angegeben werden (--output).")
        return 1

    password = args.password or getpass.getpass("Passwort eingeben: ")

    if not password:
        logger.error("Passwort darf nicht leer sein.")
        return 1

    try:
        raw_data = qr_data_class.QrDataProcessor.deserialize(qr_text, password)
        output_file = Path(args.output)

        with open(output_file, 'wb') as f:
            f.write(raw_data)

        logger.info(f"Datei erfolgreich entschlüsselt und gespeichert: {output_file}")
        return 0

    except qr_data_class.DecryptionError as e:
        logger.error(f"Entschlüsselung fehlgeschlagen: {e}")
        return 1
    except Exception as e:
        logger.error(f"Fehler beim Entschlüsseln: {e}")
        return 1


def main():
    """Hauptfunktion für die CLI."""
    parser = argparse.ArgumentParser(
        description='QR Data Exchange - Verschlüsselte Dateiübertragung via QR-Codes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  %(prog)s generate -i datei.txt -o qrcode.png
  %(prog)s read -i qrcode.png -o wiederhergestellt.txt
  %(prog)s decrypt -t "BASE64STRING..." -o datei.txt
        """
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Ausführliche Ausgabe (Debug-Modus)'
    )

    subparsers = parser.add_subparsers(dest='command', help='Verfügbare Befehle')

    # Generate Command
    generate_parser = subparsers.add_parser(
        'generate',
        help='Generiert einen QR-Code aus einer Datei'
    )
    generate_parser.add_argument(
        '-i', '--input',
        required=True,
        help='Eingabedatei'
    )
    generate_parser.add_argument(
        '-o', '--output',
        help='Ausgabedatei für QR-Code (Standard: <input>.png)'
    )
    generate_parser.add_argument(
        '-p', '--password',
        help='Passwort (wird interaktiv abgefragt, wenn nicht angegeben)'
    )
    generate_parser.add_argument(
        '--max-size',
        type=int,
        help='Maximale Größe in Bytes (Standard: 2953)'
    )
    generate_parser.add_argument(
        '--show-text',
        action='store_true',
        help='Zeigt den QR-Code-Text an'
    )

    # Read Command
    read_parser = subparsers.add_parser(
        'read',
        help='Liest einen QR-Code aus einem Bild'
    )
    read_parser.add_argument(
        '-i', '--input',
        required=True,
        help='QR-Code Bilddatei'
    )
    read_parser.add_argument(
        '-o', '--output',
        help='Ausgabedatei (entschlüsselt automatisch, wenn angegeben)'
    )
    read_parser.add_argument(
        '-p', '--password',
        help='Passwort (wird interaktiv abgefragt, wenn nicht angegeben)'
    )
    read_parser.add_argument(
        '--show-text',
        action='store_true',
        help='Zeigt den QR-Code-Text an'
    )

    # Decrypt Command
    decrypt_parser = subparsers.add_parser(
        'decrypt',
        help='Entschlüsselt QR-Code-Text direkt'
    )
    decrypt_parser.add_argument(
        '-t', '--text',
        required=True,
        help='QR-Code-Text (Base64-kodiert)'
    )
    decrypt_parser.add_argument(
        '-o', '--output',
        required=True,
        help='Ausgabedatei'
    )
    decrypt_parser.add_argument(
        '-p', '--password',
        help='Passwort (wird interaktiv abgefragt, wenn nicht angegeben)'
    )

    args = parser.parse_args()

    setup_logging(args.verbose)

    if not args.command:
        parser.print_help()
        return 1

    # Führe den entsprechenden Befehl aus
    if args.command == 'generate':
        return generate_qr(args)
    elif args.command == 'read':
        return read_qr(args)
    elif args.command == 'decrypt':
        return decrypt_text(args)

    return 0


if __name__ == '__main__':
    sys.exit(main())
