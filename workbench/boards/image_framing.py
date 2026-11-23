"""Find render PNGs whose subject sits off-center or touches the edge."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops, UnidentifiedImageError

CENTER_TOLERANCE = 0.04
EDGE_MARGIN = 0.02
BACKGROUND_TOLERANCE = 8


@dataclass(frozen=True)
class SubjectFrame:
    left: float
    top: float
    right: float
    bottom: float


class ImageFramingChecker:
    """Check a PNG on a plain background. A photo or screenshot has no plain background and passes."""

    def problems(self, image_path: Path) -> tuple[str, ...]:
        try:
            with Image.open(image_path) as image:
                frame = self._subject_frame(image.convert("RGB"))
        except UnidentifiedImageError:
            return ()
        if frame is None:
            return ()
        return self._edge_problems(frame) + self._center_problems(frame)

    def _subject_frame(self, image: Image.Image) -> SubjectFrame | None:
        width, height = image.size
        background = image.getpixel((0, 0))
        corners = ((width - 1, 0), (0, height - 1), (width - 1, height - 1))
        if any(self._differs(image.getpixel(corner), background) for corner in corners):
            return None
        difference = ImageChops.difference(image, Image.new("RGB", image.size, background))
        box = difference.convert("L").point(lambda v: 255 if v > BACKGROUND_TOLERANCE else 0).getbbox()
        if box is None:
            return None
        return SubjectFrame(box[0] / width, box[1] / height, box[2] / width, box[3] / height)

    def _differs(self, pixel: tuple[int, ...], background: tuple[int, ...]) -> bool:
        return any(abs(a - b) > BACKGROUND_TOLERANCE for a, b in zip(pixel, background))

    def _edge_problems(self, frame: SubjectFrame) -> tuple[str, ...]:
        touches_edge = (frame.left < EDGE_MARGIN or frame.top < EDGE_MARGIN
                        or 1 - frame.right < EDGE_MARGIN or 1 - frame.bottom < EDGE_MARGIN)
        return ("subject touches the image edge: leave a margin of at least 2%",) if touches_edge else ()

    def _center_problems(self, frame: SubjectFrame) -> tuple[str, ...]:
        off_x = (frame.left + frame.right) / 2 - 0.5
        off_y = (frame.top + frame.bottom) / 2 - 0.5
        if abs(off_x) <= CENTER_TOLERANCE and abs(off_y) <= CENTER_TOLERANCE:
            return ()
        return (f"subject is off-center by {off_x:+.0%} x, {off_y:+.0%} y: center it in the frame",)
