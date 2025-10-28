from __future__ import annotations

import math
import unicodedata
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageOps

from .config import GenerationConfig, IllustrationSpec, StickerSpec

DEFAULT_FONT_CANDIDATES: Sequence[Path] = (
    Path("C:/Windows/Fonts/YuGothR.ttc"),
    Path("C:/Windows/Fonts/MSGOTHIC.TTC"),
    Path("C:/Windows/Fonts/msyh.ttc"),
    Path("/System/Library/Fonts/AppleSDGothicNeo.ttc"),
    Path("/System/Library/Fonts/Helvetica.ttc"),
    Path("/Library/Fonts/Arial Unicode.ttf"),
    Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/truetype/noto/NotoSansCJKjp-Regular.otf"),
    Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
)


def _parse_color(value: str) -> Tuple[int, int, int, int]:
    raw = value.strip()
    if not raw.startswith("#"):
        raise ValueError(f"Unsupported color format: {value}")
    raw = raw[1:]
    if len(raw) == 3:
        raw = "".join(ch * 2 for ch in raw)
    if len(raw) == 6:
        raw += "FF"
    if len(raw) != 8:
        raise ValueError(f"Invalid hex color: {value}")
    r = int(raw[0:2], 16)
    g = int(raw[2:4], 16)
    b = int(raw[4:6], 16)
    a = int(raw[6:8], 16)
    return (r, g, b, a)


def _slugify(source: str) -> str:
    normalized = unicodedata.normalize("NFKD", source)
    ascii_only = []
    for char in normalized:
        if char.isalnum():
            ascii_only.append(char.lower())
        elif char in (" ", "-", "_"):
            ascii_only.append("-")
    slug = "".join(ascii_only)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-_ ")


class StickerGenerator:
    def __init__(self, config: GenerationConfig, base_dir: Optional[Path] = None) -> None:
        self.config = config
        self.base_dir = Path(base_dir or Path.cwd())
        self.output_dir = (self.base_dir / self.config.output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._font_path = self._resolve_font_path()
        self._measure_image = Image.new("RGBA", (10, 10))
        self._measure_draw = ImageDraw.Draw(self._measure_image)

    def generate_all(self) -> None:
        for index, spec in enumerate(self.config.stickers, start=1):
            base_image = self._render_base(spec)
            slug = self._ensure_slug(spec, index)
            self._export_scaled(base_image, slug, "main", self.config.main_size)
            self._export_scaled(base_image, slug, "store", self.config.store_size)
            self._export_scaled(base_image, slug, "tab", self.config.tab_size)

        if self.config.set_icon_text:
            self._generate_set_icon(self.config.set_icon_text)

    def _render_base(self, spec: StickerSpec) -> Image.Image:
        width, height = self.config.base_size
        background = self._compose_background(spec, (width, height))
        draw = ImageDraw.Draw(background)

        available_width = width - spec.padding * 2
        available_height = height - spec.padding * 2
        has_art = bool(spec.image_path or (spec.illustration and spec.illustration.enabled))
        image_reserved_height = int(available_height * spec.image_area_ratio) if has_art else 0
        text_box_height = max(available_height - image_reserved_height, int(available_height * 0.35))
        font, lines, line_height, line_gap = self._layout_text(
            spec.text,
            available_width,
            text_box_height,
            self.config.font_size,
            spec.line_spacing,
        )

        text_block_height = self._block_height(len(lines), line_height, line_gap)
        text_top = spec.padding + max(0, (text_box_height - text_block_height) // 2)
        text_left = spec.padding

        self._draw_text_block(
            draw,
            lines,
            font,
            text_left,
            text_top,
            available_width,
            line_height,
            line_gap,
            spec,
        )

        text_bottom = text_top + text_block_height
        art_image = self._obtain_art_image(spec)
        if art_image is not None:
            self._composite_art(
                background,
                art_image,
                available_width,
                height,
                spec.padding,
                text_bottom,
                spec.image_bottom_margin,
            )

        return background

    def _compose_background(self, spec: StickerSpec, size: Tuple[int, int]) -> Image.Image:
        width, height = size
        base_color = _parse_color(spec.background_color)
        canvas = Image.new("RGBA", (width, height), base_color)

        if spec.background_image:
            path = self._resolve_path(spec.background_image)
            with Image.open(path) as bg:
                background = ImageOps.fit(bg.convert("RGBA"), (width, height), Image.LANCZOS)
            canvas.alpha_composite(background)
        return canvas

    def _composite_art(
        self,
        canvas: Image.Image,
        art_image: Image.Image,
        text_width: int,
        full_height: int,
        padding: int,
        text_bottom: int,
        bottom_margin: int,
    ) -> None:
        art_rgba = art_image
        max_width = text_width
        max_height = max(0, full_height - text_bottom - padding - bottom_margin)
        if max_height <= 0:
            return

        art_rgba.thumbnail((max_width, max_height), Image.LANCZOS)
        horizontal_margin = (text_width - art_rgba.width) // 2
        x_pos = padding + max(0, horizontal_margin)
        y_pos = full_height - padding - bottom_margin - art_rgba.height
        canvas.alpha_composite(art_rgba, dest=(x_pos, y_pos))

    def _draw_text_block(
        self,
        draw: ImageDraw.ImageDraw,
        lines: List[str],
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        left: int,
        top: int,
        width: int,
        line_height: int,
        line_gap: int,
        spec: StickerSpec,
    ) -> None:
        y = top
        for line in lines:
            text_width = self._text_length(line, font)
            x = left + max(0, (width - text_width) // 2)
            if spec.text_shadow_color:
                offset_x, offset_y = spec.text_shadow_offset
                draw.text(
                    (x + offset_x, y + offset_y),
                    line,
                    font=font,
                    fill=_parse_color(spec.text_shadow_color),
                )
            draw.text(
                (x, y),
                line,
                font=font,
                fill=_parse_color(spec.text_color),
                stroke_width=spec.text_stroke_width,
                stroke_fill=_parse_color(spec.text_stroke_color) if spec.text_stroke_color else None,
            )
            y += line_height + line_gap

    def _layout_text(
        self,
        text: str,
        max_width: int,
        max_height: int,
        base_font_size: int,
        line_spacing: float,
    ) -> Tuple[ImageFont.FreeTypeFont | ImageFont.ImageFont, List[str], int, int]:
        size = base_font_size
        min_size = max(20, base_font_size // 4)
        while size >= min_size:
            font = self._get_font(size)
            lines = self._wrap_text(text, font, max_width)
            line_height, line_gap, block_height, max_line_width = self._measure_block(lines, font, line_spacing)
            if block_height <= max_height and max_line_width <= max_width:
                return font, lines, line_height, line_gap
            size -= 4

        font = self._get_font(min_size)
        lines = self._wrap_text(text, font, max_width)
        line_height, line_gap, _, _ = self._measure_block(lines, font, line_spacing)
        return font, lines, line_height, line_gap

    def _measure_block(
        self,
        lines: List[str],
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        line_spacing: float,
    ) -> Tuple[int, int, int, int]:
        line_height = self._line_height(font)
        line_gap = max(0, int(math.floor(line_height * max(0.0, line_spacing - 1.0))))
        total_height = self._block_height(len(lines), line_height, line_gap)
        max_width = max((self._text_length(line, font) for line in lines), default=0)
        return line_height, line_gap, total_height, max_width

    @staticmethod
    def _block_height(line_count: int, line_height: int, line_gap: int) -> int:
        if line_count == 0:
            return 0
        return line_count * line_height + (line_count - 1) * line_gap

    def _wrap_text(
        self,
        text: str,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        max_width: int,
    ) -> List[str]:
        if not text:
            return [""]
        lines: List[str] = []
        current = ""
        for char in text:
            if char == "\n":
                lines.append(current)
                current = ""
                continue
            tentative = current + char
            length = self._text_length(tentative, font)
            if length <= max_width or not current:
                current = tentative
            else:
                lines.append(current)
                current = char
        if current or not lines:
            lines.append(current)
        return lines

    def _generate_set_icon(self, text: str) -> None:
        size = max(self.config.store_size)
        base_size = size * self.config.scale_multiplier
        canvas = Image.new("RGBA", (base_size, base_size), _parse_color(self.config.set_icon_background))
        font_size = self.config.set_icon_font_size or max(48, int(base_size * 0.42))
        font, lines, line_height, line_gap = self._layout_text(
            text,
            base_size - int(base_size * 0.2),
            base_size - int(base_size * 0.2),
            font_size,
            1.1,
        )
        draw = ImageDraw.Draw(canvas)
        block_height = self._block_height(len(lines), line_height, line_gap)
        y = (base_size - block_height) // 2
        for line in lines:
            width = self._text_length(line, font)
            x = (base_size - width) // 2
            draw.text(
                (x, y),
                line,
                font=font,
                fill=_parse_color(self.config.set_icon_text_color),
            )
            y += line_height + line_gap

        target_dir = self.output_dir / "set_icon"
        target_dir.mkdir(parents=True, exist_ok=True)
        store_size = (size, size)
        set_icon_path = target_dir / "set_icon.png"
        ImageOps.fit(canvas, store_size, Image.LANCZOS, centering=(0.5, 0.5)).save(set_icon_path)

    def _export_scaled(self, image: Image.Image, slug: str, category: str, size: Tuple[int, int]) -> None:
        target_dir = self.output_dir / category
        target_dir.mkdir(parents=True, exist_ok=True)
        if size[0] <= 0 or size[1] <= 0:
            return

        if not isinstance(size[0], int) or not isinstance(size[1], int):
            size = (int(size[0]), int(size[1]))

        resized = self._resize_for_target(image, size)
        output_path = target_dir / f"{slug}_{category}.png"
        resized.save(output_path)

    def _resize_for_target(self, image: Image.Image, size: Tuple[int, int]) -> Image.Image:
        src_ratio = image.width / image.height
        target_ratio = size[0] / size[1]
        if abs(src_ratio - target_ratio) <= 0.01:
            return image.resize(size, Image.LANCZOS)
        return ImageOps.fit(image, size, Image.LANCZOS, centering=(0.5, 0.5))

    def _ensure_slug(self, spec: StickerSpec, index: int) -> str:
        if spec.slug:
            return spec.slug
        derived = _slugify(spec.text)
        if derived:
            return derived
        return f"stamp_{index:02d}"

    def _resolve_path(self, maybe_path: Optional[str | Path]) -> Path:
        if maybe_path is None:
            raise ValueError("Expected a path but received None")
        path = Path(maybe_path)
        if not path.is_absolute():
            path = (self.base_dir / path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Asset not found: {path}")
        return path

    def _resolve_font_path(self) -> Optional[Path]:
        if self.config.font_path:
            path = self._resolve_path(self.config.font_path)
            return path
        for candidate in DEFAULT_FONT_CANDIDATES:
            if candidate.exists():
                return candidate
        return None

    def _get_font(self, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        if self._font_path:
            try:
                return ImageFont.truetype(str(self._font_path), size=size)
            except OSError as exc:
                raise RuntimeError(f"Failed to load font '{self._font_path}': {exc}") from exc
        return ImageFont.load_default()

    def _text_length(self, text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> int:
        length = self._measure_draw.textlength(text, font=font)
        return int(math.ceil(length))

    def _line_height(self, font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> int:
        try:
            ascent, descent = font.getmetrics()
            return int(ascent + descent)
        except (AttributeError, TypeError):
            bbox = self._measure_draw.textbbox((0, 0), "Ag", font=font)
            return bbox[3] - bbox[1]
    def _obtain_art_image(self, spec: StickerSpec) -> Optional[Image.Image]:
        if spec.image_path:
            path = self._resolve_path(spec.image_path)
            with Image.open(path) as art:
                return art.convert("RGBA")
        if spec.illustration and spec.illustration.enabled:
            return self._render_illustration(spec.illustration)
        return None

    def _render_illustration(self, illustration: IllustrationSpec) -> Image.Image:
        base_size = int(min(self.config.base_size) * 0.55)
        base_size = max(base_size, 200)
        if illustration.style.lower() == "cat":
            return self._draw_cat_blob(illustration, base_size)
        return self._draw_blob(illustration, base_size)

    def _draw_blob(self, illustration: IllustrationSpec, size: int) -> Image.Image:
        image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        blob_bbox = (
            int(size * 0.08),
            int(size * 0.15),
            int(size * 0.92),
            int(size * 0.95),
        )
        outline_width = max(4, size // 35)
        draw.ellipse(blob_bbox, fill=_parse_color(illustration.face_color), outline=_parse_color(illustration.outline_color), width=outline_width)
        self._draw_face(draw, illustration, size, blob_bbox, outline_width)
        return image

    def _draw_cat_blob(self, illustration: IllustrationSpec, size: int) -> Image.Image:
        image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        ear_height = int(size * 0.22)
        ear_width = int(size * 0.22)
        center_x = size // 2
        left_ear = [
            (center_x - ear_width, int(size * 0.25)),
            (center_x - ear_width * 2, int(size * 0.05)),
            (center_x - int(ear_width * 0.3), int(size * 0.05)),
        ]
        right_ear = [
            (center_x + ear_width, int(size * 0.25)),
            (center_x + ear_width * 2, int(size * 0.05)),
            (center_x + int(ear_width * 0.3), int(size * 0.05)),
        ]
        fill_color = _parse_color(illustration.face_color)
        outline_color = _parse_color(illustration.outline_color)
        outline_width = max(4, size // 35)
        draw.polygon(left_ear, fill=fill_color, outline=outline_color)
        draw.polygon(right_ear, fill=fill_color, outline=outline_color)
        blob_bbox = (
            int(size * 0.1),
            int(size * 0.2),
            int(size * 0.9),
            int(size * 0.95),
        )
        draw.ellipse(blob_bbox, fill=fill_color, outline=outline_color, width=outline_width)

        if illustration.accent_color:
            inner_color = _parse_color(illustration.accent_color)
            inner_left = [
                (center_x - ear_width + outline_width, int(size * 0.23)),
                (center_x - ear_width * 1.7, int(size * 0.09)),
                (center_x - int(ear_width * 0.5), int(size * 0.08)),
            ]
            inner_right = [
                (center_x + ear_width - outline_width, int(size * 0.23)),
                (center_x + ear_width * 1.7, int(size * 0.09)),
                (center_x + int(ear_width * 0.5), int(size * 0.08)),
            ]
            draw.polygon(inner_left, fill=inner_color)
            draw.polygon(inner_right, fill=inner_color)

        self._draw_face(draw, illustration, size, blob_bbox, outline_width)
        return image

    def _draw_face(
        self,
        draw: ImageDraw.ImageDraw,
        illustration: IllustrationSpec,
        size: int,
        blob_bbox: Tuple[int, int, int, int],
        outline_width: int,
    ) -> None:
        outline = _parse_color(illustration.outline_color)
        accent = _parse_color(illustration.accent_color) if illustration.accent_color else outline
        eye_diameter = max(8, size // 9)
        eye_spacing = size // 5
        eye_y = int(size * 0.45)
        left_eye_center = (size // 2 - eye_spacing, eye_y)
        right_eye_center = (size // 2 + eye_spacing, eye_y)
        expression = illustration.expression.lower()

        def draw_eye(center: Tuple[int, int], closed: bool = False) -> None:
            x, y = center
            half = eye_diameter // 2
            if closed:
                draw.line(
                    (x - half, y, x + half, y + outline_width // 2),
                    fill=outline,
                    width=max(2, outline_width),
                )
            else:
                draw.ellipse(
                    (x - half, y - half, x + half, y + half),
                    fill=accent,
                )

        if expression == "wink":
            draw_eye(left_eye_center)
            draw_eye(right_eye_center, closed=True)
        elif expression == "angry":
            brow_offset = size // 12
            draw.line(
                (left_eye_center[0] - eye_diameter, eye_y - brow_offset, left_eye_center[0] + eye_diameter, eye_y - brow_offset // 2),
                fill=outline,
                width=max(2, outline_width),
            )
            draw.line(
                (right_eye_center[0] - eye_diameter, eye_y - brow_offset // 2, right_eye_center[0] + eye_diameter, eye_y - brow_offset),
                fill=outline,
                width=max(2, outline_width),
            )
            draw_eye(left_eye_center)
            draw_eye(right_eye_center)
        elif expression == "happy":
            sparkle = max(3, eye_diameter // 4)
            draw_eye(left_eye_center)
            draw_eye(right_eye_center)
            draw.ellipse(
                (
                    left_eye_center[0] - sparkle,
                    left_eye_center[1] - sparkle,
                    left_eye_center[0] + sparkle,
                    left_eye_center[1] + sparkle,
                ),
                fill=_parse_color("#FFFFFF"),
            )
            draw.ellipse(
                (
                    right_eye_center[0] - sparkle,
                    right_eye_center[1] - sparkle,
                    right_eye_center[0] + sparkle,
                    right_eye_center[1] + sparkle,
                ),
                fill=_parse_color("#FFFFFF"),
            )
        elif expression == "sleepy":
            draw_eye(left_eye_center, closed=True)
            draw_eye(right_eye_center, closed=True)
        else:
            draw_eye(left_eye_center)
            draw_eye(right_eye_center)

        mouth_width = int(size * 0.32)
        mouth_height = int(size * 0.18)
        mouth_center_y = int(size * 0.68)
        mouth_box = (
            size // 2 - mouth_width,
            mouth_center_y - mouth_height,
            size // 2 + mouth_width,
            mouth_center_y + mouth_height,
        )
        mouth_style = {
            "smile": (200, 340, False),
            "laugh": (190, 350, True),
            "wink": (210, 350, True),
            "happy": (200, 350, True),
            "angry": (200, 200, False),
            "sad": (20, 160, False),
            "sleepy": (200, 200, False),
        }.get(expression, (200, 340, False))

        start, end, fill_chord = mouth_style
        if expression == "angry":
            draw.line(
                (size // 2 - mouth_width, mouth_center_y, size // 2 + mouth_width, mouth_center_y + outline_width // 2),
                fill=outline,
                width=max(3, outline_width),
            )
        elif expression == "sad":
            draw.arc(mouth_box, start=start, end=end, fill=outline, width=max(3, outline_width))
        else:
            if fill_chord:
                draw.chord(mouth_box, start=start, end=end, fill=accent, outline=outline, width=max(3, outline_width))
            else:
                draw.arc(mouth_box, start=start, end=end, fill=outline, width=max(3, outline_width))
