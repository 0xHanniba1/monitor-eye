"""Image matching engine using OpenCV template matching."""

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np


@dataclass
class Match:
    """Represents a found image match on screen."""

    x: int
    y: int
    width: int
    height: int
    score: float

    @property
    def center(self) -> tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)

    @property
    def click_point(self) -> tuple[int, int]:
        return self.center


class ImageFinder:
    """Finds template images within a screen capture using OpenCV."""

    def __init__(self, confidence: float = 0.8):
        self.confidence = confidence

    def _load_template(self, template_path: str) -> np.ndarray:
        img = cv2.imread(template_path)
        if img is None:
            raise FileNotFoundError(f"Template not found: {template_path}")
        return img

    def _crop_region(self, screen: np.ndarray,
                     region: Optional[tuple[int, int, int, int]]) -> tuple[np.ndarray, int, int]:
        if region is None:
            return screen, 0, 0
        x, y, w, h = region
        return screen[y:y + h, x:x + w], x, y

    def find(self, screen: np.ndarray, template_path: str,
             region: Optional[tuple[int, int, int, int]] = None) -> Optional[Match]:
        template = self._load_template(template_path)
        cropped, ox, oy = self._crop_region(screen, region)

        if (template.shape[0] > cropped.shape[0]
                or template.shape[1] > cropped.shape[1]):
            return None

        result = cv2.matchTemplate(cropped, template, cv2.TM_CCORR_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val < self.confidence:
            return None

        h, w = template.shape[:2]
        return Match(
            x=max_loc[0] + ox,
            y=max_loc[1] + oy,
            width=w,
            height=h,
            score=float(max_val),
        )

    def find_all(self, screen: np.ndarray, template_path: str,
                 region: Optional[tuple[int, int, int, int]] = None) -> list[Match]:
        template = self._load_template(template_path)
        cropped, ox, oy = self._crop_region(screen, region)

        if (template.shape[0] > cropped.shape[0]
                or template.shape[1] > cropped.shape[1]):
            return []

        result = cv2.matchTemplate(cropped, template, cv2.TM_CCORR_NORMED)
        locations = np.where(result >= self.confidence)
        h, w = template.shape[:2]

        matches = []
        for pt in zip(*locations[::-1]):
            matches.append(Match(
                x=int(pt[0]) + ox,
                y=int(pt[1]) + oy,
                width=w,
                height=h,
                score=float(result[pt[1], pt[0]]),
            ))

        if not matches:
            return []
        matches.sort(key=lambda m: m.score, reverse=True)
        filtered = []
        for m in matches:
            too_close = False
            for kept in filtered:
                if abs(m.x - kept.x) < w // 2 and abs(m.y - kept.y) < h // 2:
                    too_close = True
                    break
            if not too_close:
                filtered.append(m)
        return filtered
