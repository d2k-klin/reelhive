# `publish/platforms`

**Overview.** One adapter per platform. Each knows how to sign in, refresh a token, check a video against the platform's own rules, and upload and post it with its copy. They share [`base.py`](base.py) and the retrying `send()` from [`../http.py`](../http.py).

## What's here

| File | Platform | Upload flow | Captions |
| --- | --- | --- | --- |
| [`base.py`](base.py) | `Adapter`, `Upload` (the finished video), `Posted` | – | – |
| [`youtube.py`](youtube.py) | YouTube Data API v3 | Resumable upload in 8 MiB chunks, continuing from the byte range YouTube reports on `308` | `video.srt` as an English caption track |
| [`linkedin.py`](linkedin.py) | LinkedIn Videos + Posts APIs | `initializeUpload`, a `PUT` per part (ETags kept in order), `finalizeUpload`, wait for `AVAILABLE`, then the post; commentary in LinkedIn's little text format | `video.srt` through `captionsUploadUrl` |
| [`tiktok.py`](tiktok.py) | TikTok Content Posting API | `FILE_UPLOAD` in 10 MB chunks (the remainder joins the last), then the post status; `draft` sends to the inbox, `direct` posts with the account's allowed privacy | – |
| [`instagram.py`](instagram.py) | Instagram Graph API (Facebook Login) | A `REELS` container with `upload_type=resumable`, the file to `rupload.facebook.com`, wait for `FINISHED`, `media_publish`, then the permalink | – |

`ADAPTERS` maps each platform to its adapter, and `overview()` reports per platform whether the developer app is configured and who is signed in (never a token).

## Extending

See [`../README.md`](../README.md#extending-a-new-platform). Keep every request going through `send()`, and every limit a platform documents in either the copy model (`schemas/publish.py`) or `check()`, so a video or caption the platform would reject is caught before anything is sent.
