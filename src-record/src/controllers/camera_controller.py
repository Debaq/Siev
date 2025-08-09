"""Camera controller module."""


class CameraController:
    """Handles camera operations."""

    def start_camera(self, camera_id: int) -> None:
        """Start camera feed for the given camera ID."""
        raise NotImplementedError

    def get_frame(self):
        """Retrieve the latest frame from the camera."""
        raise NotImplementedError
