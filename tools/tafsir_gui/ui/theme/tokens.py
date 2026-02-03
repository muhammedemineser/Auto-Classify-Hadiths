"""
Design tokens extracted from Tafsir viewer.html.
These constants express the palette, typography, spacing, and motion system
so the NiceGUI UI can align closely with the reference design language.
"""

from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class ColorPalette:
    background: str
    panel: str
    ink: str
    muted: str
    border: str
    accent: str
    shadow: str
    badge: str


LIGHT_PALETTE = ColorPalette(
    background="#f7f7f9",
    panel="#ffffff",
    ink="#0f172a",
    muted="#526079",
    border="#d9dce4",
    accent="#b6860f",
    shadow="0 10px 20px rgba(0, 0, 0, 0.12)",
    badge="#eef1f7",
)

DARK_PALETTE = ColorPalette(
    background="#0b0f14",
    panel="#111826",
    ink="#f2e8d5",
    muted="#9ca6bb",
    border="rgba(255, 255, 255, 0.08)",
    accent="#f6c344",
    shadow="0 14px 32px rgba(0, 0, 0, 0.35)",
    badge="#1b2537",
)


@dataclass(frozen=True)
class TypographyScale:
    primary_family: Sequence[str]
    secondary_family: Sequence[str]
    base_size: int
    heading_size: int
    line_height: float
    letter_spacing: str


TYPOGRAPHY = TypographyScale(
    primary_family=("Manrope", "system-ui", "sans-serif"),
    secondary_family=("Amiri", "Noto Naskh Arabic", "serif"),
    base_size=14,
    heading_size=20,
    line_height=1.8,
    letter_spacing="0.03em",
)


@dataclass(frozen=True)
class SpacingScale:
    tiny: int
    small: int
    base: int
    medium: int
    large: int
    gutter: int


SPACING = SpacingScale(
    tiny=6,
    small=10,
    base=14,
    medium=18,
    large=24,
    gutter=32,
)


@dataclass(frozen=True)
class RadiusScale:
    pill: int
    card: int
    input: int


RADIUS = RadiusScale(pill=999, card=18, input=12)


@dataclass(frozen=True)
class ShadowScale:
    soft: str
    strong: str


SHADOWS = ShadowScale(
    soft="0 6px 16px rgba(0, 0, 0, 0.15)",
    strong="0 14px 32px rgba(0, 0, 0, 0.35)",
)


COLOR_MODES: Mapping[str, ColorPalette] = {
    "light": LIGHT_PALETTE,
    "dark": DARK_PALETTE,
}
