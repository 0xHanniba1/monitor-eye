"""pytest fixtures for MonitorEye testing."""

import pytest

from monitor_eye.screen import MonitorScreen


@pytest.fixture
def monitor_screen():
    """Provide a MonitorScreen connected to the built-in mock server.

    Usage in test files:
        def test_something(monitor_screen):
            hr = monitor_screen.region(20, 40, 200, 80).read_number()
            assert hr is not None
    """
    screen = MonitorScreen.from_mock()
    yield screen
    screen.disconnect()
