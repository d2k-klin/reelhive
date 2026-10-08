# `evals/rubrics`

**Overview.** The fixed instructions the LLM judge scores with. They have explicit anchors for 1, 3 and 5, so scores mean the same thing from run to run and provider to provider.

## What's here

| File | Judges |
| --- | --- |
| [`script.md`](script.md) | The script: hook, clarity, audience fit, storyline adherence, call to action |
| [`image-prompts.md`](image-prompts.md) | Concept image prompts: relevance to the scene, style consistency, and no product UI |

## Changing a rubric

A rubric change moves every judge score, so treat it like a prompt change: CI's eval gate runs on it, and the baseline must be refreshed in the same PR. Keep the anchors concrete and observable ("the first sentence names a tension the audience recognises"), not vague ("good hook"). M6's suggestion metric will add `suggestions.md` here.
