# Multi-Part QR Code Feature - Technical Documentation

## Overview

PyQrDataExchange supports automatic splitting of large files into multiple QR codes. This feature enables transfer of files exceeding the ~2953 byte limit of a single QR code.

## Key Features

- ✅ **Automatic Detection**: System automatically uses multi-part when file is too large
- ✅ **Order-Independent**: QR codes can be scanned in any order
- ✅ **Integrity Validation**: SHA256 hash ensures data isn't corrupted
- ✅ **Efficient**: Single encryption pass before splitting
- ✅ **Backward Compatible**: Single-part QR codes still work
- ✅ **Format Version**: Version field for future compatibility

## How Multi-Part Works

### Generation Process

1. **Read & Hash**: File is read and SHA256 hash calculated
2. **Package**: Raw data and hash packed together
3. **Encrypt**: Package compressed (zstd) and encrypted (NaCl/Argon2)
4. **Split**: Encrypted data split into ~2000 byte chunks
5. **Wrap**: Each chunk wrapped with metadata (version, part number, total)
6. **Encode**: Each part encoded to base64 and generated as QR code

### Reconstruction Process

1. **Scan**: QR codes scanned (any order)
2. **Parse**: Each QR decoded and metadata extracted
3. **Validate**: Check all parts present and from same file
4. **Reassemble**: Parts sorted and concatenated
5. **Decrypt**: Combined data decrypted and decompressed
6. **Verify**: SHA256 hash validated against original
7. **Extract**: Original file extracted

## Data Format Specification

### Multi-Part QR Code Structure

```python
base64(msgpack({
    'v': 2,              # Version (int) - Format version
    'p': part_number,    # Part number (int) - 1, 2, 3, ...
    't': total_parts,    # Total parts (int) - e.g., 5
    'd': chunk_data      # Chunk data (bytes) - Part of encrypted blob
}))
```

### Encrypted Data Package

Before splitting, the data is packaged:

```python
msgpack({
    'd': raw_file_data,  # Original file bytes
    'h': sha256_hash     # SHA256 hash of raw_file_data
})
```

Then this package is:
1. Compressed with zstd (level 16)
2. Encrypted with NaCl SecretBox
3. Split into chunks

### Version History

- **Version 1** (deprecated): Hash stored in each part's metadata
- **Version 2** (current): Hash stored in encrypted package (more secure)

## Size Calculations

### Overhead Breakdown

```
Base QR capacity:     2953 bytes (default, configurable)
Metadata overhead:    ~200 bytes (version, part numbers, msgpack)
Base64 overhead:      ~33% (4/3 ratio)
Effective data/QR:    ~2000 bytes (after all overhead)
```

### Example Calculations

**Example 1: Small File (fits in single QR)**
```
File size:         1500 bytes
After compress:    ~1000 bytes (depends on content)
After encrypt:     ~1050 bytes (adds nonce, MAC)
After encode:      ~1400 bytes (base64)
Result:            Single QR code ✓
```

**Example 2: Medium File (needs multi-part)**
```
File size:         10 KB (10240 bytes)
After compress:    ~8 KB (depends on content)
After encrypt:     ~8.1 KB
Per QR payload:    ~2000 bytes
Number of parts:   ceil(8100 / 2000) = 5 QR codes
```

**Example 3: Large File**
```
File size:         100 KB
After compress:    ~60 KB (typical compression)
After encrypt:     ~60.1 KB
Number of parts:   ceil(61500 / 2000) = 31 QR codes
```

## Implementation Details

### Key Design Decisions

#### 1. Encrypt Before Split (Not After)
**Why?** Security and efficiency
- ✅ Single encryption operation
- ✅ No partial decryption possible
- ✅ Cannot reassemble without password
- ❌ Alternative: Encrypt each chunk separately (worse security, same overhead)

#### 2. Hash Validation
**Why?** Detect corruption or tampering
- Hash calculated on original file
- Stored in encrypted package (V2)
- Validated after decryption
- Ensures complete file integrity

#### 3. Order-Independent Parts
**Why?** User convenience
- Parts can be scanned in any order
- Lost parts easily identified by number
- Flexible for various scanning workflows

#### 4. Version Field
**Why?** Future compatibility
- Allows format changes without breaking old codes
- Currently using version 2
- Parser can handle multiple versions

### Code Flow

#### Generation (service.py)

```python
def generate_qr_from_file(filepath, password, max_bytes):
    raw_data = read_file(filepath)
    
    # Try single-part first
    encrypted = serialize(raw_data, password)
    if len(encrypted) < max_bytes:
        return single_qr(encrypted)
    
    # Fall back to multi-part
    qr_strings = serialize_multipart(raw_data, password, max_bytes)
    return [create_qr(s) for s in qr_strings]
```

#### Splitting (qr_multi_part.py)

```python
def serialize_multipart(raw_data, password, max_qr_bytes):
    # Calculate hash first
    file_hash = sha256(raw_data)
    
    # Package with hash
    package = msgpack({'d': raw_data, 'h': file_hash})
    
    # Encrypt entire package
    encrypted = QrDataProcessor.serialize(package, password)
    encrypted_bytes = base64.decode(encrypted)
    
    # Calculate chunk size
    max_chunk = calculate_max_chunk(max_qr_bytes)
    
    # Split into chunks
    chunks = split_data(encrypted_bytes, max_chunk)
    
    # Wrap each chunk with metadata
    parts = []
    for i, chunk in enumerate(chunks, 1):
        part = msgpack({
            'v': 2,
            'p': i,
            't': len(chunks),
            'd': chunk
        })
        parts.append(base64.encode(part))
    
    return parts
```

#### Reconstruction (qr_multi_part.py)

```python
def deserialize_multipart(qr_strings, password):
    # Parse all parts
    parts = [parse_qr(s) for s in qr_strings]
    
    # Validate consistency
    validate_parts(parts)
    
    # Sort by part number
    parts.sort(key=lambda p: p['part_number'])
    
    # Reassemble encrypted data
    encrypted_bytes = b''.join(p['data'] for p in parts)
    encrypted = base64.encode(encrypted_bytes)
    
    # Decrypt and decompress
    package = QrDataProcessor.deserialize(encrypted, password)
    
    # Unpack and validate
    unpacked = msgpack.unpack(package)
    raw_data = unpacked['d']
    stored_hash = unpacked['h']
    
    # Verify integrity
    calculated_hash = sha256(raw_data)
    if calculated_hash != stored_hash:
        raise ValueError("Hash validation failed")
    
    return raw_data
```

## GUI Integration

### Display Window (extra_windows.py)

**Single-Part Display:**
- Simple window with QR image
- Text field shows base64 string
- Single "Save As" button

**Multi-Part Display:**
- Navigation bar with Previous/Next buttons
- Part counter: "Part 3/5"
- QR container (updates on navigation)
- Text preview (truncated)
- Two save buttons:
  - "Save Current": Current QR only
  - "Save All": All QR codes + text files to folder

### Reading Window

**Single QR:**
- Standard text field
- Or file browser for QR image

**Multi-Part:**
- "Add QR Code Image" button
- Counter: "4 QR codes loaded (last: Part 2/5)"
- Automatic validation of part info
- "Clear List" to reset

**Smart Text Parsing:**
- Detects concatenated QR texts
- Splits at `==` boundaries (base64 padding)
- Auto-converts to multi-part array

```python
# Input: "abc123==def456==ghi789=="
# Output: ["abc123==", "def456==", "ghi789=="]
```

## CLI Integration

### Generate Command

```bash
# Automatic multi-part
python -m app.cli generate -i large_file.pdf

# Output naming
# large_file_part1_of_3.png
# large_file_part2_of_3.png
# large_file_part3_of_3.png

# With text export
python -m app.cli generate -i large_file.pdf --save-texts
# Also creates: large_file_qr_texts.txt
```

### Read Command

```bash
# Wildcard (all parts)
python -m app.cli read -i qr_part*.png -o restored.pdf

# Explicit parts
python -m app.cli read -i part1.png part2.png -o file.txt

# Status output:
# INFO: Multi-part QR code detected (part 1/3)
# WARNING: Only 2 of 3 parts loaded!
```

### Decrypt Command

```bash
# From text file
python -m app.cli decrypt --text-file qr_texts.txt -o file.pdf

# Text file format:
# Part 1/3
# <base64 string>
#
# Part 2/3
# <base64 string>
```

## Error Handling

### Common Errors

**"Missing parts: [2, 4]"**
- Thrown when not all parts present
- Lists specific missing part numbers
- User needs to scan missing QR codes

**"Inconsistent total_parts in parts"**
- Parts claim different total counts
- Likely from different files mixed together
- User should verify QR code sources

**"Hash validation failed - data is corrupt"**
- Decryption succeeded but hash mismatch
- Data corruption during transmission
- Or QR codes from different encryptions
- Rescan QR codes with better quality

**"Not a valid multi-part QR"**
- Thrown by `get_part_info()` on invalid format
- QR might be corrupted
- Or from different application

### Validation Steps

1. **Parse Check**: Valid msgpack + base64?
2. **Format Check**: Has v, p, t, d fields?
3. **Consistency Check**: All parts agree on total?
4. **Completeness Check**: All part numbers present?
5. **Reassembly**: Successful decryption?
6. **Hash Check**: Calculated hash matches stored?

## Performance Characteristics

### Time Complexity

- **Generation**: O(n) where n = file size
  - Single encryption pass
  - Splitting is linear
  - QR generation per part: O(1)

- **Reading**: O(m) where m = number of parts
  - Each part parsed independently
  - Sorting: O(m log m) but m is small
  - Single decryption pass

### Memory Usage

- **Generation**: O(n + m×c) where c = chunk size
  - Holds entire file in memory
  - Plus all QR code images

- **Reading**: O(m×c)
  - Accumulates all chunks
  - Then decrypts in one pass

### Optimization Tips

1. **Compression Level**: Level 16 zstd is aggressive
   - Good compression ratio
   - Slower but only done once
   - Consider lower level for huge files

2. **QR Error Correction**: Currently level 1 (L)
   - Lowest error correction
   - Maximizes data capacity
   - Consider level 2 (M) for printing

3. **Chunk Size**: ~2000 bytes
   - Balance between number of QR codes and robustness
   - Could be tuned based on use case

## Security Considerations

### What's Secure

✅ **Encryption**: Same strength as single-part
✅ **Authentication**: MAC included in each part
✅ **Integrity**: Hash validation
✅ **No Partial Decryption**: All parts needed

### What's Visible

❌ **File Size**: Approximate from part count
❌ **Part Count**: Visible in metadata
❌ **Part Numbers**: Order is visible

### Attack Resistance

**Scenario: Attacker has some (not all) parts**
- Cannot decrypt partial data
- Cannot guess missing parts (encrypted)
- Cannot modify parts (MAC will fail)

**Scenario: Attacker swaps parts between files**
- Hash validation will fail
- Total part count inconsistency detected

**Scenario: Attacker reorders parts**
- No problem! System handles any order
- Part numbers ensure correct reassembly

## Backward Compatibility

### Reading Old Single-Part QR Codes

The system auto-detects format:

```python
if is_multipart_qr(qr_text):
    return deserialize_multipart(qr_texts, password)
else:
    return deserialize(qr_text, password)
```

### Version 1 vs Version 2

**Version 1** (no longer generated):
- Hash stored in each part's metadata
- More redundant but slightly less secure

**Version 2** (current):
- Hash stored in encrypted package
- Better security (hash is encrypted)
- Slightly more efficient

Both versions are supported for reading.

## Testing

### Unit Tests

```python
# Test basic multi-part
data = b"Hello" * 1000  # Large enough
parts = serialize_multipart(data, "pass", 500)
assert len(parts) > 1
restored = deserialize_multipart(parts, "pass")
assert restored == data

# Test order independence
import random
shuffled = parts.copy()
random.shuffle(shuffled)
restored = deserialize_multipart(shuffled, "pass")
assert restored == data

# Test missing parts
partial = parts[:-1]  # Missing last part
try:
    deserialize_multipart(partial, "pass")
    assert False, "Should have raised error"
except ValueError as e:
    assert "Missing parts" in str(e)
```

### Integration Tests

```bash
# Create test file
dd if=/dev/urandom of=test.bin bs=1024 count=10

# Generate
python -m app.cli generate -i test.bin -p testpass

# Should create multiple parts
# Verify output
python -m app.cli read -i test_part*.png -p testpass -o restored.bin

# Compare
diff test.bin restored.bin  # Should be identical
```

## Future Improvements

### Potential Enhancements

1. **Reed-Solomon Error Correction**
   - Add redundancy across parts
   - Recover from missing parts (e.g., 3 of 5 needed)

2. **Progressive Decryption**
   - Decrypt and save as parts arrive
   - Useful for very large files

3. **Compression Tuning**
   - Adaptive compression level
   - Based on file type detection

4. **QR Code Optimization**
   - Higher error correction for printing
   - Lower for digital-only use

5. **Metadata Extensions**
   - Original filename
   - File type/MIME
   - Creation timestamp

## Appendix: Format Examples

### Single-Part QR Code

```
iVBORw0KGgoAAAANSUhEUgAAAV4AAAFeAQAAAADlUEq3AAABm0lEQVR4nO2YMY7j...
[Base64 of: msgpack([salt, encrypted_compressed_data])]
```

### Multi-Part QR Code (Version 2)

**Part 1 of 3:**
```
gaR2AqFwAaF0A6Fkxo0A1Z3...
[Base64 of: msgpack({'v': 2, 'p': 1, 't': 3, 'd': chunk1})]
```

**Part 2 of 3:**
```
gaR2AqFwAqF0A6Fkxo0B7K9...
[Base64 of: msgpack({'v': 2, 'p': 2, 't': 3, 'd': chunk2})]
```

**Part 3 of 3:**
```
gaR2AqFwA6F0A6Fkxo0C9M2...
[Base64 of: msgpack({'v': 2, 'p': 3, 't': 3, 'd': chunk3})]
```

### QR Texts File Format

```
# Part 1/3
gaR2AqFwAqF0A6Fkxo0A1Z3dGVzdCBkYXRh...

# Part 2/3
gaR2AqFwAqF0A6Fkxo0B7K9hbm90aGVyIGNo...

# Part 3/3
gaR2AqFwA6F0A6Fkxo0C9M2ZmluYWwgY2h1...
```

---

**For more information, see the main README.md**