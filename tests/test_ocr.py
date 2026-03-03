"""Tests for the OCR preprocessing pipeline."""

import numpy as np
import cv2
import pytest

from monitor_eye.ocr import OCREngine


class TestOCRPreprocessing:
    @pytest.fixture
    def engine(self):
        return OCREngine()

    def _make_text_image(self, text: str, font_size: float = 1.0,
                         bg_color: int = 0, fg_color: int = 255,
                         height: int = 60, width: int = 200) -> np.ndarray:
        """Generate a test image with text."""
        img = np.full((height, width), bg_color, dtype=np.uint8)
        cv2.putText(img, text, (10, height - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, font_size, fg_color, 2)
        return img

    def test_read_number_white_on_black(self, engine):
        """White text on black background — SikuliX Issue #440."""
        img = self._make_text_image("72", bg_color=0, fg_color=255)
        result = engine.read_number(img)
        assert result == 72

    def test_read_number_black_on_white(self, engine):
        """Normal dark text on light background."""
        img = self._make_text_image("98", bg_color=255, fg_color=0)
        result = engine.read_number(img)
        assert result == 98

    def test_read_number_small_font(self, engine):
        """Small font text — SikuliX small font issue."""
        img = self._make_text_image("120", font_size=0.6,
                                    height=30, width=120,
                                    bg_color=0, fg_color=255)
        result = engine.read_number(img)
        assert result == 120

    def test_read_number_with_slash(self, engine):
        """Blood pressure format like 120/80."""
        img = self._make_text_image("120/80", font_size=0.8,
                                    width=200, bg_color=0, fg_color=255)
        result = engine.read_text(img)
        assert "120" in result and "80" in result

    def test_read_number_returns_none_for_no_digits(self, engine):
        """Blank image should return None."""
        img = np.zeros((60, 200), dtype=np.uint8)
        result = engine.read_number(img)
        assert result is None

    def test_preprocess_inverts_dark_background(self, engine):
        """Verify preprocessing auto-inverts dark backgrounds."""
        dark_bg = np.full((60, 200), 30, dtype=np.uint8)
        processed = engine.preprocess(dark_bg)
        assert np.mean(processed) > 128

    def test_preprocess_scales_small_images(self, engine):
        """Verify preprocessing scales up small images."""
        small = np.full((15, 60), 200, dtype=np.uint8)
        processed = engine.preprocess(small)
        assert processed.shape[0] >= 50
