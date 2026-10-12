# Privacy and credit

ReelHive runs on your machine. This page lists what, if anything, leaves it, and how the ReelHive credit works.

## What leaves your machine

| Data | Leaves your machine? |
| --- | --- |
| Brief text, script, image filenames and captions, page titles | Yes, to your agent provider (Claude, Bedrock, OpenAI or GitHub Copilot); no, with Ollama |
| Product website text (when you give a website) | Yes, the research step sends the readable text of up to 10 pages to your agent provider; no, with Ollama |
| Text of your documents (PDFs and decks) | Yes, the research step sends the page text to your agent provider; no, with Ollama. The page images stay local |
| Screenshots, and the layout regions measured on them | Screenshots no; region labels (the heading of each region) go with the page titles |
| Your images | No, unless `describe_images: true` |
| Rendered frames | No, unless `frame_review: true`: then one still per shot goes to your review provider |
| Image prompts | Yes, to OpenAI, only when `generate` is on |
| Your video clips | No (a poster frame per clip only with `describe_images: true`) |
| Audio, video, login state | No, until you publish |
| The finished video, its subtitles and the post copy | Only when you publish, and only to the platforms you approve: straight from your machine to each platform under your account ([publishing.md](publishing.md)). The copy is drafted by your agent provider from the brief and narration |
| Publishing sign-ins (tokens) | No: kept in `~/.reelhive/accounts`, owner-only, sent only to the platform they belong to |

## The ReelHive credit

Every video ends with a short **Made with ReelHive by Mr.D** card (`credit: end`), or carries a small corner badge (`credit: corner`). To turn the visible credit off:

```bash
REELHIVE_DISABLE_CREDIT=true uv run reelhive run brief.yaml
```

An invisible MP4 metadata tag is always written.
