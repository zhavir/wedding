"""Convert local editorial images to metadata-free, correctly oriented WebP files.

uv run python scripts/optimize_images.py tmp/source tmp/landing-images
"""

import argparse
from pathlib import Path

from PIL import Image, ImageOps
from pillow_heif import register_heif_opener


def convert(source: Path, destination: Path, width: int, quality: int) -> None:
    with Image.open(source) as original:
        image = ImageOps.exif_transpose(original)
        image.thumbnail((width, width), Image.Resampling.LANCZOS)
        # Rebuild pixel data so EXIF (including GPS), XMP and other source metadata
        # cannot be inherited by the exported image.
        mode = "RGBA" if "A" in image.getbands() else "RGB"
        pixels = image.convert(mode)
        clean = Image.frombytes(mode, pixels.size, pixels.tobytes())
        clean.save(destination, "WEBP", quality=quality, method=6)
    print(f"{destination}: {destination.stat().st_size / 1024:.0f} KiB")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="One image or a directory of images")
    parser.add_argument("destination", type=Path, help="Output directory")
    parser.add_argument(
        "--size", type=int, default=1600, help="Maximum edge in pixels (no upscaling)"
    )
    parser.add_argument("--quality", type=int, default=82)
    args = parser.parse_args()
    if args.size < 1 or not 1 <= args.quality <= 100:
        parser.error("Use a positive size and quality between 1 and 100.")
    register_heif_opener()
    sources = sorted(args.source.iterdir()) if args.source.is_dir() else [args.source]
    sources = [
        p
        for p in sources
        if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".avif"}
    ]
    if not sources:
        parser.error("No supported images found.")
    names = [p.stem.lower() for p in sources]
    if len(set(names)) != len(names):
        parser.error("Input images must have unique names, regardless of extension/case.")
    args.destination.mkdir(parents=True, exist_ok=True)
    for source in sources:
        destination = args.destination / f"{source.stem.lower()}.webp"
        if source.resolve() == destination.resolve():
            parser.error("Keep the output directory separate from the originals.")
        convert(source, destination, args.size, args.quality)


if __name__ == "__main__":
    main()
