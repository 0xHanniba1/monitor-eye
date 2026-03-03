"""Tests for the pytest plugin fixture."""

from monitor_eye.screen import MonitorScreen


def test_monitor_fixture_works(monitor_screen):
    """Verify the fixture provides a working MonitorScreen."""
    assert isinstance(monitor_screen, MonitorScreen)
    frame = monitor_screen.capture()
    assert frame is not None
    assert frame.shape[0] > 0
