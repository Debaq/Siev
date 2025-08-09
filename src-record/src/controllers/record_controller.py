"""Recording controller module."""


class RecordController:
    """Manages video recording operations."""

    def start(self) -> None:
        """Start recording."""
        raise NotImplementedError

    def stop(self) -> None:
        """Stop recording."""
        raise NotImplementedError
