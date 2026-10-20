"""Idempotent local Floci and PostgreSQL bootstrap. Never used in production."""

import asyncio
import time

from app.core.config import settings
from app.manage import migrate, seed_local
from app.services.aws import s3, ses
from botocore.exceptions import BotoCoreError, ClientError

cfg = settings()
if cfg.aws_region != "eu-central-1":
    raise RuntimeError("Local Floci bootstrap expects eu-central-1")
for _attempt in range(60):
    try:
        buckets = s3().list_buckets()
        break
    except BotoCoreError, ClientError:
        time.sleep(1)
else:
    raise RuntimeError("Floci did not become ready")
if cfg.bucket_name not in [bucket["Name"] for bucket in buckets.get("Buckets", [])]:
    s3().create_bucket(
        Bucket=cfg.bucket_name, CreateBucketConfiguration={"LocationConstraint": "eu-central-1"}
    )
s3().put_bucket_cors(
    Bucket=cfg.bucket_name,
    CORSConfiguration={
        "CORSRules": [
            {
                "AllowedOrigins": ["http://localhost:5173", "http://web:5173"],
                "AllowedMethods": ["GET", "POST", "PUT"],
                "AllowedHeaders": ["*"],
                "ExposeHeaders": ["ETag"],
                "MaxAgeSeconds": 3600,
            }
        ]
    },
)
s3().put_bucket_lifecycle_configuration(
    Bucket=cfg.bucket_name,
    LifecycleConfiguration={
        "Rules": [
            {
                "ID": "expire-pending",
                "Status": "Enabled",
                "Filter": {"Prefix": "pending/"},
                "Expiration": {"Days": 1},
                "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 1},
            }
        ]
    },
)
ses().verify_email_identity(EmailAddress=cfg.email_from)


async def initialize() -> None:
    await migrate()
    await seed_local()


asyncio.run(initialize())
print("Local AWS and SQL ready. Guest: DEMO-LOVE-2027. Admin: DEMO-ADMIN-2027")
