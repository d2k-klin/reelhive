# Publishing

ReelHive can post a finished video to **YouTube**, **LinkedIn**, **TikTok** and **Instagram Reels**. It drafts the words that go with the video for each platform, shows them to you, and posts only after you approve. Uploads go straight from your machine to each platform, under your own accounts, through your own developer apps. ReelHive has no server in between.

## How it works

```
reelhive publish runs/<run> --to youtube,linkedin

  ready ─► publish        checks each platform, then drafts the copy (title, description, captions, hashtags)
     you review and edit  publish/job.json, or the Publish panel in the studio
  ready ─► post_youtube   uploads and posts, all platforms in parallel; each result is saved as it lands
        └► post_linkedin
```

- **`ready`** runs before any model call or upload. It checks that the run has a finished video, that each platform's developer app is configured, that you're signed in, and that the video meets the platform's rules (length and file size). A wrong orientation is only a warning: a 16:9 video on TikTok or Reels shows with bars.
- **`publish`** writes one post per platform, from your brief, the research and the narration, held to each platform's limits. It never invents a link, a number or a feature.
- **`post_<platform>`** uploads and posts. A platform that fails doesn't stop the others. Publishing again posts only to the platforms that aren't live yet, so nothing goes out twice.

## Publish a video

```bash
reelhive publish runs/<run> --to youtube,linkedin,tiktok,instagram
```

ReelHive drafts the posts, prints them, and asks `Post this video publicly to ... now?`. Answer `n` to stop there. You can edit `runs/<run>/publish/job.json` and run the command again, and the draft is kept. Other options:

| Option | Does |
| --- | --- |
| `--draft-only` | Draft and show the posts; post nothing |
| `--redraft` | Write new copy even if a draft exists |
| `--yes` | Post without the question (for scripts, after you've reviewed the draft) |

In the studio, a finished run has a **Publish** panel. Pick the platforms, draft, edit the copy, and confirm. The panel lists each post's link once it's live.

The video's subtitles (`video.srt`) go up as closed captions on YouTube and LinkedIn. Posts are labelled as AI-generated where the platform supports it: YouTube's altered or synthetic content setting and TikTok's AI-generated label. Set `publishing.label_ai: false` to turn that off.

## Set up each platform once

Each platform needs a developer app of your own: you hold its keys, and it posts as you. Create the app, put its id and secret in environment variables (never in `config.yaml`), register the redirect URI, then sign in:

```bash
reelhive connect youtube     # opens the browser; sign in and allow access
reelhive accounts            # what is set up and who is signed in
reelhive disconnect youtube  # forget the sign-in on this machine
```

The redirect URI is `http://localhost:8765/callback` (`publishing.redirect_port` changes the port). `reelhive accounts` prints it. Register exactly this URI in every app.

| Platform | Create the app | Environment variables | Grants | Before the platform's review |
| --- | --- | --- | --- | --- |
| YouTube | [Google Cloud console](https://console.cloud.google.com/apis/credentials): enable *YouTube Data API v3*, create an OAuth client of type *Desktop app* | `REELHIVE_YOUTUBE_CLIENT_ID`, `REELHIVE_YOUTUBE_CLIENT_SECRET` | `youtube.upload`, `youtube.force-ssl` (captions) | Uploads stay **private** until Google audits the project; ReelHive says so when it happens |
| LinkedIn | [LinkedIn developers](https://www.linkedin.com/developers/apps): add *Sign In with LinkedIn using OpenID Connect* and *Share on LinkedIn* | `REELHIVE_LINKEDIN_CLIENT_ID`, `REELHIVE_LINKEDIN_CLIENT_SECRET` | `openid`, `profile`, `w_member_social` (and `w_organization_social` for a page) | Sign-ins last 60 days; connect again when asked |
| TikTok | [TikTok for Developers](https://developers.tiktok.com/apps): add *Login Kit* and *Content Posting API* | `REELHIVE_TIKTOK_CLIENT_KEY`, `REELHIVE_TIKTOK_CLIENT_SECRET` | `user.info.basic`, `user.info.profile`, `video.upload`, `video.publish` | Direct posts are **private only** until TikTok audits the app; `draft` mode works before that |
| Instagram | [Meta for Developers](https://developers.facebook.com/apps): a business app with Instagram content publishing and Facebook Login for Business | `REELHIVE_META_APP_ID`, `REELHIVE_META_APP_SECRET` | `instagram_basic`, `instagram_content_publish`, `pages_show_list`, `pages_read_engagement`, `business_management` | Needs an Instagram **Business or Creator** account linked to a Facebook Page; sign-ins last 60 days |

## Settings

Optional, in `config.yaml`:

```yaml
publishing:
  redirect_port: 8765
  label_ai: true
  youtube:   {privacy: private, category_id: "28", notify_subscribers: false}   # private | unlisted | public
  linkedin:  {organization: null, visibility: PUBLIC}     # urn:li:organization:123 posts as that page
  tiktok:    {mode: draft, privacy: SELF_ONLY}            # draft: to your TikTok inbox; direct: posted at once
  instagram: {share_to_feed: true, account: null}         # account: the username, when several are linked
```

TikTok `draft` sends the video to your TikTok inbox. You finish it in the app and paste the drafted caption there, because TikTok's inbox doesn't take a caption from apps. `direct` posts at once with the caption, at a privacy level your account allows (`creator_info`), with comments, duets and stitches as configured.

## Where things are kept

| What | Where |
| --- | --- |
| Signed-in accounts (tokens) | `~/.reelhive/accounts/<platform>.json`, owner-only (`REELHIVE_HOME` moves the folder). Never in a run folder, a log or a prompt |
| Developer app id and secret | Environment variables only |
| Drafted copy, results, links | `runs/<run>/publish/job.json` |
| Progress and results | `runs/<run>/run.log.jsonl` (`publish.drafted`, `publish.posted`, `publish.failed`) |

If a post is interrupted mid-upload (the computer slept, the process was killed), it's marked failed with a note to check the platform first. Only the platform knows whether it went through, so ReelHive never retries it on its own.

## Limits

| Platform | Video | Copy |
| --- | --- | --- |
| YouTube | Any length ReelHive makes | Title 100, description 5,000 characters, no `<` or `>`; up to 15 tags, 30 characters each, 450 together |
| LinkedIn | 3 s to 30 min, 75 KB to 500 MB | Post 2,800 characters with up to 5 hashtags; video title 100 |
| TikTok | At least 3 s and up to your account's maximum, up to 4 GB | Caption 2,200 UTF-16 units (an emoji counts twice) |
| Instagram Reels | 3 s to 15 min, up to 1 GB | Caption 2,200 characters, up to 30 hashtags and 20 mentions |
