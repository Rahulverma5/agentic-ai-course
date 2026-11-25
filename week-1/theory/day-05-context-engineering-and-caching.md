[← Day 4](../../week-1/theory/day-04-workflow-patterns.md) · [Week 1 overview](../README.md) · [▶️ Practice notebook](../practice/day-05-context-and-caching.ipynb) · [Day 6 →](../../week-1/theory/day-06-rag-for-agents.md)

## Day 5 — Context engineering & prompt caching

⏱ 75 min theory · 30 min lab · 45 min capstone

**Goals:** treat the context window as a scarce resource; learn context rot, compaction, just-in-time retrieval and caching, with the math behind the savings.


### 🎥 Watch first (short videos)
- 🎥 [What Is Context Engineering? Why It Matters for AI Agents](https://www.youtube.com/watch?v=Qx0fCqpkBus): *IBM Technology (Anna Gutowska)*. prompt vs context engineering
- 🎥 [What is Prompt Caching?](https://www.youtube.com/watch?v=axuTuZ9ERv8): *community explainer*. why a stable prefix saves money
- 🎥 [From Context Engineering to AI Agent Harnesses (optional, longer)](https://www.youtube.com/watch?v=2Muxy3wE-E0): *Lance Martin (LangChain), High Signal podcast*. deep dive: reduce, offload, isolate context

> Durations are approximate. "Community explainer" means an independent creator; the written links in each section are the primary sources.

### 5.1 From prompt engineering to context engineering

**Intuition.** Prompt engineering = writing *one good instruction*. Context engineering = deciding **everything** the model sees at **every step**: system prompt, tool definitions, retrieved docs, history, tool results and memory. For agents, the second matters far more, because the context changes every loop.

```mermaid
flowchart LR
    subgraph Window["Context window at step k"]
        S[System prompt] --- T[Tool definitions] --- M[Memory / notes] --- H[History + tool results] --- Q[Latest message]
    end
    RET[Retrieval] -.just in time.-> H
    CMP[Compaction] -.shrinks.-> H
```

**Writing good system prompts ("the right altitude"):**
- ❌ Too low: brittle if/else rules ("If the user says X, reply Y").
- ❌ Too high: vague ("be helpful").
- ✅ Right altitude: role, goals, principles, hard constraints and examples of good behavior, organized in sections (`## Role`, `## Tools`, `## Policies`, `## Output style`).

📖 Deep dive: ⭐ [Anthropic — Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

### 5.2 Context rot and "lost in the middle"

**Intuition.** More context isn't free attention. As inputs grow, models get *less reliable* at using any one fact, and facts in the **middle** of long contexts are used worst.

```
Accuracy
  ▲  ●                                   ●      "Lost in the middle" (Liu et al., 2023):
  │    ●                              ●          U-shaped curve. Facts at the start and end
  │       ●                        ●             are used best.
  │          ●   ●   ●   ●   ●  ●
  └────────────────────────────────────► position of the relevant fact in the context
     start                 middle            end
```

**Practical consequences**
- Put **instructions at the top** (system) and the **current task/question at the end**.
- Keep the context **lean**: drop stale tool outputs and summarize old turns.
- A 1M-token window is a *ceiling*, not a target. Quality per token drops as you fill it.

📖 Deep dive: 📄 [Lost in the Middle (Liu et al., 2023)](https://arxiv.org/abs/2307.03172) · [Chroma — Context Rot (2025)](https://research.trychroma.com/context-rot)

### 5.3 Techniques to keep context small

| Technique | What it does | Pros | Cons | Use when |
|---|---|---|---|---|
| **Tool-output truncation** | Cap each result (e.g. 2k tokens) | Trivial, big win | Can cut needed info | Always |
| **Context editing** | Remove old tool results from history | Keeps reasoning, drops bulk | Model can't re-read removed data | Long tool-heavy loops |
| **Compaction** | Summarize old history into a short block | Unlimited-length sessions | Summary can lose details | Long conversations / long tasks |
| **Just-in-time retrieval** | Keep *pointers* (file paths, ids) and load on demand | Tiny context, fresh data | More tool calls | Large corpora, codebases |
| **Structured notes / memory** | Agent writes progress notes to a file | Survives resets | Needs a discipline in the prompt | Multi-hour tasks (Day 7) |
| **Subagents** | Delegate messy work, get a summary back | Isolates noise | Token cost, info loss | Research/exploration (Day 9) |

Simple manual context editing:

```python
def trim_old_tool_results(contents, keep_last=3, placeholder="[old tool result removed]"):
    """Keep only the last `keep_last` function responses in full; shrink older ones (Gemini Content list)."""
    seen = 0
    for content in reversed(contents):
        for part in content.parts or []:
            if part.function_response:
                seen += 1
                if seen > keep_last:
                    part.function_response.response = {"output": placeholder}
    return contents
```

**Compaction by hand** (there's no server-side compaction in `generateContent`, so you summarize yourself): when the history gets long, ask a cheap model to summarize everything except the last few turns, then continue from `[summary] + recent turns`.

```python
def compact(contents, keep_recent=6):
    if len(contents) <= keep_recent:
        return contents
    old, recent = contents[:-keep_recent], contents[-keep_recent:]
    transcript = "\n".join(f"{c.role}: {''.join(p.text or '' for p in c.parts or [])}" for c in old)
    summary = ask("Summarize this conversation for continuing it. Keep: decisions, facts from tools, "
                  f"open tasks, file/order ids.\n\n{transcript}", model=CHEAP_MODEL)
    return [user(f"[Summary of earlier conversation]\n{summary}")] + recent
```

> ⚠️ **Editing history interacts with caching.** Any change to earlier turns breaks the cached prefix from that point on (5.4). Trim or compact in big, rare batches, not a little every turn. Keep the cut on a clean boundary: never separate a function call from its response.

📖 Deep dive: 📘 [Gemini — Optimization (caching, batch)](https://ai.google.dev/gemini-api/docs/optimization) · ⭐ [Anthropic — Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) (provider-neutral)

### 5.4 Prompt caching: the biggest free win

**Intuition.** Each loop step resends the same prefix (system + tools + history). Caching lets the provider store the processed prefix, so the next call **reads** it at a fraction of the price and much faster. It's a **prefix match**: change one byte early and everything after it is a miss.

```
call 1: [system][tools][msg1][msg2]                   ← full price (prefix becomes cacheable)
call 2: [system][tools][msg1][msg2][tool result]      ← prefix served from cache (≈0.1× price)
                └───────── cached ─────────┘ └ new ┘
```

**Gemini has two kinds:** **implicit caching** is automatic on current models: reuse an identical prefix above a minimum size and the matching tokens are billed at a discount (cache hits aren't guaranteed). **Explicit caching** (`client.caches.create(...)` with a TTL) guarantees reuse for a big shared prefix, plus a small per-hour storage fee.

**Savings math.** Prefix of `P` tokens reused over `n` calls, base price `c` per token, write multiplier `w` (implicit: 1; providers with paid cache writes: ~1.25), read multiplier `r` (Gemini cached tokens: roughly 0.1):

$$\text{no cache} = nPc \qquad \text{cache} = wPc + (n-1)\,rPc \qquad \text{saving} \approx 1 - \frac{w + (n-1)r}{n}$$

For `n = 10`, `w = 1`, `r = 0.1`: saving ≈ 1 − (1 + 0.9)/10 = **81%** on the prefix tokens. Latency to first token also drops for long prefixes.

```python
# Implicit caching: nothing to configure. Keep the prefix (system instruction + tools + early turns) identical.
config = types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, tools=to_gemini_tools(TOOLS))
r = client.models.generate_content(model=MODEL, contents=contents, config=config)
print(r.usage_metadata.prompt_token_count, r.usage_metadata.cached_content_token_count)

# Explicit caching: create once with a TTL, reference it by name, delete when done.
cache = client.caches.create(model=MODEL, config=types.CreateCachedContentConfig(
    system_instruction=BIG_POLICY_MANUAL, ttl="600s"))
r = client.models.generate_content(model=MODEL, contents="What's the return window?",
                                   config=types.GenerateContentConfig(cached_content=cache.name))
client.caches.delete(name=cache.name)
```

**Silent cache killers (very common in real codebases):**
- `datetime.now()` or a request id in the system prompt → put volatile data **at the end**.
- Tools in random order or `json.dumps` without `sort_keys` → make them deterministic.
- Swapping tool sets per request → keep one stable tool list.
- Prefixes shorter than the model's minimum cacheable size → silently not cached.

| ✅ Do | ❌ Don't |
|---|---|
| Stable system + tools first, conversation after | Timestamps at the top |
| Append-only history | Rewriting old messages every turn |
| Check `cached_content_token_count > 0` in logs | Assume caching works |

📖 Deep dive: 📘⭐ [Gemini — Optimization: implicit & explicit caching](https://ai.google.dev/gemini-api/docs/optimization) · 📘 [Gemini pricing (cached-token prices)](https://ai.google.dev/gemini-api/docs/pricing)

### 🧪 Lab → do it in the practice notebook 5 — Measure it (30 min)
1. Run a 5-turn conversation with a long, stable system instruction and watch `cached_content_token_count` per turn (implicit caching). Then try an explicit cache.
2. Add `datetime.now()` to the start of the system instruction and watch `cached_content_token_count` drop to 0.
3. Put a key fact in the middle of a 50k-token filler document vs at the end, and ask about it 5 times each. Do you see any difference?

### 🏗 Capstone — Day 5
Restructure the ShopEase prompt (stable sections, volatile data last), enable caching, add tool-output truncation and old-result trimming, and log cache hit rate per conversation. Target: >70% of input tokens served from cache in a 10-turn chat.

### ✅ Checkpoint
1. Why does adding the current time to the system prompt cost money?
2. Calculate the cache saving for a 20-call session with r = 0.1.
3. When would you choose compaction instead of context editing?
4. What's "just-in-time" context, and how do coding agents (Gemini CLI, Claude Code) use it for codebases?

---

**Next:** open the [practice notebook](../practice/day-05-context-and-caching.ipynb) · capstone milestone in [projects/shopease-support-agent](../../projects/shopease-support-agent/README.md#milestones-build-your-own-version-alongside-the-course)

[← Day 4](../../week-1/theory/day-04-workflow-patterns.md) · [Week 1 overview](../README.md) · [▶️ Practice notebook](../practice/day-05-context-and-caching.ipynb) · [Day 6 →](../../week-1/theory/day-06-rag-for-agents.md)
