"""Tests for the image matching engine."""

import numpy as np
import cv2
import pytest

from monitor_eye.finder import ImageFinder, Match


class TestMatch:
    def test_match_has_coordinates_and_score(self):
        m = Match(x=100, y=200, width=50, height=30, score=0.95)
        assert m.x == 100
        assert m.y == 200
        assert m.center == (125, 215)
        assert m.score == 0.95

    def test_match_click_point_is_center(self):
        m = Match(x=10, y=20, width=100, height=50, score=0.9)
        assert m.click_point == (60, 45)


class TestImageFinder:
    @pytest.fixture
    def finder(self):
        return ImageFinder(confidence=0.8)

    @pytest.fixture
    def screen_with_red_square(self):
        """800x600 black screen with a 50x50 red square at (200, 150)."""
        img = np.zeros((600, 800, 3), dtype=np.uint8)
        img[150:200, 200:250] = (0, 0, 255)  # BGR red
        return img

    @pytest.fixture
    def red_square_template(self, tmp_path):
        """50x50 red square template saved as PNG."""
        tmpl = np.zeros((50, 50, 3), dtype=np.uint8)
        tmpl[:] = (0, 0, 255)
        path = tmp_path / "red_square.png"
        cv2.imwrite(str(path), tmpl)
        return str(path)

    def test_find_exact_match(self, finder, screen_with_red_square, red_square_template):
        match = finder.find(screen_with_red_square, red_square_template)
        assert match is not None
        assert match.score >= 0.8
        assert abs(match.x - 200) <= 2
        assert abs(match.y - 150) <= 2

    def test_find_returns_none_when_not_found(self, finder, screen_with_red_square, tmp_path):
        tmpl = np.zeros((50, 50, 3), dtype=np.uint8)
        tmpl[:] = (0, 255, 0)
        path = tmp_path / "green_square.png"
        cv2.imwrite(str(path), tmpl)
        match = finder.find(screen_with_red_square, str(path))
        assert match is None

    def test_find_all_returns_multiple(self, finder, tmp_path):
        img = np.zeros((600, 800, 3), dtype=np.uint8)
        img[100:150, 100:150] = (0, 0, 255)
        img[300:350, 400:450] = (0, 0, 255)
        tmpl = np.zeros((50, 50, 3), dtype=np.uint8)
        tmpl[:] = (0, 0, 255)
        path = tmp_path / "red.png"
        cv2.imwrite(str(path), tmpl)
        matches = finder.find_all(img, str(path))
        assert len(matches) >= 2

    def test_find_in_region(self, finder, screen_with_red_square, red_square_template):
        match = finder.find(screen_with_red_square, red_square_template,
                           region=(180, 130, 100, 100))
        assert match is not None
        match = finder.find(screen_with_red_square, red_square_template,
                           region=(500, 400, 100, 100))
        assert match is None
