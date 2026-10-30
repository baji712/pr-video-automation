# Short-form PR video automation — technical test (free-first)

**This repository is a technical validation, not a sales-ready video-production service.** It accepts CC0/public-domain photo candidates, composes a draft vertical MP4 with original synthetic audio, and checks its technical output. The result is explicitly marked as a draft, not a promotion for an actual business. No content is posted to social media.

## Operation

- On each push to `main`, GitHub Actions runs safety checks and makes an offline 12-second draft from a public-domain coffee photo bundled with scikit-image.
- `Actions` → `Validate video pipeline (no publishing)` → `Run workflow` runs either `demo` or `commons` test. `commons` queries Wikimedia Commons for photos whose metadata reports CC0/public domain and aborts when fewer than four distinct files qualify. This is a *technical* license filter; human review of image and other rights is still mandatory.
- A weekly Monday 10:17 JST schedule exists but is **disabled by default**. The `ENABLE_SCHEDULED_RENDER` repo variable must be set to `true` deliberately after checking cost, asset rights, and quality.
- The output artifact `pr-demo-for-human-review` (3-day retention) contains an MP4, `sources.json`, and `quality.json`. A public repository's Actions logs/artifacts may be accessible to others. Do not add client photos, PII, passwords, contracts, or unpublished assets to this repository.

## Guardrails

- Only use a **public** repository with standard GitHub-hosted runners; the workflow refuses to run for a private repo. If your billing settings change, review them before enabling any schedule.
- No Runway credits, purchased APIs, paid image services, subscriptions, posting, email sends, or ads.
- CC0 photos can have separate people, trademarks, or location-related restrictions. The pipeline writes provenance and never approves publication automatically.
- Still photos with panning are not real recorded motion. The proof-of-concept is not presented as a premium PR film, nor should it be shown to prospects as proven work.
- For an actual selling-quality campaign, use genuine client-owned video clips, specific marketing objectives, human rights review, and a creative quality pass first.

## Local execution

Python 3.11+, `ffmpeg`, `ffprobe`, and Noto CJK fonts are required.

```
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python video_pipeline.py --source demo
python video_pipeline.py --source commons --query 'coffee cafe' --min-photos 4
```

No new charges without express user approval. A successful automated render is not proof of commercial demand.