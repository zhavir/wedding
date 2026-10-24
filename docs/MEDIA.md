# Uploads and moderation

Guests sign in with their invitation link or code before uploading. Everything goes to private S3 storage. Completing an upload validates the actual file and creates a WebP preview; **it does not publish anything**.

Open `/admin`, choose **Gallery**, and open a record to preview the image/video. Check **Visible in gallery** and save, or select completed records and choose **Make visible in gallery**. Uncheck it to remove an item from subsequent gallery requests. A file must be successfully processed before publication. Previously issued signed URLs expire after one hour; unpublishing cannot recall an original already downloaded.

- Images: JPEG, PNG, WebP and HEIC/HEIF; up to 25 MB and 60 megapixels.
- Videos: MP4, MOV and WebM; no application size/duration cap; approximately 8K resolution. The server inspects the actual container and extracts a WebP poster using bounded ffmpeg processes.
- Live Photos: export **unmodified originals** from Apple Photos, giving a JPEG/HEIC still and its paired MOV. Select both files in the same picker; matching filename stems pair automatically. They remain paired as one gallery item, with both original files available for download. A website cannot force the operating system picker to supply both resources; if only a still is provided, motion cannot be reconstructed.

The gallery loads only small WebP images until a viewer is opened. Videos use native controls, `playsinline`, and `preload="none"`; they do not autoplay. MOV/HEVC playback depends on the browser/device. Download originals when a browser cannot play their codec. This implementation does not transcode or alter original media. Select H.264 MP4 when universal inline playback is important.

“Load more” fetches another page; “Load all” fetches the remaining pages and can be stopped. The viewer can fetch subsequent pages while navigating. Keyboard arrows, visible buttons and horizontal touch swipes are supported. Escape closes it and returns focus to the selected thumbnail.

## Upload selection and recorded metadata

Guests can select multiple files on a phone or computer, or drop multiple files onto the upload form on a computer. A Live Photo uses its original still image plus an exported companion motion file. Browser file pickers do not consistently expose Apple's paired asset automatically; export both components when necessary.

The database records the authenticated invitation owner and name, original filename, server upload/start and completion timestamps (Unix seconds), declared type and validated size, detected dimensions and codec/format, duration for video or Live Photo motion, and the original file's SHA-256 digest. Identity and timestamps come from the server, not guest-supplied metadata. For paired Live Photos, dimensions and digest describe the still image; duration describes its motion. These details are visible in Gallery. Embedded EXIF is retained in the untouched private original; gallery previews are separate WebP images.

New objects are grouped by the authenticated uploader's stable invitation ID: `pending/<uploader-id>/<media-id>`, `originals/<uploader-id>/<media-id>`, and `previews/<uploader-id>/<media-id>.webp`. Live Photo motion uses the same folder and a `-motion` suffix. Stable IDs prevent name changes and duplicate names from mixing uploads. Existing objects retain their recorded legacy layout and remain readable; no originals are moved or recompressed by the migration.

The gallery accepts mixed batches of images and videos through multiple selection or drag-and-drop. Both MIME allowlists and server-side image/video decoding are enforced: renaming a document or executable to `.jpg` or `.mp4` does not make it valid media. Rejected files never become completed originals or public gallery entries.

## One picker and large videos

Select images and videos together in the gallery, or drag them onto the same upload area. Selected files show local previews before uploading; unsupported browser codecs show a filename fallback. There is no gallery consent checkbox. A still image and MOV with the same filename stem are automatically treated as a Live Photo pair; other files upload independently.

Files above 64 MiB use direct S3 multipart transfers. Video inspection uses authenticated S3 range requests and server-side copies, so large originals are not loaded entirely into API memory or Lambda temporary storage. Larger videos retain source ETag metadata for idempotent copying; the SHA-256 database field is populated only for media processed locally in memory.

AWS service limits still apply (S3 currently supports up to 10,000 parts of 5 GiB each). Lambda request timeouts and codec support can affect processing; failed completion can be retried while the pending upload is valid. This removes the previous 100 MB / three-minute application limits, not AWS platform limits. Abandoned multipart uploads are automatically aborted after one day. Reference: https://docs.aws.amazon.com/AmazonS3/latest/userguide/qfacts.html .

## Audience targeting

Use **Visible to guests** to select multiple guests. A photo without targets is available to every authenticated guest; a targeted photo is returned only to those selected guests. This restriction applies to both the gallery and carousel. **Visible in carousel** selects still images independently of gallery approval. The carousel fetches all eligible preview links in one authenticated request. Upload timestamps are displayed as UTC date/time in the admin.
