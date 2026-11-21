"""Tests for ImageFramingChecker."""

from pathlib import Path

from PIL import Image, ImageDraw

from workbench.image_framing import ImageFramingChecker


def save_box(path: Path, box: tuple[int, int, int, int]) -> Path:
    image = Image.new("RGB", (100, 100), (50, 50, 50))
    ImageDraw.Draw(image).rectangle(box, fill=(200, 150, 50))
    image.save(path)
    return path


def test_centered_subject_passes(tmp_path: Path) -> None:
    assert ImageFramingChecker().problems(save_box(tmp_path / "a.png", (20, 30, 80, 70))) == ()


def test_off_center_subject_fails(tmp_path: Path) -> None:
    problems = ImageFramingChecker().problems(save_box(tmp_path / "a.png", (5, 5, 60, 50)))
    assert any("off-center" in line for line in problems)


def test_subject_on_edge_fails(tmp_path: Path) -> None:
    problems = ImageFramingChecker().problems(save_box(tmp_path / "a.png", (0, 20, 100, 80)))
    assert any("edge" in line for line in problems)


def test_busy_image_passes(tmp_path: Path) -> None:
    image = Image.effect_noise((100, 100), 80).convert("RGB")
    image.save(tmp_path / "a.png")
    assert ImageFramingChecker().problems(tmp_path / "a.png") == ()
