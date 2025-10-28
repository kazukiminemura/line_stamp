from __future__ import annotations

import argparse
import sys
from pathlib import Path

from line_stamp_tool.config import GenerationConfig, load_config
from line_stamp_tool.generator import StickerGenerator


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate LINE sticker images from a config file.")
    parser.add_argument("config", help="Path to the sticker configuration (JSON or YAML).")
    parser.add_argument(
        "--font",
        dest="font",
        help="Override font path. Useful for supplying a font that supports the desired language.",
    )
    parser.add_argument(
        "--output",
        dest="output",
        help="Override the output directory for generated assets.",
    )
    parser.add_argument(
        "--set-icon-text",
        dest="set_icon_text",
        help="Override the text used for the set icon graphic.",
    )
    parser.add_argument(
        "--disable-set-icon",
        action="store_true",
        help="Skip generating the set icon asset even if defined by the config.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    config, base_dir = load_config(args.config)

    if args.font:
        config.font_path = Path(args.font)
    if args.output:
        config.output_dir = Path(args.output)
    if args.set_icon_text is not None:
        config.set_icon_text = args.set_icon_text
    if args.disable_set_icon:
        config.set_icon_text = None

    generator = StickerGenerator(config, base_dir=base_dir)
    generator.generate_all()
    print(f"Generated {len(config.stickers)} stickers in '{generator.output_dir}'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
