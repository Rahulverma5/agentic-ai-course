"""
STAGE 1 - One tool call, done by hand. No loop yet.

Goal: see with your own eyes that
  1. the model does NOT run tools - it only *asks* for one (as JSON),
  2. YOUR code runs the tool,
  3. you send the result back, and the model writes the final answer.

Run:  python 01_tool_call.py
"""

import json

import anthropic

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
MODEL = "claude-opus-5-5"


# ---------------------------------------------------------------------------
# 1. A normal Python function. This is the "real" tool.
#    (Fake data so you don't need a weather API key.)
# ---------------------------------------------------------------------------
def get_weather(city: str) -> str:
    fake_db = {"pune": "31°C, sunny", "london": "12°C, rainy", "tokyo": "18°C, cloudy"}
    return fake_db.get(city.lower(), f"No weather data for {city}")


# ---------------------------------------------------------------------------
# 2. The tool *definition* - this is all the model ever sees about the tool:
#    a name, a description (write it like docs for a new teammate), and a
#    JSON Schema for the input.
# ---------------------------------------------------------------------------
TOOLS = [
    {
        "name": "get_weather",
        "description": "Get the current weather for a city. Returns temperature and conditions.",
        "input_schema": {
            "type": "object",
            "properties": {"city": {"type": "string", "description": "City name, e.g. 'Pune'"}},
            "required": ["city"],
        },
    }
]

question = "Should I carry an umbrella in London today?"
messages = [{"role": "user", "content": question}]

# ---------------------------------------------------------------------------
# 3. First call: give the model the question + the tool list.
# ---------------------------------------------------------------------------
response = client.messages.create(model=MODEL, max_tokens=4000, tools=TOOLS, messages=messages)

print("=== Model's first reply ===")
print("stop_reason:", response.stop_reason)  # expect "tool_use" -> "I want to call a tool"
for block in response.content:
    if block.type == "text":
        print("TEXT     :", block.text)
    elif block.type == "tool_use":
        print("TOOL CALL:", block.name, json.dumps(block.input), "(id:", block.id, ")")
    else:
        print("OTHER    :", block.type)  # e.g. a "thinking" block

# ---------------------------------------------------------------------------
# 4. WE run the tool the model asked for.
# ---------------------------------------------------------------------------
tool_call = next(b for b in response.content if b.type == "tool_use")
result = get_weather(**tool_call.input)
print("\n=== We ran the tool ===\nresult:", result)

# ---------------------------------------------------------------------------
# 5. Send everything back:
#    - the assistant's reply exactly as received (including the tool_use block)
#    - a "user" message containing a tool_result that points to the tool_use id
# ---------------------------------------------------------------------------
messages.append({"role": "assistant", "content": response.content})
messages.append(
    {
        "role": "user",
        "content": [{"type": "tool_result", "tool_use_id": tool_call.id, "content": result}],
    }
)

final = client.messages.create(model=MODEL, max_tokens=4000, tools=TOOLS, messages=messages)

print("\n=== Model's final answer ===")
print("stop_reason:", final.stop_reason)  # expect "end_turn" -> "I'm done"
for block in final.content:
    if block.type == "text":
        print(block.text)

# EXERCISE: ask "Compare the weather in Pune and Tokyo".
# The model may request TWO tool calls in one reply. This script only handles
# the first one - notice what breaks. That pain is why Stage 2 adds a loop.
