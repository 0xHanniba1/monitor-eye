"""MonitorEye custom exceptions."""


class MonitorEyeError(Exception):
    """Base exception for MonitorEye."""


class FindFailed(MonitorEyeError):
    """Raised when an image pattern cannot be found on screen."""

    def __init__(self, pattern: str, timeout: float = 0):
        self.pattern = pattern
        self.timeout = timeout
        msg = f"FindFailed: '{pattern}'"
        if timeout:
            msg += f" (waited {timeout}s)"
        super().__init__(msg)


class ConnectionError(MonitorEyeError):
    """Raised when VNC connection fails."""

    def __init__(self, host: str, port: int, reason: str = ""):
        self.host = host
        self.port = port
        msg = f"Cannot connect to {host}:{port}"
        if reason:
            msg += f" — {reason}"
        super().__init__(msg)
