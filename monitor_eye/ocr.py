"""OCR engine optimized for patient monitor digit recognition."""

from typing import Optional

import cv2
import numpy as np
import pytesseract


class OCREngine:
    """OCR engine with preprocessing pipeline for medical monitor displays."""

    DIGIT_WHITELIST = "0123456789./"
    TARGET_HEIGHT = 60
    MIN_HEIGHT = 50

    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """Preprocessing pipeline that fixes SikuliX's OCR weaknesses.

        Steps:
        1. Convert to grayscale if needed
        2. Auto-invert dark backgrounds (fixes SikuliX Issue #440)
        3. Scale up small images (fixes small font recognition)
        4. Otsu binarization for clean digit edges
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Auto-invert: dark background → light background
        if np.mean(gray) < 128:
            gray = cv2.bitwise_not(gray)

        # Scale up small images for better OCR accuracy
        h = gray.shape[0]
        if h < self.MIN_HEIGHT:
            scale = self.TARGET_HEIGHT / h
            gray = cv2.resize(gray, None, fx=scale, fy=scale,
                              interpolation=cv2.INTER_CUBIC)

        # Otsu binarization
        _, binary = cv2.threshold(gray, 0, 255,
                                  cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Dilate to thicken thin strokes (helps with small/thin fonts)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        binary = cv2.dilate(binary, kernel, iterations=1)

        return binary

    def read_text(self, image: np.ndarray) -> str:
        """Read text from an image, optimized for digits and slash.

        Args:
            image: Input image (grayscale or BGR).

        Returns:
            Recognized text string, stripped of whitespace.
        """
        processed = self.preprocess(image)
        config = f"--psm 7 -c tessedit_char_whitelist={self.DIGIT_WHITELIST}"
        text = pytesseract.image_to_string(processed, config=config)
        return text.strip()

    def read_number(self, image: np.ndarray) -> Optional[int]:
        """Read an integer from an image.

        Args:
            image: Input image (grayscale or BGR).

        Returns:
            Recognized integer, or None if no digits found.
        """
        text = self.read_text(image)
        digits = "".join(c for c in text if c.isdigit())
        if not digits:
            return None
        return int(digits)
