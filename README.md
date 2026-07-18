# PyQrDataExchange

Transfers files via QR codes: the input is bundled into a tar archive, compressed with LZMA, encrypted, and encoded as one or more QR codes. Intended for offline transfer where no network connection is available or desired.

## Features

- Encryption: NaCl SecretBox with Argon2i password-based key derivation
- Compression: LZMA compresses the bundled content before encryption
- Bundles any number of files and/or whole directories (recursively) into one transfer
- Automatic multi-part splitting: large payloads are split across as many QR codes as needed
- GUI (Tkinter) and CLI, both built on the same core library
- Each QR code is encrypted independently (own salt, own Argon2i derivation, own SecretBox); part number and total-part count are only visible after successful decryption
- Multi-part QR codes can be scanned/loaded in any order

## Installation

### Standard

```bash
git clone <repository-url>
cd py-qr-data-exchange
pip install -r requirements.txt
```

### Minimal

Uses OpenCV instead of `qreader` for QR detection (smaller install):

```bash
pip install -r requirements-minimal.txt
```

### Development

Includes pytest and lint/type-check tools:

```bash
pip install -r requirements-dev.txt
```

### Manual

```bash
# with qreader (better detection)
pip install pillow qrcode qreader pynacl msgpack

# without qreader (OpenCV fallback only)
pip install pillow qrcode opencv-python pynacl msgpack
```

`lzma` and `tarfile` are part of the Python standard library; no extra package needed.

### Python version

- Python 3.7 or higher.
- Python 3.12+ uses the standard library's `filter='data'` sandbox for tar extraction (path-traversal guard). Below 3.12, a manual path check is used instead.

### qreader vs. OpenCV

`qreader` generally detects QR codes more reliably than plain OpenCV, in particular for rotated, blurry, or low-contrast images. It's an optional dependency; if it isn't installed, the OpenCV detector is used instead. `requirements-minimal.txt` omits it for a smaller install.

## Quick start

GUI:

```bash
python run_app.py
```

CLI:

```bash
python -m app.cli generate -i myfile.txt -o qrcode.png
python -m app.cli read -i qrcode.png -o restored/
```

## GUI usage

### Encrypting files/folders to QR codes

1. Start the app: `python run_app.py`
2. Enter a password (required; no length limit).
3. Select input:
   - "Browse Files": one or more files (multi-select supported)
   - "Browse Folder": a whole directory, added recursively
4. Click "Generate QR". Each QR code involves its own key derivation, so payloads needing many QR codes take correspondingly longer than a single one.
5. A navigation window opens (used the same way for one part or many):
   - "◄ Previous" / "Next ►" to browse parts
   - "Save Current": save the currently displayed QR code image
   - "Save All": save all QR codes to a folder, including `.txt` files with the QR text (these can be re-imported directly when decrypting)

### Decrypting QR codes

1. Enter the password used for encryption.
2. Click "Read QR Code(s)".
3. Add parts in any order:
   - "Add QR Code File(s)": select QR code images (`.png`/`.jpg`) and/or `.txt` files from "Save All"; multi-select supported.
   - Or paste a QR code's text into the text field and click "Add". Multiple concatenated texts (base64 blobs ending in `==`) are split automatically.
   - The status label shows "X/Y parts loaded" once at least one part has decrypted (Y is only known at that point, since it's encrypted).
4. "Decrypt and Extract to Folder" is enabled once all parts 1..Y are loaded.
5. Click it and choose an output folder; all recovered files and folder structure are extracted there.

A part that fails to decrypt (wrong password, corrupted, or from a different transfer) is rejected with an explanation when added, rather than only failing at the final decrypt step.

## CLI usage

`-v`/`--verbose` is a global flag and must come before the subcommand: `python -m app.cli -v generate ...`.

### Generate

```bash
# single file
python -m app.cli generate -i input_file.txt

# multiple files and/or a folder, bundled together
python -m app.cli generate -i file_a.txt file_b.pdf some_folder/

# custom output prefix
python -m app.cli generate -i input_file.txt -o my_qr.png

# password via argument (visible in shell history/process list)
python -m app.cli generate -i input_file.txt -p mypassword

# also write the QR text(s) to a .txt file
python -m app.cli generate -i large_file.pdf --save-texts

# custom max size per QR code
python -m app.cli generate -i file.txt --max-size 2000
```

When the content is split into multiple parts, output looks like:

```
input_file_part1_of_3.png
input_file_part2_of_3.png
input_file_part3_of_3.png
input_file_qr_texts.txt  (if --save-texts was used)
```

### Read

`-o`/`--output` is a directory; if given, the QR code(s) are decrypted and extracted into it.

```bash
# print text only, no decryption
python -m app.cli read -i qrcode.png

# decrypt and extract
python -m app.cli read -i qrcode.png -o restored/

# multiple parts
python -m app.cli read -i qr_part*.png -o restored/

# show QR text content
python -m app.cli read -i qrcode.png --show-text
```

### Decrypt from text

`-o`/`--output` is required and is a directory.

```bash
python -m app.cli decrypt -t "BASE64STRING..." -o restored/
python -m app.cli decrypt --text-file qr_texts.txt -o restored/
```

## Password guidelines

- No length limit; Argon2i's cost doesn't depend on password length, so a long passphrase costs nothing extra.
- There is no password recovery. Losing the password means the data cannot be recovered.
- Keep the password separate from the QR codes.

## Size limits

- Default limit per QR code: ~2953 bytes, adjustable with `--max-size`. After per-part encryption/msgpack/base64 overhead, roughly ~2000 bytes of that is actual compressed payload.
- No overall limit; content is split across as many QR codes as needed. A 10 KB payload after compression typically needs around 4-5 QR codes at the default size.

## How it works

### Pipeline

Generating:

```
File(s) / Folder(s)
  -> tar (bundle, preserving relative paths)
  -> LZMA compress (once, over the whole archive)
  -> split into chunks sized to fit max-size per QR code
  -> per chunk: fresh random salt -> Argon2i key derivation -> NaCl SecretBox encrypt
  -> base64
  -> QR code image
```

Reading:

```
QR code(s)
  -> base64 decode
  -> per part: read its own salt -> Argon2i key derivation -> NaCl SecretBox decrypt
  -> validate all parts agree on total count, none missing
  -> sort by part number, concatenate
  -> LZMA decompress
  -> tar extract into the chosen output folder
```

### Wire format

Every QR code has the same structure; a payload that fits in one QR code is simply the `t == 1` case.

```python
# visible without the password:
base64(msgpack({
    's': salt,             # bytes - this part's own Argon2i salt
    'e': encrypted_inner,  # NaCl SecretBox ciphertext (nonce + ciphertext + MAC)
}))

# only visible after successful decryption:
{
    'v': 1,             # format version
    'p': part_number,   # 1-indexed
    't': total_parts,
    'd': chunk_bytes,   # a slice of the single LZMA-compressed tar stream
}
```

Part number and total-part count live inside the ciphertext, so nothing about how a payload was split is visible without the password.

### Design decisions

**Every part gets its own full Argon2i derivation.** Rather than deriving one master key and cheaply re-keying each part, each QR code runs an independent, full Argon2i pass. This costs `O(number of parts)` Argon2i runs for generation/reading, which is slower for large multi-part transfers than a shared-key design would be. The trade-off is that parts share no key material.

**Compress once, encrypt per part.** The whole bundle is LZMA-compressed exactly once; only the resulting stream is sliced into per-QR-code chunks. Compressing per chunk would hurt the compression ratio for anything but a single QR code.

**No separate integrity hash.** An earlier version of this format stored a SHA256 hash to detect corruption or mixed-up parts; this is no longer needed. NaCl's authenticated encryption (Poly1305 MAC) already detects tampering or corruption of any individual part, and parts mixed across different encryption runs fail to reassemble into a valid LZMA stream or tar archive — the failure is still clear, just surfaces one layer later than an explicit hash check would.

**Order-independent parts.** Parts carry their own part number and are sorted before reassembly, so they can be scanned or loaded in any order.

**Bundling via tar.** Multiple files/folders are bundled with the standard-library `tarfile` before compression; there is no separate filename field, since names and directory structure come from the archive.

### Errors

| Error | Meaning |
|---|---|
| `Missing parts: [2, 4]` | Not all parts were loaded/scanned |
| `Inconsistent total_parts across parts` | Parts disagree on total count, likely mixed from different transfers |
| `Decryption failed. Wrong password or corrupted data.` | A part's decryption/authentication failed |
| `Decompression failed. Parts may be corrupted or come from different encryption runs.` | Parts decrypted individually but didn't reassemble into a valid compressed stream |
| Unsafe path in archive | A recovered archive member tried to escape the output folder; extraction was refused |

### Performance

- Both generation and reading scale as `O(number of parts)` in key-derivation cost. For a handful of parts this is unnoticeable; a file split into dozens of parts can take several seconds for key derivation alone.
- LZMA uses `9 | PRESET_EXTREME` for the best compression ratio; this is a one-time cost per generation, independent of the number of parts.

## Security

### Encryption details

- Algorithm: NaCl SecretBox (XSalsa20 + Poly1305)
- Key derivation: Argon2i, run independently per QR code
- Salt: unique random salt per QR code
- Authentication: MAC per part, detects tampering

### What's protected

- File/folder contents (encrypted)
- Part bookkeeping (part number, total-part count) — encrypted, not plaintext
- Tampering (authenticated encryption per part)

### What's not hidden

- Approximate total size, inferable from the number of QR codes
- The fact that the data is encrypted

### Practices worth following

- Use a long password or passphrase.
- Don't store the password together with the QR codes.
- There is no password recovery mechanism by design.

## Troubleshooting

**"Password cannot be empty"** — enter a password before generating/reading.

**"No QR code found in image"** — the image may be corrupted, low quality, or rotated more than ~45 degrees. Installing `qreader` (`pip install qreader`) improves detection.

**"Decryption failed. Wrong password or corrupted data."** — check the password, and for multi-part transfers, that all parts are loaded.

**"Missing parts: [X, Y, Z]"** — not all parts were loaded; part numbers only become visible after a part decrypts successfully, not from the filename.

**"Decompression failed. Parts may be corrupted or come from different encryption runs."** — each part decrypted individually but doesn't fit together, likely parts from two different generations were mixed. Re-scan and confirm all parts belong to the same transfer.

**GUI window not opening (multi-part)** — check the console for errors, confirm dependencies are installed, and run with `-v` for more logging.

## Examples

### Single file

```bash
echo "Secret message!" > secret.txt
python -m app.cli generate -i secret.txt
# -> secret.png
```

### Multiple files and a folder, multi-part

```bash
python -m app.cli generate -i notes.txt photo.jpg documents/ --save-texts
# if it needs 4 parts:
# archive_part1_of_4.png ... archive_part4_of_4.png
# archive_qr_texts.txt

python -m app.cli read -i archive_part*.png -o restored/
# -> restored/notes.txt, restored/photo.jpg, restored/documents/...
```

### GUI workflow

Encrypt: start `run_app.py` -> enter password -> "Browse Files"/"Browse Folder" -> "Generate QR" -> "Save All" -> share the images.

Decrypt: start `run_app.py` -> enter the same password -> "Read QR Code(s)" -> "Add QR Code File(s)" for each part -> once "N/N parts loaded" is shown, click "Decrypt and Extract to Folder" -> choose output folder.

## Development

### Project structure

```
py-qr-data-exchange/
├── app/
│   ├── main.py              # GUI application
│   ├── cli.py               # command-line interface
│   ├── controller.py        # GUI controller (background threads)
│   ├── service.py           # QR generation/reading orchestration
│   ├── qr_multi_part.py     # packaging, per-part encryption, reassembly, tar extraction
│   ├── crypt_utils.py       # Argon2i + NaCl SecretBox
│   └── extra_windows.py     # GUI windows
├── tests/                   # pytest suite
├── run_app.py                # application entry point
└── README.md
```

### Running tests

```bash
pytest
```

Each core module also has a `__main__` self-test for a quick manual check without pytest:

```bash
python -m app.crypt_utils
python -m app.qr_multi_part
python -m app.service
```

## License

Copyright 2025 ecki
SPDX-License-Identifier: Apache-2.0

## Contributing

Contributions are welcome. Please keep the code style consistent, make sure tests pass, and document any security-relevant changes.

## FAQ

**What's the maximum payload size?** No hard limit. Content is split into as many QR codes as needed; in practice the limit is how many QR codes you're willing to generate/manage/scan, and how long you're willing to wait for per-part key derivation.

**Are QR codes compatible between versions of this tool?** The wire format is versioned (`'v'` field inside the encrypted payload) for future extensibility, but the current format is a clean break from earlier releases — QR codes from older versions are not readable by this version.

**Can I send multiple files or a whole folder?** Yes; `generate` accepts any number of files and/or directories and bundles them, preserving relative structure, into one encrypted transfer.

**Can I change the password later?** No. Decrypt with the old password, then generate again with the new one.

**Do I need an internet connection?** No; everything runs locally.

**Can QR codes be printed?** Yes; 300+ DPI is recommended for reliable scanning.
