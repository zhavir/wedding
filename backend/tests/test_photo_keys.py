import pytest
from app.db.models import Photo
from app.services.photos import media_key, upload_prefix


@pytest.mark.parametrize(
    ("filename", "content_type", "expected"),
    [
        ("IMG_1234.JPG", "image/jpeg", "IMG_1234.JPG"),
        ("holiday.HEIC", "image/heic", "holiday.HEIC"),
        ("clip.MOV", "video/quicktime", "clip.MOV"),
        ("memory", "image/png", "memory.png"),
        ("../../photo.jpg", "image/jpeg", "photo.jpg"),
        (r"C:\photos\photo.jpg", "image/jpeg", "photo.jpg"),
    ],
)
def test_original_keys_preserve_safe_filename_and_extension(filename, content_type, expected):
    photo = Photo(
        id="unique-id",
        storage_prefix=upload_prefix("Mario Rossi"),
        original_filename=filename,
        content_type=content_type,
        motion_content_type="video/quicktime",
    )
    assert media_key(photo, "originals") == f"originals/guests/Mario-Rossi/unique-id-{expected}"
    assert media_key(photo, "originals", "-motion").endswith(".mov")
    assert media_key(photo, "pending") == "pending/guests/Mario-Rossi/unique-id"
    assert media_key(photo, "previews", ".webp").endswith("/unique-id.webp")


@pytest.mark.parametrize("prefix", ["", "old-invitation/", "guest/"])
def test_existing_uploads_keep_their_keys(prefix):
    photo = Photo(id="existing", storage_prefix=prefix, original_filename="photo.jpg")
    assert media_key(photo, "originals") == f"originals/{prefix}existing"
    assert media_key(photo, "originals", "-motion") == f"originals/{prefix}existing-motion"


def test_guest_folder_is_safe_and_fits_database_column():
    assert upload_prefix("../Mario / Rossi\\") == "guests/Mario-Rossi/"
    assert upload_prefix("...") == "guests/guest/"
    assert len(upload_prefix("a" * 100)) <= 65


def test_still_photo_cleanup_does_not_require_motion_metadata():
    photo = Photo(id="still", storage_prefix=upload_prefix("Mario"), motion_content_type="")
    assert media_key(photo, "originals", "-motion") == "originals/guests/Mario/still-motion"
