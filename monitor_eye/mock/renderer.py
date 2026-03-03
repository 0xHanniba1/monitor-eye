"""Mock patient monitor screen renderer using Pillow."""

import math
import random
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont


class MonitorRenderer:
    """Renders a simulated patient monitor display as numpy arrays."""

    BG_COLOR = (0, 0, 0)
    HR_COLOR = (0, 255, 0)
    SPO2_COLOR = (0, 255, 255)
    NIBP_COLOR = (255, 255, 255)
    RESP_COLOR = (255, 255, 0)
    TEMP_COLOR = (200, 200, 200)
    ALARM_COLOR = (255, 0, 0)

    def __init__(self, width: int = 800, height: int = 600):
        self.width = width
        self.height = height
        self.vitals = {
            "hr": 75,
            "spo2": 98,
            "nibp_sys": 120,
            "nibp_dia": 80,
            "resp": 16,
            "temp": 368,
        }
        self.alarm_active = False
        self.alarm_type: Optional[str] = None
        self._tick_count = 0

    def set_vitals(self, **kwargs: int) -> None:
        """Update one or more vital sign values."""
        for key, value in kwargs.items():
            if key in self.vitals:
                self.vitals[key] = value

    def trigger_alarm(self, alarm_type: str) -> None:
        """Activate an alarm with the given type identifier."""
        self.alarm_active = True
        self.alarm_type = alarm_type

    def silence_alarm(self) -> None:
        """Deactivate the current alarm."""
        self.alarm_active = False
        self.alarm_type = None

    def tick(self) -> None:
        """Advance the simulation by one step, adding small random variation."""
        self._tick_count += 1
        self.vitals["hr"] += random.randint(-1, 1)
        self.vitals["hr"] = max(40, min(200, self.vitals["hr"]))
        self.vitals["spo2"] += random.choice([-1, 0, 0, 0, 1])
        self.vitals["spo2"] = max(80, min(100, self.vitals["spo2"]))
        self.vitals["resp"] += random.choice([-1, 0, 0, 1])
        self.vitals["resp"] = max(8, min(30, self.vitals["resp"]))

    def render(self) -> np.ndarray:
        """Render the current monitor state and return as a numpy BGR array."""
        img = Image.new("RGB", (self.width, self.height), self.BG_COLOR)
        draw = ImageDraw.Draw(img)

        # Try system fonts, fall back to default
        try:
            font_large = ImageFont.truetype(
                "/System/Library/Fonts/Helvetica.ttc", 48
            )
            font_label = ImageFont.truetype(
                "/System/Library/Fonts/Helvetica.ttc", 18
            )
        except (OSError, IOError):
            try:
                font_large = ImageFont.truetype(
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48
                )
                font_label = ImageFont.truetype(
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18
                )
            except (OSError, IOError):
                font_large = ImageFont.load_default()
                font_label = ImageFont.load_default()

        # Heart Rate
        draw.text((30, 20), "HR", fill=self.HR_COLOR, font=font_label)
        draw.text(
            (30, 50), str(self.vitals["hr"]), fill=self.HR_COLOR, font=font_large
        )
        draw.text((160, 70), "bpm", fill=self.HR_COLOR, font=font_label)

        # SpO2
        draw.text((30, 140), "SpO2", fill=self.SPO2_COLOR, font=font_label)
        draw.text(
            (30, 170),
            str(self.vitals["spo2"]),
            fill=self.SPO2_COLOR,
            font=font_large,
        )
        draw.text((160, 190), "%", fill=self.SPO2_COLOR, font=font_label)

        # NIBP
        draw.text((300, 20), "NIBP", fill=self.NIBP_COLOR, font=font_label)
        nibp_text = f"{self.vitals['nibp_sys']}/{self.vitals['nibp_dia']}"
        draw.text((300, 50), nibp_text, fill=self.NIBP_COLOR, font=font_large)
        draw.text((520, 70), "mmHg", fill=self.NIBP_COLOR, font=font_label)

        # Resp
        draw.text((300, 140), "RESP", fill=self.RESP_COLOR, font=font_label)
        draw.text(
            (300, 170),
            str(self.vitals["resp"]),
            fill=self.RESP_COLOR,
            font=font_large,
        )
        draw.text((420, 190), "rpm", fill=self.RESP_COLOR, font=font_label)

        # Temp
        temp_str = f"{self.vitals['temp'] / 10:.1f}"
        draw.text((550, 140), "TEMP", fill=self.TEMP_COLOR, font=font_label)
        draw.text(
            (550, 170), temp_str, fill=self.TEMP_COLOR, font=font_large
        )
        draw.text((700, 190), "\u00b0C", fill=self.TEMP_COLOR, font=font_label)

        # ECG waveform
        wave_y_base = 350
        wave_height = 40
        for x in range(self.width):
            phase = (x + self._tick_count * 5) * 0.05
            if (x % 160) < 10:
                y = wave_y_base - int(
                    wave_height * 2 * math.sin(phase * 5)
                )
            else:
                y = wave_y_base - int(
                    wave_height * 0.3 * math.sin(phase)
                )
            y = max(280, min(420, y))
            draw.point((x, y), fill=self.HR_COLOR)

        # Alarm bar
        if self.alarm_active:
            draw.rectangle(
                [(0, 0), (self.width, 18)], fill=self.ALARM_COLOR
            )
            alarm_text = f"ALARM: {self.alarm_type}"
            draw.text(
                (10, 0), alarm_text, fill=(255, 255, 255), font=font_label
            )

        # Silence button
        draw.rectangle(
            [(650, 550), (780, 590)], outline=(128, 128, 128)
        )
        draw.text(
            (665, 560), "SILENCE", fill=(128, 128, 128), font=font_label
        )

        # Convert PIL RGB to numpy BGR (OpenCV format)
        arr = np.array(img)
        return arr[:, :, ::-1].copy()  # RGB to BGR
