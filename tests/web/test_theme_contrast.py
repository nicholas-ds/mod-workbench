"""Both themes keep dark ink readable on every clay and accent color (design standard rule 4)."""

import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[2] / "web"
MINIMUM_CONTRAST = 4.5
SURFACE_PREFIXES = ("clay-", "accent-on-")
NOT_A_SURFACE = ("clay-card", "clay-well", "clay-field", "clay-lit", "clay-shadow", "clay-dent", "clay-grain")


CALM_MARKER = ':root[data-theme="calm"]'


def read_hex_tokens(css: str) -> dict[str, str]:
    return dict(re.findall(r"--([a-z-]+):\s*(#[0-9a-fA-F]{6});", css))


def read_themes() -> tuple[dict[str, str], dict[str, str]]:
    classic_css, calm_css = (WEB / "tokens.css").read_text(encoding="utf-8").split(CALM_MARKER)
    return read_hex_tokens(classic_css), read_hex_tokens(calm_css)


def luminance(hex_color: str) -> float:
    channels = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(first: str, second: str) -> float:
    lighter, darker = sorted((luminance(first), luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def surface_colors(tokens: dict[str, str]) -> dict[str, str]:
    return {name: value for name, value in tokens.items()
            if name.startswith(SURFACE_PREFIXES) and name not in NOT_A_SURFACE}


def test_classic_surfaces_keep_ink_readable() -> None:
    classic, _ = read_themes()
    for name, color in surface_colors(classic).items():
        assert contrast(color, classic["void"]) >= MINIMUM_CONTRAST, name


def test_calm_surfaces_keep_ink_readable() -> None:
    classic, calm = read_themes()
    for name, color in surface_colors(calm).items():
        assert contrast(color, classic["void"]) >= MINIMUM_CONTRAST, name


def test_calm_overrides_only_known_tokens() -> None:
    classic, calm = read_themes()
    assert set(calm) <= set(classic)
