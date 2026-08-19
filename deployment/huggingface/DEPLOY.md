# Deploying SentinelSat to Hugging Face Spaces

**Owner:** Software/Integration Lead — Week 5 (Hardening, Aug 12–18) task:
*"Deploy to Hugging Face Spaces (public or unlisted), fix deployment-specific
bugs (env vars, secrets management for the Groq key)."*

This deploys the whole project repo as the Space, so `data/`, `src/`, and
`deployment/` all ship together and `space_app.py`'s relative paths resolve
exactly like they do locally. There is nothing to build separately.

## 0. One-time prerequisites

- A free Hugging Face account.
- A free Groq API key from [console.groq.com](https://console.groq.com) (only
  needed if you want the **live** agent pipeline to work on the Space —
  Demo Mode works without it).
- `git` and, if you don't already have it, the `huggingface_hub` CLI:
  ```bash
  pip install -U huggingface_hub
  huggingface-cli login   # paste a token with "write" scope
  ```

## 1. Create the Space

Via the web UI: **New Space** → pick an owner/name → **SDK: Gradio** →
**Hardware: CPU basic (free)** → **Public** or **Unlisted**, your call
(the plan explicitly allows either — see `docs/planning/`).

Or via the CLI:
```bash
huggingface-cli repo create sentinelsat-ids --type space --space_sdk gradio
```

This gives you a new empty git repo at
`https://huggingface.co/spaces/<your-username>/sentinelsat-ids`.

## 2. Merge the Space card into your README

Hugging Face reads Space configuration (SDK, entry file, title, etc.) from a
YAML frontmatter block that must be the **very first thing** in the Space's
root `README.md`. This project's own `README.md` doesn't have one (it's a
plain project README), so merge the block from
`deployment/huggingface/README.md` into the top of the root `README.md`
before pushing — or, simpler, keep a separate copy of the root `README.md`
with the frontmatter prepended, specifically for the Space remote:

```bash
cat deployment/huggingface/README.md README.md > /tmp/space_readme.md
cp /tmp/space_readme.md README.md   # only on the branch/copy you push to the Space
```

The important field is:
```yaml
app_file: deployment/huggingface/space_app.py
```
That's what tells the Space to run the KB-build wrapper instead of
`src/dashboard/app.py` directly.

## 3. Point requirements.txt at the Space-specific one

Spaces auto-installs whatever `requirements.txt` sits at the **repo root**.
This project's root `requirements.txt` is the full dev set (training,
notebooks, the old Streamlit/FastAPI prototype). For the Space, swap in the
trimmed one so the free CPU tier's build doesn't spend time/disk on
dependencies the deployed dashboard never imports:

```bash
cp requirements.txt requirements.full.txt        # keep the dev one around
cp deployment/huggingface/requirements.txt requirements.txt
```

Do this only on the copy/branch you push to the Space remote — don't
commit this swap to your main development branch, since local dev (training
scripts, notebooks, `generate_demo_cache.py`) still needs the full set.

## 4. Set the Groq secret (never commit it)

Space Settings → **Variables and secrets** → **New secret**:
- Name: `GROQ_API_KEY`
- Value: your Groq key

`.env` is already gitignored (see root `.gitignore`) and must stay that
way — a Space secret becomes a normal environment variable inside the
container, which is exactly what `load_dotenv()` + `os.environ` already
expect, so no code changes were needed for this part. Nothing about this
project's env-var handling was broken; the KB build (below) was the actual
gap.

## 5. Push

```bash
git remote add space https://huggingface.co/spaces/<your-username>/sentinelsat-ids
git push space main
```

Large-ish CSVs (`data/raw/consolidated_dataset_raw.csv` ~4.3 MB,
`data/noised/noised_dataset.csv` ~6.1 MB) push fine as regular git blobs at
this size, but if either grows past ~10 MB later, switch them to Git LFS
before pushing (`git lfs track "data/**/*.csv"`) — Hugging Face's own push
size checks will otherwise reject the push.

## 6. Verify

- Space builds and the dashboard loads with the live telemetry stream —
  confirms the trimmed `requirements.txt` didn't drop something needed.
- Click each of the 5 **Demo Mode** buttons — confirms `demo_cache.json`
  shipped correctly and needs no secret.
- Check the Space's build/runtime logs for `[space_app] SPARTA knowledge
  base ready (11 documents).` — confirms the cold-start KB build actually
  ran (this is the bug this deployment config exists to fix; see
  `space_app.py`'s docstring).
- Only if you set the secret: click **🔍 Run Full Agent Analysis** once —
  confirms `GROQ_API_KEY` is wired up. Expect the SPARTA Analyst's answer
  to cite a real tactic ID (e.g. `ST0009`) instead of "No class mapping
  found" — that's the specific failure mode a missing KB produces.

Before pushing, you can run the same checks locally without spending a
Groq call — see `deployment/huggingface/verify_space_ready.py`.

## Known free-tier constraints (Week 5 "hardening" honesty, not a defect)

- **Ephemeral disk — confirmed against Hugging Face's own docs, not
  assumed.** Free-tier Spaces have no persistent storage by default: "This
  disk space is ephemeral, meaning its content will be lost if your Space
  restarts or is stopped" ([Disk usage on Spaces](https://huggingface.co/docs/hub/en/spaces-storage)).
  That means `chroma_sparta/` (and whatever chromadb's default embedding
  function downloads — a small sentence-embedding ONNX model, tens of MB,
  fetched from the internet the first time it's used) gets rebuilt **on
  every cold start**, not just once at first deploy. `space_app.py` already
  makes this idempotent and cheap on the KB side (11 short documents, a
  fraction of a second once the embedding model is warm), but the
  embedding-model download itself will repeat after every sleep/restart
  unless you attach a [persistent Storage Bucket](https://huggingface.co/docs/hub/en/storage-buckets)
  — worth doing if cold-start latency on the live agent path matters for
  your demo; not worth the extra setup just for Demo Mode, which never
  touches Chroma at all.
- **Cold starts sleep.** A free CPU Space sleeps after inactivity; the
  first visitor after a sleep waits through a rebuild-free but slow
  container start plus the KB-build step above.
- **Groq free tier: 12,000 tokens/minute, 100,000 tokens/day.** A public
  Space sharing one key across all visitors' live-analysis clicks will hit
  this fast. Demo Mode exists specifically so a reviewer never needs to
  spend that budget. If you expect real traffic on the live button, put the
  Space in **Unlisted** mode instead of Public, per the plan's Phase 6
  fallback guidance.
- **Single shared simulator instance.** `src/dashboard/app.py` documents
  this itself (`sim = TelemetryReplaySimulator(...)` at module scope) — this
  is a v1, single-session demo, not per-visitor isolated state. Multiple
  concurrent visitors on the public Space will see and control the same
  stream. Out of scope to fix for Week 5; flagging here so it lands in the
  "known limitations" writeup (`docs/security/known_limitations.md`) rather
  than surprising someone during the demo.
