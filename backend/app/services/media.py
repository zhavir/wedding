"""Bounded local media inspection. Never ask ffmpeg to open uploaded URLs."""

import io
import json
import math
import subprocess
import tempfile
from pathlib import Path

from PIL import Image


def video_preview(data: bytes | str, content_type: str, metadata: dict | None = None) -> bytes:
    with tempfile.TemporaryDirectory(prefix="wedding-media-") as directory:
        if isinstance(data, bytes):
            source = str(Path(directory) / "upload")
            Path(source).write_bytes(data)
            protocols = "file,pipe"
        else:
            # Only server-generated S3 URLs reach this internal function.
            source = data
            protocols = "http,https,tcp,tls,crypto"

        probe = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-protocol_whitelist",
                protocols,
                "-show_format",
                "-show_streams",
                "-of",
                "json",
                str(source),
            ],
            capture_output=True,
            check=True,
            timeout=5,
        )
        info = json.loads(probe.stdout)
        streams = [stream for stream in info["streams"] if stream.get("codec_type") == "video"]
        names = set(info["format"]["format_name"].split(","))
        expected = {"webm", "matroska"} if content_type == "video/webm" else {"mov", "mp4"}
        duration = float(info["format"].get("duration", 0))
        if not streams or not names & expected or not math.isfinite(duration) or duration <= 0:
            raise ValueError("Video must be a valid MP4, MOV or WebM file.")
        if int(streams[0].get("width", 0)) * int(streams[0].get("height", 0)) > 35_000_000:
            raise ValueError("Video resolution is too large.")
        if metadata is not None:
            metadata.update(
                width=int(streams[0]["width"]),
                height=int(streams[0]["height"]),
                duration_ms=round(duration * 1000),
                codec=streams[0].get("codec_name", "")[:40],
            )
        image = subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-nostdin",
                "-threads",
                "1",
                "-protocol_whitelist",
                protocols,
                "-i",
                str(source),
                "-map",
                "0:v:0",
                "-frames:v",
                "1",
                "-vf",
                "scale=1200:1200:force_original_aspect_ratio=decrease",
                "-f",
                "image2pipe",
                "-vcodec",
                "png",
                "-threads",
                "1",
                "pipe:1",
            ],
            capture_output=True,
            check=True,
            timeout=8,
        )
        with Image.open(io.BytesIO(image.stdout)) as frame:
            output = io.BytesIO()
            frame.convert("RGB").save(output, format="WEBP", quality=82)
            return output.getvalue()
