"""Decode uploaded images in a worker with bounded memory and runtime."""

import io
import json
import shutil
import subprocess
import sys
import tempfile
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from _typeshed import SupportsRead

PREVIEW_SIZE = (1200, 1200)


def image_preview(source: SupportsRead[bytes]) -> tuple[bytes, dict]:
    # Pillow needs a seekable source. Spool to disk without buffering the upload in RAM.
    with tempfile.TemporaryFile() as upload:
        shutil.copyfileobj(source, upload, length=1024**2)
        upload.seek(0)
        result = subprocess.run(
            [sys.executable, "-m", "app.services.image_preview"],
            stdin=upload,
            capture_output=True,
            check=True,
            timeout=15,
        )
    metadata, _, preview = result.stdout.partition(b"\n")
    return preview, json.loads(metadata)


def main() -> None:
    import resource

    from PIL import ExifTags, Image, ImageOps
    from pillow_heif import register_heif_opener

    # Leave memory for the API process and its other work in the 1 GiB runtime.
    memory = 640 * 1024**2
    resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
    register_heif_opener()
    Image.MAX_IMAGE_PIXELS = None

    source = sys.stdin.buffer
    with Image.open(source) as probe:
        content_type = Image.MIME.get(probe.format or "")
        if content_type not in {
            "image/jpeg",
            "image/png",
            "image/webp",
            "image/heic",
            "image/heif",
        }:
            raise ValueError("The image format is not supported.")
        probe.verify()

    source.seek(0)
    with Image.open(source) as image:
        width, height = image.size
        if image.getexif().get(ExifTags.Base.Orientation) in {5, 6, 7, 8}:
            width, height = height, width
        metadata = {
            "width": width,
            "height": height,
            "codec": image.format or "",
            "content_type": content_type,
        }
        # Resize before applying orientation to avoid copying a full-resolution frame.
        # Pillow's thumbnail also uses JPEG decoder downsampling where available.
        image.thumbnail(PREVIEW_SIZE)
        preview = io.BytesIO()
        ImageOps.exif_transpose(image).convert("RGB").save(preview, "WEBP", quality=82)

    sys.stdout.buffer.write(json.dumps(metadata).encode() + b"\n" + preview.getvalue())


if __name__ == "__main__":
    main()
