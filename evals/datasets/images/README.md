# `evals/datasets/images`

**Overview.** Fixture images for eval briefs that use `visuals.images`. They are simple, generated shapes, large enough (1920×1920) to pass the minimum resolution in every format, with captions that let the matcher pair them with scenes.

## What's here

| File | Caption (from `captions.yaml`) |
| --- | --- |
| `dashboard.png` | A cost dashboard with charts of monthly cloud spend |
| `team.png` | A small team around a laptop discussing a report |
| `chart.png` | A line chart trending down after savings |
| `phone.png` | A phone showing a notification about a finished task |
| `captions.yaml` | filename → caption, read by `visuals/provided.py` |

## Extending

Add PNG, JPEG or WebP files of at least 1280×1280, give each a caption with words the matcher can find in narration, and refresh the eval baseline. Keep files small (these are about 14 KB each) and free of real people, brands or products.
