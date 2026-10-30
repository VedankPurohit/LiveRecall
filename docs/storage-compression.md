# Screenshot storage and compression

Screenshots remain individual images so the timeline, OCR, CLIP, and export can
read any frame without a video decoder or a shared frame dependency.

The existing automatic compression setting now checks for eligible images at API
startup and hourly afterward. It remains disabled by default. It uses the saved
age, format, and quality settings. Manual compression and automatic compression share
one worker. A failed or missing image does not block later images.

Choose JPEG or WebP under Settings > Storage > Compression format. JPEG remains
the default for existing settings files and new installations. The saved choice
applies to automatic compression, Compress now, and confirmed force recompression.
Changing it does not convert images already marked compressed. WebP usually
reduces bytes more and takes more encoding CPU; both choices are lossy.

An API request can override the saved format for one operation. Send this JSON to
`POST /api/v1/compression/start`:

```json
{"older_than_days": 30, "quality": 85, "image_format": "webp"}
```

That endpoint skips images already marked compressed. To convert already
compressed JPEGs, the existing force-recompress preview and confirmation flow
supports the same `image_format` field. Recompression is lossy, even when the
quality number is higher. Make a verified backup first. This change does not
automatically convert any existing library to WebP.

The compressor writes one candidate in the screenshot directory, flushes and
fsyncs it, and fully decodes it before touching the database. It discards candidates
that are as large as the original. For smaller candidates, one database
transaction updates the path and compression metadata. On POSIX systems it also
fsyncs the parent directory before the transaction, so the new directory entry
precedes the database reference. A directory-sync failure aborts the replacement
and leaves the original intact. Only after a successful commit
does it delete the original. OCR text, embeddings, screenshot IDs, and capture
timestamps remain unchanged. The first recorded original size survives later
force recompression.

A process interruption before the database commit can leave an unreferenced
`*.compressed-*` candidate. An interruption after commit but before deletion can
leave an extra original. Both cases retain the referenced image. Do not delete
files by filename pattern alone. Compare against database paths before cleaning
orphans. These process-interruption guarantees apply on all supported platforms.
Python cannot fsync directory handles on Windows, so durable ordering across a
power failure is not promised there. POSIX fsync ordering still depends on the
filesystem and storage hardware honoring sync requests. No bulk orphan cleanup
or live-library migration ships with this change.

## Measure your own library

```sh
python scripts/benchmark_image_compression.py /path/to/screenshots \
  --samples 24 --output /path/to/metrics.json
```

The benchmark reads an evenly spaced sample and encodes only in memory. Its
output contains aggregate byte counts, encoding time, and full-resolution
luminance SSIM. It does not export screenshots, screenshot filenames, or OCR.
It includes JPEG quality 85 and 75, WebP quality 85 and 80, a faster WebP85
variant, and lossless WebP. Quality values are not directly comparable across
codecs. SSIM does not establish OCR accuracy or small colored-text legibility.

On one 24-image sample, WebP85 reduced bytes by 48.7% versus the existing JPEGs,
with mean luminance SSIM 0.989 and minimum 0.982. JPEG85 reduced bytes by 19.6%.
Lossless WebP grew the same sample by 152%. These are sample measurements, not
a promised saving for another library. WebP takes more encoding CPU than JPEG;
the worker handles one image at a time.

The pinned Pillow 10.3 build already supports WebP. AVIF is not supported by that
build without additional dependencies. Video/delta storage could exploit changes
between adjacent screenshots, but needs indexed segments, random-frame retrieval,
recoverable writes, and new backup/export behavior. It is a separate storage design.

## Retained text search

Archiving older history can remove every CLIP image vector while leaving newer
OCR, FTS and text vectors intact. Text-only search no longer requires an image
vector. Auto search uses the available text indexes when the image index is
empty, without loading CLIP. Explicit image search still asks the user to sync
image embeddings first. This does not recompute or rewrite retained history.

## External disks

The current app stores absolute screenshot paths in SQLite. Moving the whole data
directory and leaving a symlink at its original location preserves those paths,
but the drive must remain attached. Unplugging it breaks database access and new
capture; the app has no disk-offline fallback. Keep the app stopped during any
whole-directory move and verify the copy before removing the source.

Keeping the database and new captures local while placing older screenshots on
an external disk needs an archive-aware retrieval flow, including an explicit
offline state. This change does not add one and does not relocate user data.

Codec references: [Pillow image format documentation](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#webp)
and [WebP compression techniques](https://developers.google.com/speed/webp/docs/compression).
