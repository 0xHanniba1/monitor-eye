"""MonitorEye — Pure Python GUI testing toolkit for patient monitors."""

__version__ = "0.1.0"

from monitor_eye.screen import MonitorScreen, Region
from monitor_eye.finder import Match
from monitor_eye.exceptions import FindFailed, ConnectionError

__all__ = ["MonitorScreen", "Region", "Match", "FindFailed", "ConnectionError"]
