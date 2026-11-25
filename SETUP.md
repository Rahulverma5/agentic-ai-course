# Setup: GitHub Codespaces (free tier), local, or Colab, with the Gemini API

Everything in this course runs on a **2-core CPU machine** with a **free Gemini API key**. There's no GPU and no PyTorch; embeddings use small ONNX models via `fastembed`.

## 1. Get a free Gemini API key
1. Go to **[Google AI Studio → API keys](https://aistudio.google.com/apikey)** and sign in with a Google account.
2. **Create API key**, then copy it. Treat it like a password and never commit it.

## Option A — GitHub Codespaces (recommended)

### 2. Add the key as a Codespaces secret (one time)
GitHub → your profile → **Settings → Codespaces → Secrets → New secret**
- Name: `GEMINI_API_KEY`, Value: your key
- Repository access: select `agentic-ai-course`

Secrets are injected as environment variables. If you add a secret while a codespace is running, **restart the codespace** to pick it up.

### 3. Create the codespace
On the repo page: **Code → Codespaces → Create codespace on main**, then choose the **2-core** machine.
The first start takes a few minutes. `.devcontainer/devcontainer.json` runs:
```bash
pip install -r requirements.txt && pip install -e . && python -m shopease.data
```

### 4. Open a notebook
Open `week-1/practice/day-01-tokens-and-cost.ipynb`, pick the **Python 3.12** kernel, and run the first cell. It calls `check_setup()` and confirms the key was found.

### Codespaces free-tier tips
- Use the **2-core** machine (core-hours are billed per core). Check your allowance at [github.com/settings/billing](https://github.com/settings/billing).
- **Stop the codespace** when you're done, and set the idle timeout to 15–30 min (Settings → Codespaces).
- Day 14 framework packages are not preinstalled: `pip install -r requirements-frameworks.txt` when you get there.

## Option B — Local machine
```bash
git clone https://github.com/Rahulverma5/agentic-ai-course
cd agentic-ai-course
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt && pip install -e . && python -m shopease.data
echo 'GEMINI_API_KEY=your-key-here' > .env           # never commit .env (it's git-ignored)
```
Open the notebooks in VS Code or `jupyter lab` (`pip install jupyterlab`).

## Option C — Google Colab / Kaggle
Each notebook's first cell detects Colab/Kaggle and clones + installs the repo automatically. Add your key under Colab 🔑 *Secrets* or Kaggle *Add-ons → Secrets* as `GEMINI_API_KEY`.

## Models, quotas and cost

| Setting | Default | Used for |
|---|---|---|
| `COURSE_MODEL` | `gemini-flash-latest` | Agents and harder reasoning |
| `COURSE_CHEAP_MODEL` | `gemini-flash-lite-latest` | Bulk work: routers, judges, summaries, subagents |

- The defaults are **Google-maintained aliases** that point at the current Flash / Flash-Lite release. Because availability differs by account, `check_setup()` (first cell of every notebook) **lists the models your key can use** and switches to the best available Flash / Flash-Lite if a default isn't there. To pin exact model ids (recommended for reproducible evals), set the env vars, e.g. in `.env`: `COURSE_MODEL=<model id from the models page>`.
- **Free tier = $0**, but with **rate limits** (requests per minute and per day, per project). They change over time, and Pro models may not be on the free tier at all. Check **AI Studio → Usage / Rate limits** for your current numbers (and the rate-limits page in the [Gemini API docs](https://ai.google.dev/gemini-api/docs)).
- The course client **retries automatically** on `429` (rate limited) and `5xx` with exponential backoff, so a cell may pause for a while. That's expected on the free tier.
- If you hit the **daily** limit on Flash, switch the agent model to Flash-Lite for the day: `COURSE_MODEL=gemini-flash-lite-latest`. Or enable billing on the project (paid tier: much higher limits, pay per token).
- Every notebook ends with `tracker.summary()`. It shows tokens, plus an **estimate at paid prices** so you learn to reason about cost even while you pay $0. Update `course_utils/cost.py` from the [pricing page](https://ai.google.dev/gemini-api/docs/pricing) if prices change.

## Which Gemini API does the course use?
The course uses `client.models.generate_content` from the official `google-genai` SDK: the widely used, stable request/response API. Google also offers a newer **[Interactions API](https://ai.google.dev/gemini-api/docs/interactions-overview)** (server-side conversation state), and its docs now label `generateContent` as the "Generate Content API". Everything you learn here (function calling, thought signatures, caching, structured output) carries over.

## Troubleshooting
| Problem | Fix |
|---|---|
| `GEMINI_API_KEY is not set` | Add the Codespaces secret, then restart the codespace; or create `.env` |
| `429 RESOURCE_EXHAUSTED` that doesn't go away | You hit the per-day quota: wait for the daily reset, switch to Flash-Lite, or enable billing |
| `404 NOT_FOUND … is not found for API version …` | Model names differ by account and change over time. Re-run the setup cell: `check_setup()` lists the models **your key** can use and switches to the best Flash / Flash-Lite automatically. To choose yourself: `from course_utils import available_models; available_models()`, then set `COURSE_MODEL` / `COURSE_CHEAP_MODEL` (e.g. in `.env` or `os.environ` before the setup cell) |
| A thinking level is rejected | Not every model supports every level: use `thinking_level=None` (model default) or another level |
| `ModuleNotFoundError: course_utils` / `shopease` | Run `pip install -e .` from the repo root, then restart the kernel |
| Colab/Kaggle: `ImportError` in the setup cell, or a cell that was "auto-fixed" to import `projects.…` | The clone in `/content` is outdated, or the cell was edited. Run `!rm -rf /content/agentic-ai-course`, then **Runtime → Restart session**, re-open the notebook from GitHub (fresh cell), and run it again. Set `COURSE_BRANCH` to try another branch |
| `ShopEase data not found` | `python -m shopease.data` |
| Day 6 model download is slow | First run downloads ~70–130 MB of small ONNX models; later runs use the cache |
