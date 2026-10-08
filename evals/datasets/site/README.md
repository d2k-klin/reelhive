# `evals/datasets/site`

**Overview.** A tiny static web app ("Acme Cloud") that screenshot briefs capture. The eval harness serves it on a random 127.0.0.1 port, so screenshot discovery, capture and masking run for real without touching the internet.

## What's here

| Page | Purpose |
| --- | --- |
| `index.html` | Home, linking to the other pages (discovery starts here) |
| `dashboard.html` | Product UI with numbers, the natural pick for "show the product" scenes |
| `reports.html` | A second product page |
| `settings.html` | Holds a fake API key in `.api-key`, so masking is exercised (briefs mask `.api-key`) |

## Extending

Add a page and link it from the nav in every page, so discovery finds it. Keep it static (no JavaScript frameworks, no external assets) so captures are deterministic, and refresh the eval baseline.
