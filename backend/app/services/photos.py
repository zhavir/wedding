import hashlib
import io
import subprocess
import warnings

from boto3.s3.transfer import TransferConfig
from botocore.exceptions import ClientError
from fastapi import HTTPException
from PIL import Image, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener

from app.core.config import settings
from app.db.models import Photo
from app.services.aws import s3
from app.services.media import video_preview

register_heif_opener()

Image.MAX_IMAGE_PIXELS = 60_000_000


def media_key(photo: Photo, kind: str, suffix: str = "") -> str:
    return f"{kind}/{photo.storage_prefix or ''}{photo.id}{suffix}"


def inspect_remote_video(photo: Photo, motion: bool = False):
    key = media_key(photo, "pending", "-motion" if motion else "")
    head = s3().head_object(Bucket=settings().bucket_name, Key=key)
    if head["ContentLength"] != (photo.motion_size if motion else photo.size):
        raise ValueError("Uploaded file size does not match.")
    url = s3().generate_presigned_url(
        "get_object", Params={"Bucket": settings().bucket_name, "Key": key}, ExpiresIn=900
    )
    metadata: dict = {}
    preview = video_preview(
        url, photo.motion_content_type if motion else photo.content_type, metadata
    )
    return preview, metadata, head["ETag"]


def preserve_remote_video(photo: Photo, etag: str, motion: bool = False):
    suffix = "-motion" if motion else ""
    key = media_key(photo, "originals", suffix)
    bucket = settings().bucket_name
    try:
        existing = s3().head_object(Bucket=bucket, Key=key)
    except ClientError as exc:
        if exc.response["Error"]["Code"] not in {"404", "NoSuchKey", "NotFound"}:
            raise
    else:
        if existing.get("Metadata", {}).get("source-etag") == etag:
            return
        raise HTTPException(409, "This upload was already finalised with different contents.")
    s3().copy(
        {"Bucket": bucket, "Key": media_key(photo, "pending", suffix)},
        bucket,
        key,
        ExtraArgs={
            "CopySourceIfMatch": etag,
            "MetadataDirective": "REPLACE",
            "Metadata": {"source-etag": etag},
            "ContentType": photo.motion_content_type if motion else photo.content_type,
            "CacheControl": "private, max-age=3600",
        },
        Config=TransferConfig(
            multipart_threshold=64 * 1024**2, multipart_chunksize=128 * 1024**2, max_concurrency=2
        ),
    )


def process_photo(photo: Photo) -> None:
    bucket = settings().bucket_name
    pending = media_key(photo, "pending")
    try:
        obj = s3().get_object(Bucket=bucket, Key=pending)
    except ClientError as exc:
        if exc.response["Error"]["Code"] in ("NoSuchKey", "404"):
            raise HTTPException(409, "The upload hasn't finished yet.") from None
        raise
    if obj["ContentLength"] != photo.size or (
        photo.content_type.startswith("image/") and photo.size > settings().max_upload_bytes
    ):
        obj["Body"].close()
        raise HTTPException(422, "Uploaded file size does not match.")
    if photo.content_type.startswith("video/") and photo.size > 64 * 1024**2:
        obj["Body"].close()
        try:
            preview, metadata, etag = inspect_remote_video(photo)
        except subprocess.SubprocessError, KeyError, OSError, ValueError:
            s3().delete_object(Bucket=bucket, Key=pending)
            raise HTTPException(422, "Please upload a valid image or video.") from None
        preserve_remote_video(photo, etag)
        s3().put_object(
            Bucket=bucket,
            Key=media_key(photo, "previews", ".webp"),
            Body=preview,
            ContentType="image/webp",
            CacheControl="private, max-age=3600",
        )
        for key, value in metadata.items():
            setattr(photo, key, value)
        return
    original = obj["Body"].read()
    photo.sha256 = hashlib.sha256(original).hexdigest()
    metadata: dict = {}
    try:
        if photo.content_type.startswith("video/"):
            preview_bytes = video_preview(original, photo.content_type, metadata)
        else:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(original)) as probe:
                    detected = Image.MIME.get(probe.format or "")
                    probe.verify()
                if detected != photo.content_type and not (
                    detected in {"image/heif", "image/heic"}
                    and photo.content_type in {"image/heif", "image/heic"}
                ):
                    raise ValueError()
                with Image.open(io.BytesIO(original)) as source:
                    preview = ImageOps.exif_transpose(source)
                    metadata.update(
                        width=preview.width, height=preview.height, codec=(source.format or "")[:40]
                    )
                    preview.thumbnail((1200, 1200))
                    buf = io.BytesIO()
                    preview.convert("RGB").save(buf, format="WEBP", quality=82)
            preview_bytes = buf.getvalue()
        motion = b""
        motion_etag = ""
        if photo.motion_size:
            if photo.motion_size > 64 * 1024**2:
                _, motion_metadata, motion_etag = inspect_remote_video(photo, True)
            else:
                motion_object = s3().get_object(
                    Bucket=bucket, Key=media_key(photo, "pending", "-motion")
                )
                if motion_object["ContentLength"] != photo.motion_size:
                    motion_object["Body"].close()
                    raise ValueError("Live Photo motion size does not match.")
                motion = motion_object["Body"].read()
                motion_metadata = {}
                video_preview(motion, photo.motion_content_type, motion_metadata)
            metadata["duration_ms"] = motion_metadata["duration_ms"]
    except (
        subprocess.SubprocessError,
        KeyError,
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ):
        s3().delete_object(Bucket=bucket, Key=pending)
        raise HTTPException(
            422, "Please upload a valid image (up to 60 megapixels) or video."
        ) from None
    if motion_etag:
        preserve_remote_video(photo, motion_etag, True)
    for key, value in metadata.items():
        setattr(photo, key, value)
    objects = [
        (media_key(photo, "originals"), original, photo.content_type),
        (media_key(photo, "previews", ".webp"), preview_bytes, "image/webp"),
    ]
    if motion:
        objects.append((
            media_key(photo, "originals", "-motion"),
            motion,
            photo.motion_content_type,
        ))
    for key, data, content_type in objects:
        try:
            s3().put_object(
                Bucket=bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
                CacheControl="private, max-age=3600",
                IfNoneMatch="*",
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] not in ("PreconditionFailed", "412"):
                raise
            existing = s3().get_object(Bucket=bucket, Key=key)["Body"].read()
            if hashlib.sha256(existing).digest() != hashlib.sha256(data).digest():
                raise HTTPException(
                    409, "This upload was already finalised with different contents."
                ) from None


def photo_view(photo: Photo) -> dict[str, str]:
    def url(key: str) -> str:
        return s3(True).generate_presigned_url(
            "get_object", Params={"Bucket": settings().bucket_name, "Key": key}, ExpiresIn=3600
        )

    return {
        "id": photo.id,
        "kind": "live"
        if photo.motion_size
        else "video"
        if photo.content_type.startswith("video/")
        else "photo",
        "motion": url(media_key(photo, "originals", "-motion")) if photo.motion_size else "",
        "caption": photo.caption,
        "preview": url(media_key(photo, "previews", ".webp")),
        "original": url(media_key(photo, "originals")),
    }
