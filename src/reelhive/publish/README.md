# `publish`

**Overview.** Publishing a finished video to YouTube, LinkedIn, TikTok and Instagram Reels, from the user's machine, with the user's own developer apps and accounts. Nothing here runs during a video run: publishing starts only when the user asks, and posts only after they approve the copy.

## What's here

| Path | What it is |
| --- | --- |
| [`accounts.py`](accounts.py) | Signed-in accounts per machine in `~/.reelhive/accounts/<platform>.json` (`REELHIVE_HOME` moves it), written owner-only. `Account.public()` is what the CLI and studio may show: never a token. |
| [`oauth.py`](oauth.py) | Sign-in: OAuth 2.0 authorization code with a loopback redirect to `http://localhost:<port>/callback`, a random `state` and PKCE (S256) where the platform supports it. A one-shot listener on 127.0.0.1 takes the code only with its own state, never logs the query, then the code is exchanged and the account saved. |
| [`http.py`](http.py) | `send()`: one request with bounded retries (429, 5xx, dropped connections; honours `Retry-After`) and errors that name the step and the platform's reason, never a token. `ranges()` / `read()` for chunked uploads. |
| [`platforms/`](platforms) | One adapter per platform: sign-in, refresh, the platform's video rules, and the upload-and-post flow. |

The graph side lives elsewhere: [`../graphs/publish.py`](../graphs/publish.py) (the copy and post graphs), [`../nodes/publish_nodes.py`](../nodes/publish_nodes.py) (`ready` and `post_<platform>`), [`../agents/publisher.py`](../agents/publisher.py) (the copy) and [`../schemas/publish.py`](../schemas/publish.py) (copy limits and the job).

## Rules

- Client ids and secrets come from environment variables only; tokens stay in the accounts folder. Neither is ever written to a run folder, a log or a prompt.
- A post goes out under the user's name: the copy is approved by a person between the two graphs, and the CLI and studio ask again before posting.
- A platform that is already published for a run is never posted again; a post interrupted mid-upload is marked failed with a note to check the platform first.

## Extending: a new platform

1. Add the platform to `Platform`, `PLATFORMS` and `COPY_MODELS` in `schemas/publish.py`, with a copy model that enforces its limits.
2. Write `platforms/<name>.py`: subclass `Adapter` (`exchange`, `identify`, `refresh`, `check`, `post`) and register it in `platforms/__init__.py`.
3. Add a `post_<name>` node in `nodes/publish_nodes.py`, its settings to `Publishing` in `config.py`, and its guidance to `GUIDANCE` in `agents/publisher.py`.
4. Test it against a mock of the platform's API in `tests/unit/test_publish_platforms.py`, and document the developer-app setup in [docs/publishing.md](../../../docs/publishing.md).
