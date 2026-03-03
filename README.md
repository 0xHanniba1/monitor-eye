# MonitorEye

Pure Python GUI testing toolkit for patient monitors — a lightweight SikuliX alternative.

## Why MonitorEye?

SikuliX is the de facto open-source GUI automation tool, but it has critical limitations for embedded medical device testing:

| Problem (SikuliX) | Solution (MonitorEye) |
|---|---|
| Jython 2.7 only | Python 3.9+ |
| Java dependency (~80MB) | `pip install` (~5MB) |
| VNC protocol bugs (RFB 3.x only, special keys fail) | vncdotool (RFB 3.3-3.8) |
| OCR digit accuracy ~10% on small/inverted text | Preprocessing pipeline with auto-invert, upscale, digit whitelist |
| No pytest integration | Native pytest fixtures |
| No headless CI/CD | Headless by default |

## Quick Start

```bash
# System dependency
brew install tesseract  # macOS
# apt install tesseract-ocr  # Linux

# Install MonitorEye
cd monitor-eye
pip install -e ".[dev]"

# Run example tests (uses built-in mock — no real hardware needed)
pytest examples/test_comen_monitor.py -v
```

## Usage

```python
from monitor_eye import MonitorScreen

# Connect to mock server (no hardware needed)
screen = MonitorScreen.from_mock()

# Or connect to a real monitor via VNC
# screen = MonitorScreen("192.168.1.100", port=5900)

# Read heart rate via OCR
hr = screen.region(20, 40, 200, 80).read_number()
print(f"Heart Rate: {hr} bpm")

# Find and click an image pattern
screen.click("alarm_icon.png")

# Capture screenshot
screen.capture("evidence/screenshot.png")

screen.disconnect()
```

## pytest Fixture

MonitorEye registers a `monitor_screen` fixture automatically:

```python
def test_heart_rate(monitor_screen):
    hr = monitor_screen.region(20, 40, 200, 80).read_number()
    assert hr is None or 30 < hr < 250

def test_alarm_silence(monitor_screen):
    monitor_screen._mock_server.renderer.trigger_alarm("hr_high")
    monitor_screen._conn.click(715, 570)
    assert not monitor_screen._mock_server.renderer.alarm_active
```

## Architecture

```
MonitorScreen           ← User-facing API
├── VNCConnection       ← vncdotool wrapper (CLI subprocess)
├── ImageFinder         ← OpenCV template matching + NMS
├── OCREngine           ← Tesseract + preprocessing pipeline
└── MockVNCServer       ← Built-in RFB 3.3 server for testing
    └── MonitorRenderer ← Pillow-based fake monitor display
```

### OCR Preprocessing Pipeline

Solves three specific SikuliX defects:

```
Raw image → Grayscale → Auto-invert (dark bg) → Scale up (small font)
  → Morphological dilate → OTSU binarize → Tesseract (digit whitelist)
```

1. **Auto-invert** — fixes white-on-black text (SikuliX Issue #440)
2. **Scale up** — fixes small font (<12px) recognition failure
3. **Digit whitelist** — fixes "13" → "'|3" misrecognition

## Project Structure

```
monitor-eye/
├── monitor_eye/
│   ├── __init__.py          # Public API exports
│   ├── screen.py            # MonitorScreen + Region
│   ├── connection.py        # VNC connection (vncdotool)
│   ├── finder.py            # Image matching (OpenCV)
│   ├── ocr.py               # OCR engine (Tesseract)
│   ├── exceptions.py        # FindFailed, ConnectionError
│   ├── pytest_plugin.py     # monitor_screen fixture
│   └── mock/
│       ├── vnc_server.py    # Minimal RFB 3.3 VNC server
│       └── renderer.py      # Pillow monitor display renderer
├── tests/                   # 41 tests, all passing
├── examples/
│   └── test_comen_monitor.py
└── pyproject.toml
```

## Requirements

- Python 3.9+
- Tesseract OCR (`brew install tesseract` / `apt install tesseract-ocr`)

## Running Tests

```bash
pytest tests/ examples/ -v
```

## Target Device

Designed for COMEN patient monitors (C60/C80/K12 series) but works with any device accessible via VNC.

## License

MIT
