# 📁 File Assistant: warm-up project

The smallest useful agent: it reads, writes and organizes files inside `./workspace`. It works the same way as Claude Code, only smaller. Do this before Day 3 to feel the agent loop in plain Python.

| File | What you learn |
|---|---|
| `01_tool_call.py` | One tool call by hand: the model asks, your code runs it, you send the result back |
| `02_agent_loop.py` | The `while` loop: several tool calls per step, errors as feedback, a step limit, sandboxed paths (`safe_path`) |

```bash
cd projects/file-assistant
python 01_tool_call.py
python 02_agent_loop.py      # try: "Read todo.txt and create plan.md with the tasks sorted by priority"
```

## Exercises
1. In `01_tool_call.py`, ask *"Compare the weather in Pune and Tokyo."* What breaks, and why does that need a loop?
2. Add a `delete_file` tool to `02_agent_loop.py`, then add a confirmation prompt before it runs (human-in-the-loop, Day 12).
3. Set `MAX_STEPS = 2` and give it a big task. Watch the safety limit stop it.
