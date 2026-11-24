"""
STAGE 1 - One function call, done by hand. No loop yet. (Gemini, google-genai SDK)

Goal: see with your own eyes that
  1. the model does NOT run tools - it only *asks* for one (a structured function call),
  2. YOUR code runs the tool,
  3. you send the result back, and the model writes the final answer.

Run:  GEMINI_API_KEY=... python 01_tool_call.py
"""

import json
import os

from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL = os.getenv("COURSE_MODEL", "gemini-flash-latest")


# ---------------------------------------------------------------------------
# 1. A normal Python function. This is the "real" tool.
#    (Fake data so you don't need a weather API key.)
# ---------------------------------------------------------------------------
def get_weather(city: str) -> str:
    fake_db = {"pune": "31°C, sunny", "london": "12°C, rainy", "tokyo": "18°C, cloudy"}
    return fake_db.get(city.lower(), f"No weather data for {city}")


# ---------------------------------------------------------------------------
# 2. The function *declaration* - this is all the model ever sees about the tool:
#    a name, a description (write it like docs for a new teammate), and a JSON Schema.
# ---------------------------------------------------------------------------
GET_WEATHER = types.FunctionDeclaration(
    name="get_weather",
    description="Get the current weather for a city. Returns temperature and conditions.",
    parameters_json_schema={
        "type": "object",
        "properties": {"city": {"type": "string", "description": "City name, e.g. 'Pune'"}},
        "required": ["city"],
    },
)
# Disable automatic function calling so WE run the tool (that's the whole point of this script).
CONFIG = types.GenerateContentConfig(tools=[types.Tool(function_declarations=[GET_WEATHER])])

question = "Should I carry an umbrella in London today?"
contents = [types.Content(role="user", parts=[types.Part.from_text(text=question)])]

# ---------------------------------------------------------------------------
# 3. First call: give the model the question + the tool list.
# ---------------------------------------------------------------------------
response = client.models.generate_content(model=MODEL, contents=contents, config=CONFIG)

print("=== Model's first reply ===")
for part in response.candidates[0].content.parts:
    if part.function_call:
        print("FUNCTION CALL:", part.function_call.name, json.dumps(dict(part.function_call.args)),
              "(id:", part.function_call.id, ")")
    elif part.text and not part.thought:
        print("TEXT         :", part.text)

# ---------------------------------------------------------------------------
# 4. WE run the tool the model asked for.
# ---------------------------------------------------------------------------
call = response.function_calls[0]
result = get_weather(**call.args)
print("\n=== We ran the tool ===\nresult:", result)

# ---------------------------------------------------------------------------
# 5. Send everything back:
#    - the model's turn exactly as received (it may carry thought signatures that must be returned)
#    - a "user" turn with a function_response matching the call's name (and id)
# ---------------------------------------------------------------------------
contents.append(response.candidates[0].content)
contents.append(types.Content(role="user", parts=[types.Part(function_response=types.FunctionResponse(
    id=call.id, name=call.name, response={"output": result}))]))

final = client.models.generate_content(model=MODEL, contents=contents, config=CONFIG)

print("\n=== Model's final answer ===")
print("finish_reason:", final.candidates[0].finish_reason)  # STOP -> "I'm done"
print(final.text)

# EXERCISE: ask "Compare the weather in Pune and Tokyo".
# The model may request TWO function calls in one reply. This script only handles
# the first one - notice what breaks. That pain is why Stage 2 adds a loop.
