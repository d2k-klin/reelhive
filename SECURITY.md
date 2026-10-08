# Security Policy

## Reporting a vulnerability

Please report security issues privately through the repository's [security advisory](https://github.com/d2k-klin/reelhive/security/advisories/new) feature, not in a public issue. We aim to acknowledge within 72 hours.

## Supported versions

ReelHive is pre-1.0. Security fixes go into the **latest release** only.

| Version | Supported |
| --- | --- |
| latest `0.x` | ✅ |
| older `0.x` | ❌ |

## Design guarantees

- **Local first.** ReelHive runs on your machine. Only agent calls (to the provider you choose) and, when enabled, image generation (to OpenAI) leave it. Ollama with generation off is fully offline.
- **No passwords.** `reelhive login` opens a visible browser where you sign in yourself; only the resulting session state is saved, with owner-only permissions. Keep `auth.json` out of Git.
- **Masking.** Screenshot `mask` selectors are blacked out by Playwright before any image is written.
- **Locked-down Copilot.** Copilot sessions expose only ReelHive's submit tool; every other permission request (shell, file writes) is denied, and config discovery, skills, hooks and Git operations are disabled.
- **Run folders stay local** and are gitignored. Images are embedded into the render by path checks that refuse anything outside the run folder.
- **Credentials** come from environment variables or standard provider mechanisms and are never written to run folders, logs or reports.
