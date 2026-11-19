"""
STAGE 2 - A real agent: the while-loop.

A tiny "file assistant" that can only touch files inside ./workspace.
It has 3 tools: list_files, read_file, write_file.

Try tasks like:
  - "What files do I have? Summarize each one."
  - "Read todo.txt and create plan.md with the tasks ordered by priority."
  - "Make a file called ideas.txt with 5 project ideas for learning agents."

Run:  python 02_agent_loop.py
"""

import json
from pathlib import Path

import anthropic

client = anthropic.Anthropic()
MODEL = "claude-opus-5-5"
MAX_STEPS = 15  # safety: never loop forever
WORKSPACE = (Path(__file__).parent / "workspace").resolve()
WORKSPACE.mkdir(exist_ok=True)

SYSTEM_PROMPT = f"""You are a helpful file assistant.
You can only see and change files inside the user's workspace folder, using your tools.
Paths are relative to the workspace (e.g. "notes.txt").
Before changing a file, read it first. When you are done, reply with a short summary of what you did."""


# =============================================================================
# TOOLS: plain Python functions
# =============================================================================
def safe_path(relative: str) -> Path:
    """Guardrail: block paths like '../../etc/passwd' that escape the workspace."""
    path = (WORKSPACE / relative).resolve()
    if not path.is_relative_to(WORKSPACE):
        raise ValueError(f"Path '{relative}' is outside the workspace. Use a relative path.")
    return path


def list_files() -> str:
    files = [str(p.relative_to(WORKSPACE)) for p in WORKSPACE.rglob("*") if p.is_file()]
    return "\n".join(sorted(files)) or "(workspace is empty)"


def read_file(path: str) -> str:
    p = safe_path(path)
    if not p.exists():
        # Helpful errors let the model recover on its own.
        return f"Error: '{path}' not found. Call list_files to see what exists."
    text = p.read_text()
    if len(text) > 20_000:  # context hygiene: don't flood the context window
        return text[:20_000] + "\n...[truncated]"
    return text


def write_file(path: str, content: str) -> str:
    p = safe_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return f"Wrote {len(content)} characters to {path}"


# name -> function, so the loop can dispatch any tool call
TOOL_FUNCTIONS = {"list_files": list_files, "read_file": read_file, "write_file": write_file}

# What the model sees
TOOLS = [
    {
        "name": "list_files",
        "description": "List all files in the workspace (relative paths, one per line).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "read_file",
        "description": "Read the full text of a file in the workspace.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Relative path, e.g. 'notes.txt'"}},
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Create or overwrite a file in the workspace with the given content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path, e.g. 'plan.md'"},
                "content": {"type": "string", "description": "The complete new file content"},
            },
            "required": ["path", "content"],
        },
    },
]


def run_tool(name: str, tool_input: dict) -> tuple[str, bool]:
    """Run one tool. Returns (result_text, is_error). Errors go back to the model, not crash us."""
    try:
        return TOOL_FUNCTIONS[name](**tool_input), False
    except Exception as e:
        return f"Error: {e}", True


# =============================================================================
# THE AGENT LOOP  <- the important part. Think -> Act -> Observe -> repeat.
# =============================================================================
def run_agent(messages: list) -> None:
    for step in range(1, MAX_STEPS + 1):
        # ---- THINK: send the whole history, the model decides what to do next
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
            output_config={"effort": "medium"},  # how hard the model thinks: low/medium/high/...
            # If a safety classifier declines, retry on a fallback model automatically.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        # Always save the reply as-is (it may contain thinking + tool_use blocks)
        messages.append({"role": "assistant", "content": response.content})

        for block in response.content:
            if block.type == "text" and block.text.strip():
                print(f"\n🤖 {block.text}")

        # ---- DONE? The model stops asking for tools when it thinks the task is finished.
        if response.stop_reason == "end_turn":
            return
        if response.stop_reason == "refusal":
            print("\n⚠️  The model declined this request.")
            return
        if response.stop_reason == "max_tokens":
            print("\n⚠️  Reply was cut off (max_tokens).")
            return

        # ---- ACT: run every tool the model asked for (there can be several)
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            print(f"   🔧 step {step}: {block.name}({json.dumps(block.input)[:80]})")
            result, is_error = run_tool(block.name, block.input)
            tool_results.append(
                {"type": "tool_result", "tool_use_id": block.id, "content": result, "is_error": is_error}
            )

        # ---- OBSERVE: give ALL results back in ONE user message, then loop again
        messages.append({"role": "user", "content": tool_results})

    print(f"\n⚠️  Stopped after {MAX_STEPS} steps (safety limit).")


def main() -> None:
    print(f"File assistant. Workspace: {WORKSPACE}\nType a task, or 'quit'.")
    messages: list = []  # kept across tasks, so the agent remembers the conversation
    while True:
        task = input("\n👤 > ").strip()
        if task.lower() in {"quit", "exit", "q"}:
            break
        if task:
            messages.append({"role": "user", "content": task})
            run_agent(messages)


if __name__ == "__main__":
    main()
