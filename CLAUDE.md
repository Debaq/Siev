# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

SIEV (Sistema Integrado de Evaluación Vestibular) is a Videonystagmography (VNG) system for medical diagnosis of vestibular disorders. It combines computer vision (YOLOv8), real-time signal processing (Kalman filtering), and hardware integration (ESP32C3 microcontrollers with IMU sensors) to track eye movements and detect nystagmus.

**Current Version**: 0.0.1-alpha (auto-bumped on push to development)
**Main Branch**: alpha_version
**Tech Stack**: Python 3.x, PySide6 (Qt6), OpenCV, Ultralytics YOLOv8, PyTorch

## Development Commands

### Running the Application

```bash
# Using the startup script (recommended)
./siev.sh

# Manual startup
cd ~/Siev
micromamba activate vng
python src/main.py
```

### Environment Setup

```bash
# Create and activate conda environment
micromamba create -n vng python=3.x
micromamba activate vng

# Install dependencies
pip install -r requirements.txt
```

### Testing

```bash
# Run tests (if available)
pytest tests/
```

## Architecture Overview

### Manager Pattern Architecture

SIEV follows a manager-based architecture where high-level managers coordinate specialized subsystems:

- **HardwareManager** (`managers/hardware_manager.py`): Controls all hardware (serial communication, IMU sensors, LED calibration)
- **DataManager** (`managers/data_manager.py`): Manages patient profiles, test results, and data persistence
- **TestManager** (`managers/test_manager.py`): Handles test protocols (caloric, saccades, smooth pursuit, etc.)
- **VideoManager** (`managers/video_manager.py`): Manages video capture, playback, and recording

### Key Processing Pipelines

#### 1. Eye Tracking Pipeline
```
Camera → YOLOv8 Detection → Kalman Filtering → Pixel-to-Degree Conversion → Graph Display
```

- **Model**: `src/models/siev_vng_r01.pt` (YOLOv8 custom trained)
- **Filtering**: `EyeDataProcessor.py` implements Kalman filter with acceleration model
- **Calibration**: `CalibrationManager.py` converts pixels to degrees using IR LED reference points

#### 2. Nystagmus Detection Pipeline
```
Eye Position → Velocity/Acceleration Calculation → Pattern Detection → VCL Measurement
```

- **Detector**: `DetectorNistagmo.py` identifies involuntary eye movements
- **VCL**: Velocity of Slow Component (Velocidad del Componente Lento)

#### 3. Hardware Communication
```
Serial (115200 8N1) → ESP32C3 → IMU (BNO055/ICM20948) → Python Processing
```

- **Protocol**: See `hardware/esp8266_siev/esp8266_siev_protocol.md`
- **Commands**: LED control (L_12_ON, L_14_OFF), IMU data requests
- **Handlers**: `SerialHandler.py` and `serial_thread.py`

### Threading Model

- **Qt Signal/Slot**: All UI updates and cross-thread communication use Qt's signal/slot mechanism
- **Serial Thread**: `SerialReadThread` runs continuously to read hardware data
- **Video Thread**: `video_thread.py` handles camera capture without blocking UI
- **Worker Threads**: Long operations (file processing, calibration) use QThread workers

## Critical Systems

### Calibration System

Two-point calibration using IR LEDs at known positions:

```python
# Geometric constants in CalibrationManager.py
LED_DISTANCE_FROM_MIDLINE = 6.0  # cm - Distance from nose centerline
LED_DISTANCE_FROM_EYE = 9.0      # cm - Perpendicular distance to eye
LED_SEPARATION_TOTAL = 12.0      # cm - Total LED separation
```

The system:
1. Captures eye positions while looking at left LED
2. Captures eye positions while looking at right LED
3. Computes pixel-to-degree conversion factors for each eye
4. Uses theoretical angle between LEDs (~53°) to validate calibration

### Protocol System

`protocol_manager.py` manages test protocols (stored in JSON format):
- **Caloric Tests**: Thermal stimulation (44°C and 30°C for OD/OI)
- **Smooth Pursuit**: Slow eye movement tracking
- **Optokinetic Nystagmus**: Response to moving patterns
- **Saccades**: Rapid eye movement tests
- **Spontaneous Nystagmus**: Resting state detection

Each protocol defines:
- Duration (2-5 minutes typical)
- Stimulus parameters
- Recording settings
- Analysis criteria

### Auto-Update System

`main.py` implements automatic Git-based updates:
- Checks GitHub for updates on startup (15s timeout)
- Shows UpdateDialog if updates available
- Executes `git pull` and `pip install -r requirements.txt`
- Uses `micromamba run` for dependency installation

**Important**: Updates discard local changes with `git reset --hard HEAD`

## File Structure Notes

```
src/
├── main.py                    # Entry point with auto-update system
├── VERSION.json               # Version tracking (auto-bumped by CI)
├── managers/                  # High-level subsystem managers
├── models/
│   ├── data_models.py        # Data structures (nearly empty, check before editing)
│   └── siev_vng_r01.pt       # YOLOv8 trained model for eye detection
├── ui/
│   ├── main_window.py        # Primary window (complex, ~100+ lines init)
│   ├── dialogs/              # Modal dialogs (user management, calibration, etc.)
│   └── views/                # Specialized views (fullscreen video, etc.)
└── utils/                     # Core processing utilities
    ├── CalibrationManager.py  # Pixel-to-degree conversion
    ├── EyeDataProcessor.py    # Kalman filtering (6-state model)
    ├── DetectorNistagmo.py    # Nystagmus detection algorithms
    ├── protocol_manager.py    # Test protocol handling
    ├── SievManager.py         # Patient data management
    ├── graphing/              # Real-time plotting (pyqtgraph)
    │   ├── triple_plot_widget.py  # 3-channel display
    │   └── caloric_graph.py       # Caloric test visualization
    └── video/                 # Video capture/playback
```

## Hardware Integration

### Serial Communication
- **Baudrate**: 115200
- **Format**: 8N1 (8 bits, no parity, 1 stop bit)
- **Timeout**: 2 seconds
- **Terminator**: `\r\n` (CR+LF)

### Supported Hardware
- **ESP32C3**: 4 microcontrollers for LED control and IMU
- **IMU**: BNO055 or ICM20948 (9-axis inertial measurement)
- **Cameras**: USB cameras (V4L2 on Linux, DirectShow on Windows)
- **LEDs**: IR LEDs at 760nm for calibration and illumination

### Camera Resolution Detection
`CameraResolutionDetector.py` automatically detects supported resolutions:
- Preferred: 1920x1080 (Full HD)
- Fallback: 1280x720 (HD) or 640x480 (VGA)

## Development Patterns

### Signal/Slot Usage
Always use Qt signals for cross-component communication:
```python
# Define signals in class
class MyManager(QObject):
    data_ready = Signal(dict)

# Connect in parent
manager.data_ready.connect(self.on_data_received)
```

### State Management
Key state flags tracked in `MainWindow`:
- `is_recording`: Recording in progress
- `is_calibrating`: Calibration active
- `fixed_on_flag`: LED fixation mode
- `current_user_data`: Active patient

### Data Storage
`DataStorage` class handles persistence:
- Patient profiles with metadata
- Test results with timestamps
- Video recordings linked to tests
- Configuration settings

## Internationalization (i18n) and Styling

### Translation System

The application uses a custom i18n system with JSON translation files:

- **Files**: `src/resources/translations/` (es.json, en.json)
- **Manager**: `utils/i18n.py` - TranslationManager class
- **Usage in code**: `self.t('key.path')` in MainWindow, or `get_translation_manager().t('key.path')` elsewhere
- **Auto-detection**: System locale is detected on startup
- **Supported languages**: Spanish (default), English

**Translation keys structure**:
- `app.*` - Application info (title, version)
- `menu.*` - Menu items and submenus
- `tests.*` - Test names (OD/OI 44/30, etc.)
- `controls.*` - Button labels (iniciar, detener, pausar, etc.)
- `parameters.*` - Measurement parameters (amplitud, VCL, etc.)
- `camera.*` - Camera settings labels
- `messages.*` - System messages (error, success, warnings)
- `time.*` - Time-related strings with formatting support

**Example usage**:
```python
# In MainWindow
self.ui.btn_start.setText(self.t('controls.iniciar'))
QMessageBox.warning(self, self.t('messages.error'), "Error message")

# In other modules
from utils.i18n import get_translation_manager
tm = get_translation_manager()
text = tm.t('menu.archivo')
```

### Style System

The application uses QSS stylesheets for theming:

- **Files**: `src/resources/styles/*.qss`
- **Manager**: `utils/style_manager.py` - StyleManager class
- **Current theme**: 'professional' (applied in main.py)
- **Usage**: `get_style_manager().apply_style(app, 'theme_name')`

Styles are automatically detected and can be changed dynamically during runtime.

## CI/CD

### GitHub Actions Workflow
`.github/workflow/version-bump.yml`:
- Triggers on push to `development` branch
- Auto-increments patch version in `VERSION.json`
- Commits with `[skip ci]` to prevent loops

### Branch Strategy
- `main`: Stable production
- `development`: Active development (auto-version-bump)
- `alpha_version`: Alpha releases (main branch for PRs)
- `claude/*`: Automated feature branches

## Known Constraints

1. **Recording Duration**: Max 5 minutes per session (hardware buffer limits)
2. **Calibration**: Requires stable head position and good lighting
3. **Real-time Processing**: Requires i5+ processor for smooth 50Hz data rate
4. **Camera Compatibility**: Some USB cameras may not support V4L2 controls on Linux
5. **Serial Port**: May require udev rules on Linux for non-root access

## Important Notes

- The codebase uses Spanish comments and variable names in many places
- PDF generation uses `vng_pdf_generator.py` with matplotlib-based charts
- Kalman filter in `EyeDataProcessor.py` uses 6-state model: [x, y, vel_x, vel_y, acc_x, acc_y]
- Eye detection confidence threshold typically set around 0.5-0.7
- IMU sampling rate: 50Hz for optimal nystagmus detection
- Video recordings are synchronized with graph data using timestamps
