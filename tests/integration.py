"""Black-box integration against the actual API, PostgreSQL and Floci S3."""

import asyncio
import hashlib
import http.cookiejar
import io
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from app.db.models import Photo
from app.db.session import engine, sessions
from PIL import Image
from sqlalchemy import update

base = os.environ.get("API_URL", "http://localhost:8000") + "/api"
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def request(path, method="GET", data=None, token="", expected=200):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(
        base + path,
        body,
        method=method,
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    try:
        with opener.open(req) as res:
            assert res.status == expected
            return json.load(res)
    except urllib.error.HTTPError as exc:
        assert exc.code == expected, (exc.code, exc.read())
        return {}


def s3_url(url):
    # Container DNS: retain the signed Host while connecting to Floci's service name.
    parts = urlsplit(url)
    if parts.hostname == "localhost" and "api:8000" in base:
        return urlunsplit(
            (
                parts.scheme,
                "floci:4566",
                parts.path,
                parts.query,
                parts.fragment,
            )
        ), parts.netloc
    return url, parts.netloc


request("/health")
request("/photos", expected=401)
request("/session", "POST", {"code": "NOT-AN-INVITE"}, expected=401)
session = request("/session", "POST", {"code": "DEMO-LOVE-2027"})
token = ""
rsvp = {
    "email": "test@example.com",
    "attending": True,
    "guests": [{"name": "Integration guest", "dietary": "Vegetarian"}],
    "message": "See you there",
    "consent": True,
}
request("/rsvp", "PUT", rsvp, token)
assert request("/rsvp", token=token)["rsvp"] == rsvp
request("/rsvp", "PUT", {**rsvp, "guests": [{"name": "Guest"}] * 3}, token, 422)
request("/rsvp", "PUT", {**rsvp, "email": "invalid"}, token, 422)
original = io.BytesIO()
Image.new("RGB", (1600, 1200), (100, 130, 100)).save(original, "JPEG", quality=97)
content = original.getvalue()
for index in range(2):
    upload = request(
        "/photos/upload",
        "POST",
        {
            "filename": "original.jpg",
            "content_type": "image/jpeg",
            "size": len(content),
            "caption": f"Integration memory {index}",
            "consent": True,
        },
        token,
    )
    boundary = "wedding-test-boundary"
    parts = []
    for key, value in upload["upload"]["fields"].items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode()
        )
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="original.jpg"\r\nContent-Type: image/jpeg\r\n\r\n'.encode()
        + content
        + f"\r\n--{boundary}--\r\n".encode()
    )
    url, host = s3_url(upload["upload"]["url"])
    with urllib.request.urlopen(
        urllib.request.Request(
            url,
            b"".join(parts),
            headers={
                "Host": host,
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
        )
    ) as response:
        assert response.status in (200, 201, 204)
    request(f"/photos/{upload['id']}/complete", "POST", token=token)
    request(f"/photos/{upload['id']}/complete", "POST", token=token)
# Complete uploads remain hidden until an administrator approves them.


async def approve_test_media():
    async with sessions()() as db:
        await db.execute(
            update(Photo)
            .where(Photo.caption.like("Integration memory %"), Photo.status == "complete")
            .values(gallery_visible=True)
        )
        await db.commit()
    await engine().dispose()


asyncio.run(approve_test_media())
page = request("/photos?limit=1", token=token)
assert page["cursor"]
next_page = request("/photos?limit=1&cursor=" + page["cursor"], token=token)
assert next_page["items"][0]["id"] != page["items"][0]["id"]
# Inspect actual stored object through its signed URL, not just a successful API response.
all_photos = []
cursor = None
while True:
    batch = request("/photos" + ("?cursor=" + cursor if cursor else ""), token=token)
    all_photos.extend(batch["items"])
    cursor = batch["cursor"]
    if not cursor:
        break
photo = next(p for p in all_photos if p["id"] == upload["id"])
url, host = s3_url(photo["original"])
with urllib.request.urlopen(urllib.request.Request(url, headers={"Host": host})) as response:
    assert hashlib.sha256(response.read()).digest() == hashlib.sha256(content).digest()
url, host = s3_url(photo["preview"])
with (
    urllib.request.urlopen(urllib.request.Request(url, headers={"Host": host})) as response,
    Image.open(io.BytesIO(response.read())) as preview,
):
    assert preview.format == "WEBP" and max(preview.size) <= 1200
print(
    "PASS: invitation, RSVP validation/storage, private access, direct S3 upload, original-byte integrity, preview and pagination"
)

# Exercise real multipart completion and server-side original preservation, above
# the 64 MiB transfer threshold, without changing the valid MP4 payload.
video_path = Path(__file__).parent / "browser" / "memory.mp4"
video = video_path.read_bytes()
video += bytes(65 * 1024**2 - len(video))
upload = request(
    "/photos/upload",
    "POST",
    {
        "filename": "large-memory.mp4",
        "content_type": "video/mp4",
        "size": len(video),
        "caption": "Integration memory multipart",
    },
)
assert upload["upload"]["multipart"]
completed = []
chunk_size = upload["upload"]["part_size"]
for number, offset in enumerate(range(0, len(video), chunk_size), start=1):
    signed = request(f"/photos/{upload['id']}/parts/{number}")
    url, host = s3_url(signed["url"])
    with urllib.request.urlopen(
        urllib.request.Request(
            url, video[offset : offset + chunk_size], method="PUT", headers={"Host": host}
        )
    ) as response:
        completed.append({"number": number, "etag": response.headers["ETag"]})
request(f"/photos/{upload['id']}/complete", "POST", {"parts": completed})
asyncio.run(approve_test_media())
page = request("/photos")
while not any(item["id"] == upload["id"] for item in page["items"]):
    assert page["cursor"], "Completed multipart video is missing from the gallery"
    page = request("/photos?cursor=" + page["cursor"])
media = next(item for item in page["items"] if item["id"] == upload["id"])
url, host = s3_url(media["original"])
with urllib.request.urlopen(urllib.request.Request(url, headers={"Host": host})) as response:
    digest = hashlib.file_digest(response, "sha256").digest()
assert digest == hashlib.sha256(video).digest()
url, host = s3_url(media["preview"])
with (
    urllib.request.urlopen(urllib.request.Request(url, headers={"Host": host})) as response,
    Image.open(io.BytesIO(response.read())) as preview,
):
    assert preview.format == "WEBP"
print("PASS: multipart video upload, range inspection, original-byte integrity and WebP poster")
