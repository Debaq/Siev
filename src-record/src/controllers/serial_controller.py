"""Serial controller module."""


class SerialController:
    """Wraps serial hardware interactions."""

    def open(self) -> None:
        """Open the serial connection."""
        raise NotImplementedError

    def close(self) -> None:
        """Close the serial connection."""
        raise NotImplementedError
