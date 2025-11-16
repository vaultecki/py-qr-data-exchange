# Installation Guide

Detailed installation instructions for PyQrDataExchange.

## Quick Start

```bash
# Standard installation (recommended)
pip install -r requirements.txt

# Run the application
python run_app.py
```

## Installation Options

### 1. Standard Installation (Recommended)

Best for most users - includes all features with optimal QR code detection.

```bash
pip install -r requirements.txt
```

**Includes:**
- ✅ qreader for best QR code detection
- ✅ OpenCV as fallback
- ✅ All core features

**Installation size:** ~500 MB  
**Pros:** Best detection, all features  
**Cons:** Larger download

### 2. Minimal Installation

For embedded systems, Docker containers, or size-constrained environments.

```bash
pip install -r requirements-minimal.txt
```

**Includes:**
- ✅ OpenCV only (no qreader)
- ✅ All core features
- ⚠️ Lower QR detection rate for difficult images

**Installation size:** ~150 MB  
**Pros:** Smaller footprint  
**Cons:** Less robust QR detection

### 3. Development Installation

For contributors and developers.

```bash
pip install -r requirements-dev.txt
```

**Includes:**
- ✅ All standard dependencies
- ✅ Testing frameworks (pytest)
- ✅ Code quality tools (pylint, flake8, black)
- ✅ Type checking (mypy)
- ✅ Documentation tools (sphinx)

**Installation size:** ~700 MB

## Platform-Specific Instructions

### Windows

#### Prerequisites
1. **Python 3.7+**: Download from [python.org](https://www.python.org/downloads/)
2. **pip**: Included with Python

#### Installation
```powershell
# Open PowerShell or Command Prompt
git clone <repository-url>
cd py-qr-data-exchange

# Install dependencies
pip install -r requirements.txt

# Run application
python run_app.py
```

#### Troubleshooting

**Problem:** `pip` not recognized
```powershell
# Add Python to PATH or use full path
C:\Python312\Scripts\pip install -r requirements.txt
```

**Problem:** Microsoft Visual C++ error
```powershell
# Install Visual C++ Build Tools
# Download from: https://visualstudio.microsoft.com/downloads/
# Or install specific packages:
pip install --only-binary :all: opencv-python
```

### macOS

#### Prerequisites
1. **Python 3.7+**: Pre-installed or via Homebrew
2. **Homebrew** (optional): `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`

#### Installation
```bash
# Using system Python
pip3 install -r requirements.txt

# Or with Homebrew Python
brew install python3
pip3 install -r requirements.txt

# Run application
python3 run_app.py
```

#### Troubleshooting

**Problem:** Permission denied
```bash
# Use user installation
pip3 install --user -r requirements.txt
```

**Problem:** SSL certificate error
```bash
# Update certificates
/Applications/Python\ 3.*/Install\ Certificates.command
```

### Linux

#### Ubuntu/Debian

```bash
# Install system dependencies
sudo apt update
sudo apt install python3 python3-pip python3-tk

# Clone repository
git clone <repository-url>
cd py-qr-data-exchange

# Install Python dependencies
pip3 install -r requirements.txt

# Run application
python3 run_app.py
```

#### Fedora/RHEL/CentOS

```bash
# Install system dependencies
sudo dnf install python3 python3-pip python3-tkinter

# Install Python dependencies
pip3 install -r requirements.txt

# Run application
python3 run_app.py
```

#### Arch Linux

```bash
# Install system dependencies
sudo pacman -S python python-pip tk

# Install Python dependencies
pip install -r requirements.txt

# Run application
python run_app.py
```

#### Troubleshooting

**Problem:** `tkinter` not found
```bash
# Ubuntu/Debian
sudo apt install python3-tk

# Fedora
sudo dnf install python3-tkinter

# Arch
sudo pacman -S tk
```

**Problem:** Permission issues
```bash
# Use virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Virtual Environment (Recommended)

Using a virtual environment isolates dependencies and prevents conflicts.

### Create Virtual Environment

**Windows:**
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Deactivate Virtual Environment

```bash
deactivate
```

## Docker Installation (Optional)

For containerized deployment:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements-minimal.txt .
RUN pip install --no-cache-dir -r requirements-minimal.txt

# Copy application
COPY . .

# Run CLI by default
ENTRYPOINT ["python", "-m", "app.cli"]
```

Build and run:
```bash
docker build -t pyqrdataexchange .
docker run -v $(pwd)/data:/app/data pyqrdataexchange generate -i /app/data/file.txt
```

## Verification

Verify installation is working:

```bash
# Test imports
python -c "from app import main; print('✓ Installation successful')"

# Test QR reader
python -c "from app import service; print('✓ QR reader:', 'qreader' if 'qreader' in str(service.__file__) else 'opencv')"

# Run tests (if dev install)
pytest

# Start GUI
python run_app.py
```

## Dependency Details

### Core Dependencies

| Package | Version | Purpose | Size |
|---------|---------|---------|------|
| Pillow | ≥10.0.0 | Image handling | ~15 MB |
| qrcode | ≥7.4.0 | QR generation | ~1 MB |
| qreader | ≥3.0.0 | QR reading (advanced) | ~400 MB |
| opencv-python | ≥4.8.0 | QR reading (fallback) | ~100 MB |
| PyNaCl | ≥1.5.0 | Encryption | ~5 MB |
| msgpack | ≥1.0.0 | Serialization | ~1 MB |
| pyzstd | ≥0.15.0 | Compression | ~2 MB |

### Why These Versions?

- **Pillow 10.0+**: Security fixes, better image format support
- **qrcode 7.4+**: Improved QR code generation
- **qreader 3.0+**: Latest detection algorithms
- **opencv-python 4.8+**: Stable API, good performance
- **PyNaCl 1.5+**: Security updates
- **msgpack 1.0+**: Performance improvements
- **pyzstd 0.15+**: Better compression ratios

## Upgrading

### Update All Dependencies

```bash
pip install --upgrade -r requirements.txt
```

### Update Specific Package

```bash
pip install --upgrade qreader
```

### Check for Updates

```bash
pip list --outdated
```

## Uninstallation

### Remove Virtual Environment

```bash
# Deactivate first
deactivate

# Remove directory
rm -rf venv  # Linux/macOS
rmdir /s venv  # Windows
```

### Uninstall Packages

```bash
pip uninstall -y pillow qrcode qreader opencv-python pynacl msgpack pyzstd
```

## Troubleshooting Common Issues

### qreader Installation Fails

**Problem:** Large download or build errors

**Solution 1 - Use minimal installation:**
```bash
pip install -r requirements-minimal.txt
```

**Solution 2 - Install PyTorch separately:**
```bash
# CPU-only version (smaller)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install qreader
```

### OpenCV Import Error

**Problem:** `ImportError: libGL.so.1: cannot open shared object file`

**Solution (Linux):**
```bash
sudo apt install libgl1-mesa-glx
```

### PyNaCl Build Error

**Problem:** `error: Microsoft Visual C++ 14.0 is required`

**Solution (Windows):**
```bash
# Install pre-built wheel
pip install --only-binary :all: pynacl
```

### tkinter Not Found (GUI)

**Problem:** `ModuleNotFoundError: No module named 'tkinter'`

**Solution:**
```bash
# Ubuntu/Debian
sudo apt install python3-tk

# macOS (should be included)
brew install python-tk

# Windows (reinstall Python with tcl/tk option)
```

### Permission Denied

**Problem:** `ERROR: Could not install packages due to an EnvironmentError`

**Solution:**
```bash
# Option 1: Use --user flag
pip install --user -r requirements.txt

# Option 2: Use virtual environment (better)
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

### Out of Memory (qreader)

**Problem:** Installation or runtime out of memory

**Solution:**
```bash
# Use minimal installation with OpenCV
pip install -r requirements-minimal.txt
```

## Advanced Configuration

### Custom Package Locations

```bash
# Install to specific directory
pip install -r requirements.txt --target=/custom/path

# Add to Python path
export PYTHONPATH=/custom/path:$PYTHONPATH  # Linux/macOS
set PYTHONPATH=C:\custom\path;%PYTHONPATH%  # Windows
```

### Offline Installation

```bash
# On machine with internet:
pip download -r requirements.txt -d ./packages

# Transfer ./packages to offline machine, then:
pip install --no-index --find-links=./packages -r requirements.txt
```

### Pinning Versions

For reproducible installations, pin exact versions:

```bash
# Generate exact versions
pip freeze > requirements-locked.txt

# Install exact versions
pip install -r requirements-locked.txt
```

## Getting Help

If you encounter issues:

1. **Check logs**: Run with `-v` flag for verbose output
   ```bash
   python -m app.cli generate -i file.txt -v
   ```

2. **Verify Python version**: 
   ```bash
   python --version  # Should be 3.7+
   ```

3. **Check installed packages**:
   ```bash
   pip list
   ```

4. **Test individual components**:
   ```bash
   python -c "import PIL; print('Pillow:', PIL.__version__)"
   python -c "import cv2; print('OpenCV:', cv2.__version__)"
   python -c "import qreader; print('qreader:', qreader.__version__)"
   ```

5. **Create minimal test case**:
   ```bash
   python -m app.qr_data_class  # Test encryption
   python -m app.service         # Test QR generation
   ```

## Next Steps

After successful installation:

1. **Read the README**: `README.md` for usage instructions
2. **Try examples**: See "Examples" section in README
3. **Run GUI**: `python run_app.py`
4. **Use CLI**: `python -m app.cli --help`

---

**Need more help?** Check the main README.md or open an issue on the project repository.
