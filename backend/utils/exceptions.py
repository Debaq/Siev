"""
Custom exceptions for the SIEV system.
"""

class SievError(Exception):
    """Base class for SIEV exceptions."""
    pass

class HardwareError(SievError):
    """Raised when a hardware communication error occurs."""
    def __init__(self, message: str, detail: str = None):
        super().__init__(message)
        self.detail = detail

class CameraError(HardwareError):
    """Raised when a camera-related error occurs."""
    pass

class SerialError(HardwareError):
    """Raised when a serial communication error occurs."""
    pass

class CalibrationError(SievError):
    """Raised when calibration fails."""
    pass
