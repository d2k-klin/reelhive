<img src="assets/brand/mr-d-laptop@2x.webp" alt="Mr.D, the ReelHive mascot" align="right" width="170">

# ReelHive

> Your notes in, a finished product video out.

[![CI](https://github.com/d2k-klin/reelhive/actions/workflows/ci.yml/badge.svg)](https://github.com/d2k-klin/reelhive/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Local first](https://img.shields.io/badge/runs-locally-green.svg)](docs/privacy.md)

![A 20-second video made with ReelHive](assets/demo/demo.gif)

*Made with ReelHive from [assets/demo/brief.yaml](assets/demo/brief.yaml). With sound: [demo.mp4](assets/demo/demo.mp4).*

## What ReelHive does

Making a short product video usually means writing a script, recording a voice-over, grabbing screenshots, finding music and editing it all together. ReelHive does that work for you.

You write a few rough notes: who the video is for, the story you want to tell, the points that matter and how it should end. Add your product's website if you have one. A team of AI agents then takes over the storytelling:

1. **Research.** They read your website to learn what the product is, how its names are spelled and what it offers.
2. **Write.** They turn your notes into a story, with narration sized to the length you asked for and a polished closing line.
3. **Design.** They plan every scene: a title screen, a layout for each point, on-screen headlines, and the screenshots or images to show.
4. **Produce.** A natural-sounding voice reads the narration, background music is picked to match the mood, and every scene is timed to the voice.
5. **Check.** A reviewer checks the cut against the brief: the length, the pace, every key point told, the text fitting on screen. Anything that fails is fixed and checked again.
6. **Render.** You get a finished video, plus the script and every file that went into it.

Everything runs on your own machine. Only text goes to the AI service you choose, and your images and recordings stay with you. See [Privacy](docs/privacy.md).

## You decide how much to control

| Level | What happens |
| --- | --- |
| **Low** | You write the notes; the agents do everything else and deliver the video. |
| **Medium** | You also set the tone, brand and music, and review the script before production. |
| **High** | You direct every scene yourself: text, voice, timing and images. |

You can work in the browser-based studio, or from the terminal with a brief file.

## Quick start

```bash
git clone https://github.com/d2k-klin/reelhive && cd reelhive
make setup
uv run reelhive ui
```

Requirements, choosing your AI service and your first terminal run are in [Getting started](docs/getting-started.md).

## Documentation

| Guide | What's in it |
| --- | --- |
| [Getting started](docs/getting-started.md) | Install, first video, customization levels, every command |
| [The studio](docs/studio.md) | A tour of the studio, and one-click quick actions |
| [UI user guide](docs/ui-guide.md) | The studio, screen by screen |
| [Brief reference](docs/brief-reference.md) | Every brief field, by level |
| [Visuals](docs/visuals.md) | Screenshots, your own images and generated images |
| [AI providers](docs/providers.md) | Choosing and configuring the AI service |
| [Limits](docs/limits.md) | Durations, text lengths, image sizes, voices and formats |
| [Privacy and credit](docs/privacy.md) | What leaves your machine, and the ReelHive credit |
| [Architecture](docs/architecture.md) | How the agents and steps fit together |
| [All docs](docs/README.md) | Everything else, including the plan and learning notes |

Every folder also has a README explaining what's in it and how to extend it.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) and the [evals](evals/README.md).

## License

Code: [Apache-2.0](LICENSE). The Mr.D name and artwork are not covered by the code license ([assets/brand/LICENSE.md](assets/brand/LICENSE.md)); the illustrations were made with AI from the Mr.D artwork and curated by hand. The placeholder music in `assets/music` is public domain (CC0-1.0). Acknowledgements are in [Architecture](docs/architecture.md#built-on).
