from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

import boto3
from botocore.config import Config

from app.core.config import settings

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client
    from mypy_boto3_ses.client import SESClient


@lru_cache
def s3(public: bool = False) -> S3Client:
    cfg = settings()
    return boto3.client(
        "s3",
        region_name=cfg.aws_region,
        endpoint_url=cfg.s3_public_endpoint if public else cfg.aws_endpoint_url,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            connect_timeout=5,
            read_timeout=10,
            retries={"max_attempts": 2},
        ),
    )


@lru_cache
def ses() -> SESClient:
    cfg = settings()
    client_session = (
        boto3.Session(profile_name=cfg.ses_profile) if cfg.ses_profile else boto3.Session()
    )
    return client_session.client(
        "ses",
        region_name=cfg.ses_region or cfg.aws_region,
        endpoint_url=cfg.ses_endpoint_url or cfg.aws_endpoint_url,
        config=Config(connect_timeout=5, read_timeout=10, retries={"max_attempts": 0}),
    )
