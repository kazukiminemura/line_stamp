from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


def _as_tuple(value: Iterable[int] | int, length: int, fallback: Tuple[int, ...]) -> Tuple[int, ...]:
    if isinstance(value, int):
        return tuple([value] * length)
    try:
        items = tuple(int(v) for v in value)
    except TypeError:
        return fallback
    if len(items) != length:
        return fallback
    return items


def _as_float(value: Any, default: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    try:
        as_float = float(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, as_float))


@dataclass(slots=True)
class IllustrationSpec:
    enabled: bool = False
    style: str = "blob"
    face_color: str = "#FFD166"
    outline_color: str = "#2F2F2F"
    accent_color: Optional[str] = None
    expression: str = "smile"

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "IllustrationSpec":
        data = dict(raw)
        data["enabled"] = bool(data.get("enabled", True))
        for key in ("style", "face_color", "outline_color", "accent_color", "expression"):
            if data.get(key) is not None:
                data[key] = str(data[key])
        return cls(**data)


@dataclass(slots=True)
class StickerSpec:
    text: str
    slug: Optional[str] = None
    background_color: str = "#FFFFFF"
    text_color: str = "#000000"
    text_shadow_color: Optional[str] = None
    text_shadow_offset: Tuple[int, int] = (8, 8)
    text_stroke_color: Optional[str] = None
    text_stroke_width: int = 0
    padding: int = 90
    line_spacing: float = 1.05
    image_path: Optional[str] = None
    image_area_ratio: float = 0.45
    image_bottom_margin: int = 40
    background_image: Optional[str] = None
    illustration: Optional[IllustrationSpec] = None

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "StickerSpec":
        data = dict(raw)
        data["text_shadow_offset"] = _as_tuple(
            data.get("text_shadow_offset", (8, 8)),
            2,
            (8, 8),
        )
        data["padding"] = int(data.get("padding", 90))
        data["image_bottom_margin"] = int(data.get("image_bottom_margin", 40))
        data["line_spacing"] = _as_float(data.get("line_spacing", 1.05), 1.05, 0.1, 2.0)
        data["image_area_ratio"] = _as_float(data.get("image_area_ratio", 0.45), 0.45, 0.0, 0.95)
        data["text_stroke_width"] = int(data.get("text_stroke_width", 0))
        slug = data.get("slug")
        if slug is not None:
            data["slug"] = str(slug)
        for key in ("background_color", "text_color", "text_shadow_color", "text_stroke_color"):
            if data.get(key) is not None:
                data[key] = str(data[key])
        illustration_raw = data.get("illustration")
        if illustration_raw:
            if not isinstance(illustration_raw, dict):
                raise ValueError("illustration must be a mapping when provided")
            data["illustration"] = IllustrationSpec.from_dict(illustration_raw)
        return cls(**data)


@dataclass(slots=True)
class GenerationConfig:
    stickers: List[StickerSpec]
    output_dir: Path = Path("build/stamps")
    font_path: Optional[Path] = None
    font_size: int = 180
    main_size: Tuple[int, int] = (370, 320)
    tab_size: Tuple[int, int] = (96, 74)
    store_size: Tuple[int, int] = (240, 240)
    scale_multiplier: int = 4
    set_icon_text: Optional[str] = None
    set_icon_background: str = "#FFFFFF"
    set_icon_text_color: str = "#000000"
    set_icon_font_size: Optional[int] = None

    def __post_init__(self) -> None:
        if isinstance(self.output_dir, (str, Path)):
            self.output_dir = Path(self.output_dir)
        if isinstance(self.font_path, str):
            self.font_path = Path(self.font_path)
        self.font_size = max(24, int(self.font_size))
        self.main_size = _as_tuple(self.main_size, 2, (370, 320))  # type: ignore[arg-type]
        self.tab_size = _as_tuple(self.tab_size, 2, (96, 74))  # type: ignore[arg-type]
        self.store_size = _as_tuple(self.store_size, 2, (240, 240))  # type: ignore[arg-type]
        self.scale_multiplier = max(2, int(self.scale_multiplier))

    @property
    def base_size(self) -> Tuple[int, int]:
        return (self.main_size[0] * self.scale_multiplier, self.main_size[1] * self.scale_multiplier)


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> Dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("YAML support requires installing PyYAML") from exc
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    if not isinstance(loaded, dict):
        raise ValueError("YAML configuration must be a mapping at the top level")
    return loaded


def load_config(path: Path | str) -> Tuple[GenerationConfig, Path]:
    path_obj = Path(path)
    if not path_obj.exists():
        raise FileNotFoundError(f"Config file not found: {path_obj}")
    suffix = path_obj.suffix.lower()
    if suffix == ".json":
        raw_config = _load_json(path_obj)
    elif suffix in (".yaml", ".yml"):
        raw_config = _load_yaml(path_obj)
    else:
        raise ValueError(f"Unsupported config format: {suffix}")

    if "stickers" not in raw_config or not isinstance(raw_config["stickers"], list):
        raise ValueError("Config must define a list named 'stickers'")

    stickers = [StickerSpec.from_dict(entry) for entry in raw_config["stickers"]]
    cfg_kwargs: Dict[str, Any] = {key: value for key, value in raw_config.items() if key != "stickers"}
    cfg_kwargs["stickers"] = stickers
    config = GenerationConfig(**cfg_kwargs)
    return config, path_obj.parent.resolve()
