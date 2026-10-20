"""Direct S3 multipart transfers without proxying video bytes through FastAPI."""

import math

from botocore.exceptions import ClientError
from fastapi import HTTPException

from app.core.config import settings
from app.schemas import FinishUpload
from app.services.aws import s3
from app.services.photos import media_key

PART_SIZE = 64 * 1024**2


def part_size(size: int) -> int:
    return max(PART_SIZE, math.ceil(size / 10000 / 1024**2) * 1024**2)


def start_target(photo, motion: bool) -> dict:
    size = photo.motion_size if motion else photo.size
    content_type = photo.motion_content_type if motion else photo.content_type
    key = media_key(photo, "pending", "-motion" if motion else "")
    if size > PART_SIZE:
        result = s3().create_multipart_upload(
            Bucket=settings().bucket_name, Key=key, ContentType=content_type
        )
        setattr(photo, "motion_multipart_id" if motion else "multipart_id", result["UploadId"])
        return {"multipart": True, "part_size": part_size(size)}
    return s3(True).generate_presigned_post(
        settings().bucket_name,
        key,
        Fields={"Content-Type": content_type},
        Conditions=[{"Content-Type": content_type}, ["content-length-range", size, size]],
        ExpiresIn=600,
    )


def part_url(photo, number: int, motion: bool) -> str:
    size = photo.motion_size if motion else photo.size
    upload_id = photo.motion_multipart_id if motion else photo.multipart_id
    chunk = part_size(size)
    if not upload_id or not 1 <= number <= math.ceil(size / chunk):
        raise HTTPException(422, "Invalid upload part.")
    return s3(True).generate_presigned_url(
        "upload_part",
        Params={
            "Bucket": settings().bucket_name,
            "Key": media_key(photo, "pending", "-motion" if motion else ""),
            "UploadId": upload_id,
            "PartNumber": number,
            "ContentLength": min(chunk, size - (number - 1) * chunk),
        },
        ExpiresIn=600,
    )


def finish_targets(photo, body: FinishUpload) -> None:
    for motion, parts in [(False, body.parts), (True, body.motion_parts)]:
        field = "motion_multipart_id" if motion else "multipart_id"
        upload_id = getattr(photo, field)
        if not upload_id:
            continue
        size = photo.motion_size if motion else photo.size
        if [part.number for part in parts] != list(range(1, math.ceil(size / part_size(size)) + 1)):
            raise HTTPException(422, "All upload parts must be completed in order.")
        key = media_key(photo, "pending", "-motion" if motion else "")
        try:
            s3().complete_multipart_upload(
                Bucket=settings().bucket_name,
                Key=key,
                UploadId=upload_id,
                MultipartUpload={
                    "Parts": [{"PartNumber": part.number, "ETag": part.etag} for part in parts]
                },
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "NoSuchUpload":
                raise
            # Completion may have succeeded before a prior request timed out.
            if s3().head_object(Bucket=settings().bucket_name, Key=key)["ContentLength"] != size:
                raise HTTPException(409, "Upload completion could not be verified.") from exc
        setattr(photo, field, "")
