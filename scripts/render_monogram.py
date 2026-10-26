"""Render the email monogram from the frontend SVG without ImageMagick."""

from pathlib import Path

import cairosvg

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    cairosvg.svg2png(
        url=str(ROOT / "frontend/static/monogram.svg"),
        write_to=str(ROOT / "frontend/static/monogram.png"),
        output_width=360,
        output_height=360,
    )


if __name__ == "__main__":
    main()
