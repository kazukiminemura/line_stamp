# LINE Sticker Generator
- Python tool that renders static LINE sticker assets (main images, talk room tab, store icon) from a declarative config
- Handles text wrapping for multi-line Japanese phrases and optional drop shadows / outlines
- Supports custom background colors or images plus optional illustration overlays per sticker

## Quick Start
- Requires Python 3.10+ and Pillow (install via `pip install -r requirements.txt`)
- Copy `examples/sample_config.json`, update texts / colors / optional image paths
- Run `python generate_stamps.py your_config.json --output build/stamps`
- Generated assets land in `build/stamps/{main,store,tab,set_icon}`

```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows
pip install -r requirements.txt
python generate_stamps.py examples/sample_config.json
```

## Configuration Guide
- `output_dir`: base folder for generated images (default `build/stamps`)
- `font_size`: starting font size; tool auto-shrinks to fit if needed
- `font_path`: optional absolute/relative path to a TTF/TTC font (recommended for Japanese text)
- `set_icon_text`: text for the 240×240 set icon; omit or pass `--disable-set-icon` to skip
- `stickers`: array of sticker definitions; each entry supports:
  - `slug`: filename stem (`{slug}_{category}.png`); auto-derived when omitted
  - `text`: text rendered near the top of the sticker
  - `background_color`: hex color (e.g. `#4B9CD3`); supports alpha with `#RRGGBBAA`
  - `background_image`: optional path to an image that fills the canvas
  - `text_color`, `text_shadow_color`, `text_shadow_offset`, `text_stroke_color`, `text_stroke_width`
  - `padding`: inner margin from edges (pixels at export scale)
  - `line_spacing`: multiplier for spacing between lines (default `1.05`)
  - `image_path`: optional illustration to paste under the text
  - `illustration`: auto-generated character when you do not have your own PNG; use fields like
    - `style` (`blob` or `cat`), `face_color`, `outline_color`, optional `accent_color`
    - `expression`: `smile`, `happy`, `laugh`, `wink`, `angry`, `sad`, or `sleepy`
  - `image_area_ratio`: fraction of vertical space reserved for the illustration (0–0.95)
  - `image_bottom_margin`: extra breathing room beneath the illustration

```json
{
  "output_dir": "output/stamps",
  "font_path": "C:/Windows/Fonts/YuGothR.ttc",
  "set_icon_text": "LINE STAMP",
  "stickers": [
    {
      "slug": "arigato",
      "text": "ありがとう〜！",
      "background_color": "#F7B32B",
      "text_color": "#3A1F04",
      "text_stroke_color": "#FFFFFF",
      "text_stroke_width": 6,
      "illustration": {
        "style": "blob",
        "face_color": "#FFE066",
        "accent_color": "#FF6B6B",
        "expression": "happy"
      }
    }
  ]
}
```

## Tips
- Provide a font that supports your target language (e.g. Yu Gothic on Windows, Noto Sans CJK on Linux)
- Add illustration overlays by referencing PNG files with transparency via `image_path`
- Generated assets are ready to zip and upload to LINE Creators Market (main: 370×320, tab: 96×74, icon: 240×240)
- Re-run `generate_stamps.py` whenever you tweak the config; existing files get overwritten
