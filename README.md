# PyQrDataExchange

Secure file transfer via QR codes with encryption, compression, and automatic multi-part splitting for large payloads.

## Features

- 🔒 **Strong Encryption**: NaCl SecretBox with Argon2i password-based key derivation — every single QR code has its own random salt and its own independently derived key
- 🗜️ **Compression**: LZMA compresses the bundled content before encryption
- 📱 **QR Code Generation**: Convert files/folders to QR codes for easy, offline transfer
- 📦 **Multiple Files & Folders**: Bundle any number of files and/or entire directories (with subfolders) into a single encrypted transfer
- 🔄 **Multi-Part Support**: Large payloads are automatically split across as many QR codes as needed
- 🖥️ **GUI & CLI**: User-friendly graphical interface and powerful command-line tools
- 🕵️ **Self-Contained Parts**: Each QR code authenticates itself independently (NaCl MAC); part numbers and total-part counts are only visible after successful decryption, never in plaintext
- 🔀 **Flexible Reading**: Multi-part QR codes can be scanned/loaded in any order

## Installation

### Standard Installation (Recommended)

```bash
# Clone or download the repository
git clone <repository-url>
cd py-qr-data-exchange

# Install all dependencies
pip install -r requirements.txt
```

### Minimal Installation

For resource-constrained environments or minimal dependencies:

```bash
# Uses OpenCV instead of qreader (smaller footprint)
pip install -r requirements-minimal.txt
```

### Development Installation

For contributors and developers:

```bash
# Includes testing, linting, and documentation tools
pip install -r requirements-dev.txt
```

### Manual Installation

If you prefer to install packages individually:

**Recommended (best QR code detection):**
```bash
pip install pillow qrcode qreader pynacl msgpack
```

**Minimum (uses OpenCV fallback):**
```bash
pip install pillow qrcode opencv-python pynacl msgpack
```

Compression (`lzma`) and archiving (`tarfile`) are part of the Python standard library — no extra package needed for either.

### Python Version

- Python 3.7 or higher
- Python 3.12+ is recommended: tar extraction uses the safe `filter='data'` sandbox added in 3.12 to guard against path-traversal in untrusted archives; on older versions a manual path check is used instead.

### Why qreader?

The application uses `qreader` for improved QR code detection:
- ✅ **Better detection**: More robust than OpenCV
- ✅ **Handles difficult cases**: Rotated, blurry, or low-contrast QR codes
- ✅ **Automatic fallback**: Falls back to OpenCV if qreader not available
- ✅ **Optional**: Works with OpenCV alone, but qreader recommended

## Quick Start

### GUI Application

```bash
python run_app.py
```

Or:

```bash
python -m app.main
```

### CLI Usage

```bash
# Generate QR code(s) from a file
python -m app.cli generate -i myfile.txt -o qrcode.png

# Read QR code(s) and decrypt into a folder
python -m app.cli read -i qrcode.png -o restored/
```

## GUI Usage

### Encrypting Files/Folders to QR Codes

1. **Launch the application**
   ```bash
   python run_app.py
   ```

2. **Enter a password**
   - Password is required for encryption/decryption
   - Use a strong, memorable password — there's no length limit, so a long passphrase is a good choice

3. **Select input**
   - **"Browse Files"**: pick one or more files (hold `Ctrl`/`Cmd` to multi-select)
   - **"Browse Folder"**: pick a whole directory (added recursively, subfolders included)
   - The field next to the buttons shows the selected path, or a count like "3 items selected"

4. **Generate QR Code**
   - Click "Generate QR"
   - Wait for processing — every QR code involves its own password-hashing step, so larger payloads that need many QR codes take noticeably longer than a single one

5. **View and Save**
   - A navigation window opens (used for one part just as much as for many):
     - Browse through parts with "◄ Previous" / "Next ►"
     - "Save Current": Save the currently displayed QR code image
     - "Save All": Save all QR codes to a folder (includes `.txt` files with the QR text)

### Decrypting QR Codes

#### Option 1: From QR Code Image

1. **Enter password** (same as used for encryption)
2. **Select the QR code image** via "Browse Files" (exactly one image)
3. **Click "Read QR"**
4. **Decrypt window opens**
   - Click "Decrypt and Extract to Folder"
   - Choose an output folder — all recovered files (and folder structure) are extracted there

#### Option 2: From Text String

1. **Enter password**
2. **Click "Read String"**
3. **Add QR codes**:
   - Click "Add QR Code Image(s)" to load one or multiple parts at once
   - Select multiple files: Hold `Ctrl` (Windows/Linux) or `Cmd` (macOS) while clicking
   - Or paste QR text directly in the text field
   - Status shows: "X QR codes loaded"
4. **Click "Decrypt and Extract to Folder"**
5. **Select an output folder**

**Tip:** You can select all QR code images at once by:
- Using Ctrl+A in the file dialog
- Or selecting the first file, then Shift+Click on the last file

#### Option 3: Paste Multiple QR Texts

If you have multiple QR texts concatenated (ending with `==`):
- Paste them into the text field
- The application auto-detects the multi-part format
- Automatically splits at `==` boundaries

## CLI Usage

`-v`/`--verbose` is a global flag and must come **before** the subcommand, e.g. `python -m app.cli -v generate ...`.

### Generate QR Codes

```bash
# Basic usage (single file)
python -m app.cli generate -i input_file.txt

# Multiple files and/or a whole folder, bundled together
python -m app.cli generate -i file_a.txt file_b.pdf some_folder/

# With custom output prefix
python -m app.cli generate -i input_file.txt -o my_qr.png

# Specify password via command line (not recommended for security)
python -m app.cli generate -i input_file.txt -p mypassword

# Multi-part with text file export
python -m app.cli generate -i large_file.pdf --save-texts

# Custom max size per QR code
python -m app.cli generate -i file.txt --max-size 2000
```

**Multi-Part Output:**
When the content is split into multiple parts:
```
input_file_part1_of_3.png
input_file_part2_of_3.png
input_file_part3_of_3.png
input_file_qr_texts.txt  (if --save-texts used)
```

### Read QR Codes

`-o`/`--output` for `read` is a **folder** — if given, the QR code(s) are decrypted and everything they contain is extracted into it.

```bash
# Read single QR code (shows text only, no decryption)
python -m app.cli read -i qrcode.png

# Read and decrypt into a folder
python -m app.cli read -i qrcode.png -o restored/

# Read multiple QR codes (multi-part) and extract
python -m app.cli read -i qr_part*.png -o restored/

# Read specific parts
python -m app.cli read -i part1.png part2.png part3.png -o restored/

# Show QR text content
python -m app.cli read -i qrcode.png --show-text
```

### Decrypt from Text

`-o`/`--output` for `decrypt` is **required** and is also a folder.

```bash
# Decrypt a single QR text
python -m app.cli decrypt -t "BASE64STRING..." -o restored/

# Decrypt from a text file (multi-part)
python -m app.cli decrypt --text-file qr_texts.txt -o restored/
```

### Verbose Mode

```bash
python -m app.cli -v generate -i file.txt
```

## Password Guidelines

- **Length**: No limit — a longer passphrase is stronger and Argon2i's cost doesn't depend on password length
- **Strength**: Use a mix of letters, numbers, and symbols, or a long passphrase
- **Storage**: Keep passwords secure and separate from QR codes
- **Recovery**: Lost passwords = lost data (by design for security)

## File Size Limits

- **Default limit per QR code**: ~2953 bytes (customizable with `--max-size`), which after the per-part encryption/msgpack/base64 overhead leaves roughly ~2000 bytes of actual (compressed) payload per QR code
- **No hard limit overall**: content is automatically split across as many QR codes as needed
- **Example**: a 10 KB payload after compression typically needs ~4-5 QR codes at the default size

## How It Works

### Pipeline

**Generating QR codes:**
```
File(s) / Folder(s)
  → tar (bundle, preserving relative paths)
  → LZMA compress (once, over the whole archive)
  → split into chunks (sized to fit max-size per QR code)
  → per chunk: fresh random salt → Argon2i key derivation → NaCl SecretBox encrypt
  → base64
  → QR code image
```

**Reading QR codes:**
```
QR code(s)
  → base64 decode
  → per part: read its own salt → Argon2i key derivation → NaCl SecretBox decrypt
  → validate all parts agree on the total count and none are missing
  → sort by part number, concatenate
  → LZMA decompress
  → tar extract (into the chosen output folder)
```

### Wire Format

Every QR code carries the same self-contained structure — there is no separate "single-file" format; a payload that fits in one QR code is simply the `t == 1` case:

```python
# What's visible without the password:
base64(msgpack({
    's': salt,             # bytes — this part's own Argon2i salt
    'e': encrypted_inner,  # NaCl SecretBox ciphertext (nonce + ciphertext + MAC)
}))

# What's only visible after successful decryption:
{
    'v': 1,             # format version
    'p': part_number,   # 1-indexed
    't': total_parts,
    'd': chunk_bytes,   # a slice of the single LZMA-compressed tar stream
}
```

Because the part/total-part bookkeeping lives *inside* the ciphertext, nothing about how a payload was split is visible from the QR codes themselves without the password — unlike a design where that metadata sits in plaintext next to the ciphertext.

### Key Design Decisions

**Every part gets its own full Argon2i key derivation.** Rather than deriving one master key and cheaply re-keying each part from it, every single QR code runs its own independent, full Argon2i pass. This is deliberately the more expensive option: generating or reading a payload split into many parts costs `O(number of parts)` Argon2i runs, which is noticeably slower than a single derivation for large multi-part transfers. The trade-off buys full independence between parts — there is no shared key material anywhere.

**Compress once, encrypt per part.** The entire bundle (tar of all input files/folders) is LZMA-compressed exactly once for the best possible ratio; only the resulting compressed byte stream is sliced into per-QR-code chunks. Compressing per chunk instead would badly hurt the ratio for anything but a single QR code.

**No separate integrity hash.** Earlier iterations of this format stored a SHA256 hash of the original data to detect corruption or mixed-up parts. That's no longer necessary: NaCl's authenticated encryption (Poly1305 MAC) already detects tampering or corruption of *any individual part*, and parts accidentally mixed across different encryption runs will fail to reassemble into a valid LZMA stream (or a valid tar archive) — so the failure mode is still clear, just surfaced one layer later than an explicit hash check would.

**Order-independent parts.** Parts can be scanned/loaded in any order; they carry their own part number and are sorted before reassembly.

**Multiple files/folders via `tar`.** Bundling happens with Python's standard-library `tarfile` before compression, which is also why there's no separate filename field in the format — names and directory structure come from the archive itself.

### Error Handling

| Error | Meaning |
|---|---|
| `Missing parts: [2, 4]` | Not all parts were loaded/scanned; find and add the missing QR codes |
| `Inconsistent total_parts across parts` | Parts disagree on how many total parts there should be — likely mixed from different transfers |
| `Decryption failed. Wrong password or corrupted data.` | A part's own decryption/authentication failed — wrong password, or that specific QR code is corrupted |
| `Decompression failed. Parts may be corrupted or come from different encryption runs.` | All parts decrypted individually, but didn't reassemble into a valid compressed stream |
| Unsafe path in archive | The recovered archive contained a member trying to escape the output folder; extraction was refused |

### Performance Notes

- Because every part requires its own Argon2i run, both generation and reading scale as `O(number of parts)` in KDF cost — for a handful of QR codes this is unnoticeable, but a large file split into dozens of parts can take several seconds just for key derivation.
- LZMA with the `9 | PRESET_EXTREME` preset is used for the best compression ratio; this is a one-time cost per generation, independent of how many parts result.

## Security

### Encryption Details
- **Algorithm**: NaCl SecretBox (XSalsa20 + Poly1305)
- **Key Derivation**: Argon2i (memory-hard function), run independently per QR code
- **Salt**: Unique random salt per QR code (not per file — every part has its own)
- **Authentication**: Built-in MAC per part for tampering detection

### Security Best Practices
1. **Use strong passwords**: Mix characters, numbers, symbols
2. **Never share passwords with QR codes**: Store separately
3. **Secure transmission**: QR codes themselves don't reveal the password
4. **No backdoors**: Encryption is client-side, no key escrow

### What's Protected
- ✅ File/folder contents (encrypted)
- ✅ Part bookkeeping — part number and total-part count are encrypted, not plaintext
- ✅ Against tampering (authenticated encryption per part)

### What's NOT Hidden
- ❌ Approximate total size (inferable from the number of QR codes)
- ❌ The fact that data is encrypted (obvious from the format)

## Troubleshooting

### "Password cannot be empty"
- Ensure you enter a password before generating/reading

### "No QR code found in image"
- Image might be corrupted or low quality
- Try rescanning or using a better quality image
- Ensure the image actually contains a QR code
- **Install qreader for better detection**: `pip install qreader`
- Try adjusting image brightness/contrast
- Ensure QR code is not rotated more than 45 degrees

### "Decryption failed. Wrong password or corrupted data."
- Verify you're using the correct password
- Check if the QR code image is readable
- For multi-part transfers: ensure all parts are loaded

### "Missing parts: [X, Y, Z]"
- Not all multi-part QR codes were loaded
- Find and load the missing parts (part numbers only become visible after successful decryption of that part, not from the filename)

### "Decompression failed. Parts may be corrupted or come from different encryption runs."
- Each part decrypted on its own, but doesn't fit together — likely parts from two different generations were mixed
- Re-scan the QR codes and make sure they all belong to the same transfer

### GUI Window Not Opening (Multi-Part)
- Check console for error messages
- Ensure all dependencies are installed
- Try running with verbose logging: `python run_app.py` (console shows logs)

## Examples

### Example 1: Encrypt a Text File

```bash
# Create test file
echo "Secret message!" > secret.txt

# Generate QR code
python -m app.cli generate -i secret.txt
# Password prompt: mypassword

# Output: secret.png
```

### Example 2: Multiple Files and a Folder, Large Enough for Multi-Part

```bash
# Bundle two files and a folder into one encrypted transfer
python -m app.cli generate -i notes.txt photo.jpg documents/ --save-texts
# Password: strongpass123

# Output (if it needs, say, 4 parts):
# archive_part1_of_4.png
# archive_part2_of_4.png
# archive_part3_of_4.png
# archive_part4_of_4.png
# archive_qr_texts.txt

# Read all parts back and extract
python -m app.cli read -i archive_part*.png -o restored/
# Password: strongpass123
# -> restored/notes.txt, restored/photo.jpg, restored/documents/...
```

### Example 3: GUI Workflow

1. Start GUI: `python run_app.py`
2. Password: `test123`
3. "Browse Files" or "Browse Folder" to select input
4. Click "Generate QR"
5. Navigate through QR codes (if multi-part)
6. Click "Save All" → Select folder
7. Share QR code images

To decrypt:
1. Start GUI: `python run_app.py`
2. Password: `test123`
3. Click "Read String"
4. "Add QR Code Image" for each part
5. Status: "4 QR codes loaded"
6. "Decrypt and Extract to Folder" → choose output folder
7. Files restored!

## Development

### Project Structure

```
py-qr-data-exchange/
├── app/
│   ├── __init__.py
│   ├── main.py              # GUI application
│   ├── cli.py               # Command-line interface
│   ├── controller.py        # GUI controller
│   ├── service.py           # QR generation/reading orchestration
│   ├── qr_multi_part.py     # Packaging, per-part encryption, reassembly, tar extraction
│   ├── crypt_utils.py       # Encryption utilities (Argon2i + NaCl SecretBox)
│   └── extra_windows.py     # GUI windows
├── run_app.py               # Application entry point
└── README.md                # This file
```

### Running Tests

There is no separate pytest suite; each core module has a `__main__` self-test block instead:

```bash
# Test crypto utilities
python -m app.crypt_utils

# Test packaging/encryption/reassembly (single file, multi-part, multiple files, whole folders)
python -m app.qr_multi_part

# Test the generate/read/decrypt orchestration
python -m app.service
```

## License

Copyright [2025] [ecki]
SPDX-License-Identifier: Apache-2.0

## Contributing

Contributions welcome! Please ensure:
- Code follows existing style
- All tests pass
- Security considerations are documented

## FAQ

**Q: What's the maximum payload size?**
A: No hard limit. Content is automatically split into multiple QR codes. The practical limit is how many QR codes you're willing to generate/manage/scan, and how long you're willing to wait for the per-part key derivation.

**Q: Are QR codes compatible between versions of this tool?**
A: The wire format is versioned (`'v'` field inside the encrypted payload) for future extensibility, but this format is a clean break from earlier releases — QR codes generated by older versions of this tool are not readable by this version.

**Q: Can I send multiple files or a whole folder?**
A: Yes — `generate` accepts any number of files and/or directories and bundles them (with their relative structure) into one encrypted transfer.

**Q: Can I change the password later?**
A: No. Decrypt with the old password, then encrypt with the new password.

**Q: Do I need an internet connection?**
A: No. Everything runs locally.

**Q: Can QR codes be printed?**
A: Yes! Ensure sufficient DPI (300+ recommended) for reliable scanning.

## Support

For issues, questions, or contributions, see the project repository.

---

**Made with ❤️ for secure, portable data transfer**
