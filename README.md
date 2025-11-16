# PyQrDataExchange

Secure file transfer via QR codes with encryption, compression, and automatic multi-part splitting for large files.

## Features

- 🔒 **Strong Encryption**: NaCl/Argon2i for password-based encryption
- 🗜️ **Compression**: Zstandard compression reduces file size
- 📱 **QR Code Generation**: Convert files to QR codes for easy transfer
- 🔄 **Multi-Part Support**: Large files automatically split into multiple QR codes
- 🖥️ **GUI & CLI**: User-friendly graphical interface and powerful command-line tools
- ✅ **Hash Validation**: SHA256 ensures data integrity
- 🔀 **Flexible Reading**: Multi-part QR codes can be read in any order

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
pip install pillow qrcode qreader pynacl msgpack pyzstd
```

**Minimum (uses OpenCV fallback):**
```bash
pip install pillow qrcode opencv-python pynacl msgpack pyzstd
```

### Python Version

- Python 3.7 or higher
- Tested on Python 3.8, 3.9, 3.10, 3.11, 3.12

### Why qreader?

The application now uses `qreader` for improved QR code detection:
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
# Generate QR code from file
python -m app.cli generate -i myfile.txt -o qrcode.png

# Read QR code and decrypt
python -m app.cli read -i qrcode.png -o restored.txt
```

## GUI Usage

### Encrypting Files to QR Codes

1. **Launch the application**
   ```bash
   python run_app.py
   ```

2. **Enter a password** (1-20 characters)
   - Password is required for encryption/decryption
   - Use a strong, memorable password

3. **Select a file**
   - Click "Browse" to select your file
   - Or manually enter the file path

4. **Generate QR Code**
   - Click "Generate QR"
   - Wait for processing (may take a few seconds for large files)

5. **View and Save**
   - **Single-Part**: One QR code window opens
     - Click "Save As" to save the QR code image
   
   - **Multi-Part**: Navigation window opens
     - Browse through parts with "◄ Previous" / "Next ►"
     - "Save Current": Save the displayed QR code
     - "Save All": Save all QR codes to a folder (includes .txt files with QR text)

### Decrypting QR Codes

#### Option 1: From QR Code Image

1. **Enter password** (same as used for encryption)
2. **Select QR code image** via "Browse"
3. **Click "Read QR"**
4. **Decrypt window opens**
   - Click "Decrypt and Save as"
   - Choose output file location

#### Option 2: From Text String

1. **Enter password**
2. **Click "Read String"**
3. **Add QR codes**:
   - Click "Add QR Code Image(s)" to load one or multiple parts at once
   - Select multiple files: Hold `Ctrl` (Windows/Linux) or `Cmd` (macOS) while clicking
   - Or paste QR text directly in the text field
   - Status shows: "X QR codes loaded (last: Part Y/Z)"
4. **Click "Decrypt and Save as"**
5. **Select output file**

**Tip:** You can select all QR code images at once by:
- Using Ctrl+A in the file dialog
- Or selecting the first file, then Shift+Click on the last file

#### Option 3: Paste Multiple QR Texts

If you have multiple QR texts concatenated (ending with `==`):
- Paste them into the text field
- The application auto-detects multi-part format
- Automatically splits at `==` boundaries

## CLI Usage

### Generate QR Codes

```bash
# Basic usage
python -m app.cli generate -i input_file.txt

# With custom output
python -m app.cli generate -i input_file.txt -o my_qr.png

# Specify password via command line (not recommended for security)
python -m app.cli generate -i input_file.txt -p mypassword

# Multi-part with text file export
python -m app.cli generate -i large_file.pdf --save-texts

# Custom max size per QR code
python -m app.cli generate -i file.txt --max-size 2000
```

**Multi-Part Output:**
When a file is split into multiple parts:
```
input_file_part1_of_3.png
input_file_part2_of_3.png
input_file_part3_of_3.png
input_file_qr_texts.txt  (if --save-texts used)
```

### Read QR Codes

```bash
# Read single QR code (shows text only)
python -m app.cli read -i qrcode.png

# Read and decrypt to file
python -m app.cli read -i qrcode.png -o restored.txt

# Read multiple QR codes (multi-part)
python -m app.cli read -i qr_part*.png -o restored.pdf

# Read specific parts
python -m app.cli read -i part1.png part2.png part3.png -o file.txt

# Show QR text content
python -m app.cli read -i qrcode.png --show-text
```

### Decrypt from Text

```bash
# Decrypt single QR text
python -m app.cli decrypt -t "BASE64STRING..." -o output.txt

# Decrypt from text file (multi-part)
python -m app.cli decrypt --text-file qr_texts.txt -o restored.pdf
```

### Verbose Mode

Add `-v` or `--verbose` for detailed logging:

```bash
python -m app.cli generate -i file.txt -v
```

## Password Guidelines

- **Length**: 1-20 characters
- **Strength**: Use a mix of letters, numbers, and symbols
- **Storage**: Keep passwords secure and separate from QR codes
- **Recovery**: Lost passwords = lost data (by design for security)

## File Size Limits

### Single-Part QR Codes
- **Default limit**: ~2953 bytes (customizable with `--max-size`)
- **After compression**: Actual file size can be larger
- Files exceeding limit automatically use multi-part

### Multi-Part QR Codes
- **Automatic**: No size limit, files split automatically
- **Chunk size**: ~2000 bytes per QR code (after metadata overhead)
- **Example**: 10KB file → ~5 QR codes

## Security

### Encryption Details
- **Algorithm**: NaCl SecretBox (XSalsa20 + Poly1305)
- **Key Derivation**: Argon2i (memory-hard function)
- **Salt**: Unique random salt per encryption (16 bytes)
- **Authentication**: Built-in MAC for tampering detection

### Security Best Practices
1. **Use strong passwords**: Mix characters, numbers, symbols
2. **Never share passwords with QR codes**: Store separately
3. **Verify hash**: Multi-part QR codes include SHA256 validation
4. **Secure transmission**: QR codes themselves don't reveal password
5. **No backdoors**: Encryption is client-side, no key escrow

### What's Protected
- ✅ File contents (encrypted)
- ✅ File integrity (hash validation)
- ✅ Against tampering (authenticated encryption)

### What's NOT Hidden
- ❌ File size (approximate, from QR code count)
- ❌ Fact that data is encrypted (obvious from format)

## Technical Details

### Data Flow

**Encryption (Generate):**
```
File → Compress (zstd) → Encrypt (NaCl+Argon2) → 
Split (if needed) → Base64 → QR Code
```

**Decryption (Read):**
```
QR Code → Base64 Decode → Reassemble (if multi-part) → 
Decrypt → Decompress → File
```

### Storage Format

**Single-Part:**
```
base64(msgpack([salt, encrypted_compressed_data]))
```

**Multi-Part:**
```
base64(msgpack({
    'v': 2,              # Version
    'p': part_number,    # 1, 2, 3, ...
    't': total_parts,    # Total count
    'd': encrypted_chunk # Part of encrypted data
}))
```

The encrypted data includes:
```
msgpack({'d': raw_data, 'h': sha256_hash})
```

### Dependencies

- **pillow**: Image handling for QR codes
- **qrcode**: QR code generation
- **qreader** (recommended): Advanced QR code reading with better detection
- **opencv-python** (fallback): Alternative QR code reading
- **pynacl**: Encryption (NaCl/Argon2)
- **msgpack**: Binary serialization
- **pyzstd**: Zstandard compression

**Note:** Either `qreader` or `opencv-python` is required for reading QR codes. `qreader` is recommended for better detection accuracy.

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

### "Decryption failed. Wrong password or corrupted data"
- Verify you're using the correct password
- Check if QR code image is readable
- For multi-part: ensure all parts are loaded

### "Missing parts: [X, Y, Z]"
- Not all multi-part QR codes were loaded
- Find and load the missing parts
- Part numbers are shown in filenames

### "Hash validation failed"
- Data corruption during transmission
- QR codes might be from different files
- Try re-scanning the QR codes

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

### Example 2: Large File (Multi-Part)

```bash
# Generate multi-part QR codes
python -m app.cli generate -i document.pdf --save-texts
# Password: strongpass123

# Output:
# document_part1_of_4.png
# document_part2_of_4.png
# document_part3_of_4.png
# document_part4_of_4.png
# document_qr_texts.txt

# Read all parts
python -m app.cli read -i document_part*.png -o restored.pdf
# Password: strongpass123
```

### Example 3: GUI Workflow

1. Start GUI: `python run_app.py`
2. Password: `test123`
3. File: `myfile.txt`
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
6. "Decrypt and Save as"
7. File restored!

## Development

### Project Structure

```
py-qr-data-exchange/
├── app/
│   ├── __init__.py
│   ├── main.py              # GUI application
│   ├── cli.py               # Command-line interface
│   ├── controller.py        # GUI controller
│   ├── service.py           # QR generation/reading
│   ├── qr_data_class.py     # Single-part encryption
│   ├── qr_multi_part.py     # Multi-part processor
│   ├── crypt_utils.py       # Encryption utilities
│   └── extra_windows.py     # GUI windows
├── run_app.py               # Application entry point
├── README.md                # This file
└── README_multi_part_qr_code.md  # Multi-part documentation
```

### Running Tests

```bash
# Test encryption/decryption
python -m app.qr_data_class

# Test multi-part
python -m app.qr_multi_part

# Test service
python -m app.service

# Test crypto utilities
python -m app.crypt_utils
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

**Q: What's the maximum file size?**  
A: No hard limit. Files are automatically split into multiple QR codes. Practical limit depends on how many QR codes you want to manage.

**Q: Are QR codes compatible between versions?**  
A: Single-part QR codes are compatible. Multi-part uses version field for future compatibility.

**Q: Can I change the password later?**  
A: No. Decrypt with old password, then encrypt with new password.

**Q: Do I need internet connection?**  
A: No. Everything runs locally.

**Q: Can QR codes be printed?**  
A: Yes! Ensure sufficient DPI (300+ recommended) for reliable scanning.

## Support

For issues, questions, or contributions, see the project repository.

---

**Made with ❤️ for secure, portable data transfer**
