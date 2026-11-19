# Setup: GitHub Codespaces (free tier), local, or Colab

Everything in this course runs on a **2-core CPU machine**. There's no GPU and no PyTorch. Embeddings use small ONNX models via `fastembed`.

## Option A — GitHub Codespaces (recommended)

### 1. Add your API key as a Codespaces secret (one time)
GitHub → your profile → **Settings → Codespaces → Secrets → New secret**
- Name: `ANTHROPIC_API_KEY`, Value: your key from [platform.claude.com](https://platform.claude.com/)
- Repository access: select `agentic-ai-course`
- Optional free alternatives: `GEMINI_API_KEY` ([Google AI Studio](https://ai.google.dev/gemini-api/docs/openai)), `GROQ_API_KEY` ([Groq console](https://console.groq.com/docs/openai))

Secrets are injected as environment variables. If you add a secret while a codespace is running, **restart the codespace** (or reload the window) to pick it up.

### 2. Create the codespace
On the repo page: **Code → Codespaces → Create codespace on main**, then choose the **2-core** machine.
The first start takes a few minutes. `.devcontainer/devcontainer.json` runs:
```bash
pip install -r requirements.txt && pip install -e . && python -m shopease.data
```
That installs the course packages and generates the ShopEase sample data.

### 3. Open a notebook
Open `week-1/practice/day-01-tokens-and-cost.ipynb`, pick the **Python 3.12** kernel (top right), and run the first cell. It calls `check_setup()` and shows which keys were found.

### Free-tier tips (stretch your monthly hours)
- Use the **2-core** machine. Core-hours are billed per core, so 4-core uses your quota twice as fast. Check your current free allowance at [github.com/settings/billing](https://github.com/settings/billing).
- **Stop the codespace** when you're done (Codespaces list → ⋯ → Stop). Set the idle timeout to 15–30 min in Settings → Codespaces.
- Delete old codespaces you don't need, since storage counts too.
- Day 14 framework packages are not preinstalled. Install them only when you get there: `pip install -r requirements-frameworks.txt`.

## Option B — Local machine
```bash
git clone https://github.com/Rahulverma5/agentic-ai-course
cd agentic-ai-course
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt && pip install -e . && python -m shopease.data
echo 'ANTHROPIC_API_KEY=sk-ant-...' > .env           # never commit .env (it's git-ignored)
```
Open the notebooks in VS Code or `jupyter lab` (`pip install jupyterlab`).

## Option C — Google Colab / Kaggle
Each notebook's first cell detects Colab/Kaggle and clones + installs the repo automatically. Add your key under Colab 🔑 *Secrets* or Kaggle *Add-ons → Secrets* as `ANTHROPIC_API_KEY`.

## Cost
- Notebooks default to `claude-haiku-5-5` for bulk work (classifiers, judges, summaries) and `claude-opus-5-5` for agents.
- Every notebook ends with `tracker.summary()`, so you always see what you spent. With caching (Day 5) the whole course should cost a few dollars.
- To try everything for free, use the `🆓 free swap` cells with Gemini or Groq (quality and tool use are less reliable).

## Troubleshooting
| Problem | Fix |
|---|---|
| `ANTHROPIC_API_KEY is not set` | Add the Codespaces secret, then restart the codespace; or create `.env` |
| `ModuleNotFoundError: course_utils` / `shopease` | Run `pip install -e .` from the repo root, then restart the kernel |
| `ShopEase data not found` | `python -m shopease.data` |
| Day 6 model download is slow | First run downloads ~70–130 MB of small ONNX models; later runs use the cache |
| Free provider model not found | Set `FREE_GEMINI_MODEL` / `FREE_GROQ_MODEL` to a current model name |
