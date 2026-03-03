"""Tests for the mock monitor renderer."""

import numpy as np
import pytest

from monitor_eye.mock.renderer import MonitorRenderer


class TestMonitorRenderer:
    @pytest.fixture
    def renderer(self):
        return MonitorRenderer(width=800, height=600)

    def test_render_returns_numpy_array(self, renderer):
        frame = renderer.render()
        assert isinstance(frame, np.ndarray)
        assert frame.shape == (600, 800, 3)

    def test_default_vitals_in_range(self, renderer):
        vitals = renderer.vitals
        assert 60 <= vitals["hr"] <= 100
        assert 90 <= vitals["spo2"] <= 100
        assert 100 <= vitals["nibp_sys"] <= 140
        assert 60 <= vitals["nibp_dia"] <= 90
        assert 12 <= vitals["resp"] <= 20
        assert 360 <= vitals["temp"] <= 375

    def test_set_vitals(self, renderer):
        renderer.set_vitals(hr=150, spo2=85)
        assert renderer.vitals["hr"] == 150
        assert renderer.vitals["spo2"] == 85

    def test_trigger_alarm_sets_alarm_state(self, renderer):
        assert not renderer.alarm_active
        renderer.trigger_alarm("hr_high")
        assert renderer.alarm_active
        assert renderer.alarm_type == "hr_high"

    def test_silence_alarm(self, renderer):
        renderer.trigger_alarm("hr_high")
        renderer.silence_alarm()
        assert not renderer.alarm_active

    def test_render_produces_different_frames(self, renderer):
        frame1 = renderer.render()
        renderer.tick()
        frame2 = renderer.render()
        assert frame1.shape == frame2.shape
