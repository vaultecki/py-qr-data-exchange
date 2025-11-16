# QR Data Exchange - Multi-Part Feature

## Overview

The QR Data Exchange project now supports automatic splitting of large files into multiple QR codes!

### Features
- ✅ **Automatic splitting**: Large files are automatically split into multiple QR codes
- ✅ **Hash validation**: SHA256 hash ensures data integrity
- ✅ **Flexible reconstruction**: QR codes can be read in any order
- ✅ **Single-pass encryption**: File is encrypted once, then split (more efficient)
- ✅ **GUI & CLI support**: Both interfaces support multi-part

## How it works

### Encryption & Splitting
1. File is compressed (zstd)
2. Compressed data is encrypted (NaCl/Argon2)
3. Encrypted data is split into chunks
4. Each chunk receives metadata (part number, total count, hash)
5. QR codes are generated for each chunk

### Decryption & Reconstruction
1. QR codes are read (any order)
2. Metadata is validated (same hash, all parts present)
3. Chunks are assembled in correct order
4. Data is decrypted and decompressed
5. Hash is validated

## GUI Usage

### Generate QR Codes

1. Start the application
2. Select a file
3. Enter a password
4. Click "Generate QR"

**For large files:**
- Multiple QR codes are created automatically
- Navigate with "◄ Previous" / "Next ►"
- "Save All" button saves all QR codes to a folder
- "Save Current" button saves only the displayed QR code

### Read QR Codes

**Option 1: Single QR Code**
1. Select QR code image
2. Click "Read QR"
3. Decrypt and save

**Option 2: Multi-Part QR Codes**
1. Click "Read String"
2. Add QR code images with "Add QR Code Image"
3. Load all parts (status is displayed: "3 QR codes loaded")
4. Click "Decrypt and Save as"
5. Select output file

## CLI Usage

### Split Large File into QR Codes

```bash
# Generate multi-part QR codes
python -m app.cli generate -i large_file.pdf

# Output: large_file_part1_of_5.png, ..., large_file_part5_of_5.png
```

**With options:**
```bash
# Custom output prefix and save QR texts
python -m app.cli generate -i large_file.pdf -o my_qr --save-texts

# Output:
# - my_qr_part1_of_5.png
# - my_qr_part2_of_5.png
# - ...
# - my_qr_qr_texts.txt (contains all QR texts)
```

### Read Multi-Part QR Codes

```bash
# Read all QR code images at once and decrypt
python -m app.cli read -i qr_part*.png -o restored.pdf
```

**Or individually:**
```bash
# Read individual parts
python -m app.cli read -i qr_part1_of_3.png qr_part2_of_3.png qr_part3_of_3.png -o file.pdf
```

### Decrypt Multi-Part from Text File

```bash
# If QR texts were saved to file
python -m app.cli decrypt --text-file qr_texts.txt -o restored.pdf
```

## Technical Details

### Data Format

```python
# Single QR code (as before)
base64(msgpack([salt, encrypted_data]))

# Multi-part QR code (new)
base64(msgpack({
    'v': 1,              # Version
    'p': part_number,    # e.g. 1, 2, 3, ...
    't': total_parts,    # e.g. 5
    'd': data_chunk      # Part of encrypted data
}))
```

### Size Constraints

- **Standard QR code**: max. 2953 bytes
- **Metadata overhead**: ~200 bytes
- **Effective data size per QR**: ~2750 bytes

### Example Calculation

File: 20 KB (compressed and encrypted)
- Chunk size: ~2750 bytes
- Number of QR codes: 20000 / 2750 ≈ 8 QR codes

## Troubleshooting

### "Missing parts: [2, 4]"
- Not all QR codes were loaded
- Load the missing parts

### "Hash validation failed"
- Data is corrupt or QR codes don't belong together
- Ensure all QR codes are from the same file

### "Inconsistent hashes"
- QR codes are from different files
- Check if you loaded the correct QR codes

## Code Examples

### Programming with the API

```python
from app.qr_multi_part import MultiPartQrProcessor

# Split file
with open('large_file.pdf', 'rb') as f:
    data = f.read()

qr_strings = MultiPartQrProcessor.serialize_multipart(
    raw_data=data,
    password="my_password",
    max_qr_bytes=2953
)

print(f"{len(qr_strings)} QR codes created")

# Reassemble QR codes
restored_data = MultiPartQrProcessor.deserialize_multipart(
    qr_strings=qr_strings,
    password="my_password"
)

assert data == restored_data  # Validation
```

### Check if Multi-Part

```python
from app.qr_multi_part import MultiPartQrProcessor

qr_text = "..."  # Read from QR code

if MultiPartQrProcessor.is_multipart_qr(qr_text):
    part_num, total = MultiPartQrProcessor.get_part_info(qr_text)
    print(f"Multi-part: Part {part_num} of {total}")
else:
    print("Single-part QR code")
```

## Migration from Existing Files

Old single-part QR codes still work! The system automatically detects:
- Single-part QR codes (old method)
- Multi-part QR codes (new method)

No changes to existing workflows necessary.

## Performance

### Encryption
- **Single-part**: 1x encryption
- **Multi-part**: 1x encryption (same speed!)

### QR Code Generation
- Per QR code: ~0.1-0.5 seconds
- 10 QR codes: ~1-5 seconds

### Decryption
- Same performance as single-part
- Hash validation: minimal overhead

## Best Practices

1. **For small files** (<2 KB): Single-part is sufficient
2. **For medium files** (2-20 KB): Multi-part with 2-8 QR codes
3. **For large files** (>20 KB): Compression is important
4. **Backup**: Save QR texts additionally as text file (`--save-texts`)
5. **Organization**: Use meaningful filenames
6. **Validation**: Always check that all parts are present

## Security

- **Hash validation**: SHA256 ensures integrity
- **Encryption**: NaCl/Argon2 (same security as single-part)
- **No vulnerability**: Splitting happens AFTER encryption
- **Part information**: Metadata is not sensitive (only numbers and hash)
