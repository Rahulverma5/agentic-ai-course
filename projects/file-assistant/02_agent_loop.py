"""
STAGE 2 - A real agent: the while-loop.

A tiny "file assistant" that can only touch files inside ./workspace.
It has 3 tools: list_files, read_file, write_file.

Try tasks like:
  - "What files do I have? Summarize each one."
  - "Read todo.txt and create plan.md with the tasks ordered by priority."
  - "Make a file called ideas.txt with 5 project ideas for learning agents."

Run:  GEMINI_API_KEY=... python 02_agent_loop.py
"""

import json
import os
from pathlib import Path

from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL = os.getenv("COURSE_MODEL", "gemini-flash-latest")
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

# What the model sees (plain JSON Schema; converted to Gemini FunctionDeclarations below)
TOOL_DEFS = [
    {
        "name": "list_files",
        "description": "List all files in the workspace (relative paths, one per line).",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "read_file",
        "description": "Read the full text of a file in the workspace.",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Relative path, e.g. 'notes.txt'"}},
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Create or overwrite a file in the workspace with the given content.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path, e.g. 'plan.md'"},
                "content": {"type": "string", "description": "The complete new file content"},
            },
            "required": ["path", "content"],
        },
    },
]


TOOLS = [types.Tool(function_declarations=[
    types.FunctionDeclaration(name=t["name"], description=t["description"], parameters_json_schema=t["parameters"])
    for t in TOOL_DEFS])]
CONFIG = types.GenerateContentConfig(
    system_instruction=SYSTEM_PROMPT,
    tools=TOOLS,
    thinking_config=types.ThinkingConfig(thinking_level="MEDIUM"),  # how hard the model thinks
)


def run_tool(name: str, tool_input: dict) -> tuple[str, bool]:
    """Run one tool. Returns (result_text, is_error). Errors go back to the model, not crash us."""
    try:
        return TOOL_FUNCTIONS[name](**tool_input), False
    except Exception as e:
        return f"Error: {e}", True


# =============================================================================
# THE AGENT LOOP  <- the important part. Think -> Act -> Observe -> repeat.
# =============================================================================
def run_agent(contents: list) -> None:
    for step in range(1, MAX_STEPS + 1):
        # ---- THINK: send the whole history, the model decides what to do next
        response = client.models.generate_content(model=MODEL, contents=contents, config=CONFIG)
        candidate = response.candidates[0]
        # Always save the model turn as-is (it may contain thought signatures + function calls)
        contents.append(candidate.content)

        for part in candidate.content.parts or []:
            if part.text and not part.thought and part.text.strip():
                print(f"\n🤖 {part.text}")

        # ---- DONE? The model stops asking for tools when it thinks the task is finished.
        if not response.function_calls:
            if candidate.finish_reason.name != "STOP":
                print(f"\n⚠️  Stopped early: {candidate.finish_reason.name}")  # MAX_TOKENS, SAFETY, ...
            return

        # ---- ACT: run every function the model asked for (there can be several)
        parts = []
        for call in response.function_calls:
            print(f"   🔧 step {step}: {call.name}({json.dumps(dict(call.args or {}))[:80]})")
            result, is_error = run_tool(call.name, dict(call.args or {}))
            parts.append(types.Part(function_response=types.FunctionResponse(
                id=call.id, name=call.name, response={"error": result} if is_error else {"output": result})))

        # ---- OBSERVE: give ALL results back in ONE user turn, then loop again
        contents.append(types.Content(role="user", parts=parts))

    print(f"\n⚠️  Stopped after {MAX_STEPS} steps (safety limit).")


def main() -> None:
    print(f"File assistant. Workspace: {WORKSPACE}\nType a task, or 'quit'.")
    contents: list = []  # kept across tasks, so the agent remembers the conversation
    while True:
        task = input("\n👤 > ").strip()
        if task.lower() in {"quit", "exit", "q"}:
            break
        if task:
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text=task)]))
            run_agent(contents)


if __name__ == "__main__":
    main()
