# Local Models with agentstatelib

## How the library connects to models

**agentstatelib never calls a model.** The library only manages state: it applies patches, validates structure, and emits trace events. Every model call lives entirely in your own code.

The connection point is `LLMAgent` in `agentstatelib.contrib.base_agent`. You subclass it, implement one method (`_call_model`), and the base class handles JSON parsing, `StatePatch` validation, and the retry-with-correction loop. Because the model is called through one method you control, the provider can be anything: a local Ollama server, an ngrok-tunnelled remote machine, a cloud API, or a pure Python function that never touches a network.

The minimal shape looks like this:

```python
from agentstatelib.contrib.base_agent import LLMAgent

class MyAgent(LLMAgent):
    async def _call_model(self, prompt: str) -> str:
        # call any model here, return the raw string response
        ...
```

Everything else — retry logic, structured-output correction, event tracing — is inherited from the base class. This means swapping providers requires changing only `_call_model`, not the surrounding coordination layer.

---

## Option 1 — Ollama (local install)

Ollama is the easiest path for users who want a model running directly on their machine.

### Install and pull a model

**Linux / macOS:**

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3:8b
```

**Windows:**

Download and run the installer from [ollama.com](https://ollama.com). Then open a terminal:

```bash
ollama pull llama3:8b
```

Ollama starts a background server automatically on install. If it is not running, start it manually:

```bash
ollama serve
```

Verify it is alive:

```bash
!curl http://localhost:11434/api/tags
```

You should see a JSON response listing your installed models. If you see a connection error, Ollama is not running — start it with `ollama serve`.

### Use OllamaAgent

The example is in [`examples/models/ollama_agent.py`](../../examples/models/ollama_agent.py). The default `base_url` is `http://localhost:11434`, which is exactly where Ollama listens. **If you are running Ollama locally, you do not need to set any environment variable.** The agent just works:

```python
from examples.models.ollama_agent import OllamaAgent

agent = OllamaAgent(
    agent_id="researcher",
    system_prompt="You are a precise assistant that returns structured state patches.",
    model="llama3:8b",
    # base_url defaults to http://localhost:11434 — no change needed for local
)
```

To use a different model, change the `model` argument to whatever you pulled:

```bash
ollama pull mistral:7b
```

```python
agent = OllamaAgent(agent_id="researcher", system_prompt="...", model="mistral:7b")
```

List what you have installed:

```bash
ollama list
```

### Environment variables (optional)

If you prefer to keep config in a `.env` file rather than hardcoding it:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3:8b
```

The example file reads both of these automatically with `python-dotenv`. Without them, the defaults are used.

---

## Option 2 — Remote Ollama (ngrok, Docker, VM)

The `OllamaAgent` pattern is designed so that `base_url` is the only thing that changes between local and remote. The same code works for all of these scenarios.

### ngrok tunnel

If Ollama is running on a remote machine (or another laptop) exposed through ngrok, set `OLLAMA_BASE_URL` to the tunnel URL:

```env
OLLAMA_BASE_URL=https://your-tunnel-id.ngrok.io
```

```python
agent = OllamaAgent(
    agent_id="researcher",
    system_prompt="...",
    model="llama3:8b",
    base_url="https://your-tunnel-id.ngrok.io",
)
```

No other change is needed. The library does not know or care whether the server is local or remote.

### Docker

```bash
docker run -d --name ollama -p 11434:11434 ollama/ollama
docker exec -it ollama ollama pull llama3:8b
```

The server is then available at `http://localhost:11434` — the default — so no `base_url` change is needed.

### Remote VM or server

```python
agent = OllamaAgent(
    agent_id="researcher",
    system_prompt="...",
    model="llama3:8b",
    base_url="http://192.168.1.50:11434",  # your server's IP
)
```

---

## Option 3 — LM Studio, vLLM, Llamafile, LocalAI (OpenAI-compatible)

These tools run local models but expose an **OpenAI-compatible API**. That means you use the `OpenAIAgent` from [`examples/models/openai_agent.py`](../../examples/models/openai_agent.py) — not the Ollama one — and just point `base_url` at the local port.

| Tool | Default local URL | Notes |
|---|---|---|
| LM Studio | `http://localhost:1234/v1` | Enable "Local Server" in the app first |
| vLLM | `http://localhost:8000/v1` | GPU-focused, runs on Linux/cloud |
| Llamafile | `http://localhost:8080/v1` | Single-file executable, no install needed |
| LocalAI | `http://localhost:8080/v1` | Docker-based, many backends |

### LM Studio example

1. Download LM Studio from [lmstudio.ai](https://lmstudio.ai)
2. Download a model inside the app
3. Go to **Local Server** tab and click **Start Server**
4. Note the model identifier shown in the UI (e.g., `lmstudio-community/Meta-Llama-3-8B-Instruct-GGUF`)

```python
from examples.models.openai_agent import OpenAIAgent

agent = OpenAIAgent(
    agent_id="researcher",
    system_prompt="You are a precise assistant that returns structured state patches.",
    model="lmstudio-community/Meta-Llama-3-8B-Instruct-GGUF",
    api_key="not-needed",   # LM Studio ignores this but the field is required
    base_url="http://localhost:1234/v1",
)
```

### vLLM example

```bash
pip install vllm
python -m vllm.entrypoints.openai.api_server --model meta-llama/Meta-Llama-3-8B-Instruct
```

```python
agent = OpenAIAgent(
    agent_id="researcher",
    system_prompt="...",
    model="meta-llama/Meta-Llama-3-8B-Instruct",
    api_key="not-needed",
    base_url="http://localhost:8000/v1",
)
```

### Llamafile example

```bash
# download a .llamafile from HuggingFace, then:
chmod +x mistral-7b-instruct.llamafile
./mistral-7b-instruct.llamafile --server
```

```python
agent = OpenAIAgent(
    agent_id="researcher",
    system_prompt="...",
    model="mistral-7b-instruct",
    api_key="not-needed",
    base_url="http://localhost:8080/v1",
)
```

---

## Option 4 — Cloud APIs (no local setup)

If you do not want to run anything locally, these cloud providers work out of the box.

### OpenAI

See [`examples/models/openai_agent.py`](../../examples/models/openai_agent.py).

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

```python
from examples.models.openai_agent import OpenAIAgent

agent = OpenAIAgent(
    agent_id="planner",
    system_prompt="...",
    model="gpt-4o-mini",
)
```

### Anthropic

See [`examples/models/anthropic_agent.py`](../../examples/models/anthropic_agent.py). Anthropic uses a different API shape (Messages API) so it has its own subclass. The usage is the same:

```env
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-haiku-4-5-20251001
```

```python
from examples.models.anthropic_agent import AnthropicAgent

agent = AnthropicAgent(
    agent_id="planner",
    system_prompt="...",
    model="claude-haiku-4-5-20251001",
)
```

### Groq (free tier, very fast)

Groq runs open models like Llama3 and Mistral in the cloud with extremely low latency. It has a free tier and uses the OpenAI-compatible API shape. See [`examples/models/groq_agent.py`](../../examples/models/groq_agent.py).

```env
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama3-8b-8192
```

```python
from examples.models.groq_agent import GroqAgent

agent = GroqAgent(
    agent_id="researcher",
    system_prompt="...",
    model="llama3-8b-8192",
)
```

Groq is a good option if you want to use open models without running them locally.

### Other OpenAI-compatible cloud services

Together AI, Fireworks AI, Azure OpenAI, and most other providers expose an OpenAI-compatible endpoint. Use `OpenAIAgent` with the appropriate `base_url` and `api_key`:

```python
agent = OpenAIAgent(
    agent_id="researcher",
    system_prompt="...",
    model="mistralai/Mistral-7B-Instruct-v0.2",
    api_key=os.environ["TOGETHER_API_KEY"],
    base_url="https://api.together.xyz/v1",
)
```

---

## Option 5 — No model at all (rule-based)

Any async function that accepts a `dict` and returns a `StatePatch` is a valid agent. You do not need a model. See [`examples/models/rule_based_agent.py`](../../examples/models/rule_based_agent.py) for a complete example with a keyword classifier, a router, and a completion checker — all deterministic, instant, and free.

```python
from agentstatelib import StatePatch

async def classify(context: dict) -> StatePatch:
    message = context.get("facts", {}).get("customer_message", "").lower()
    priority = "high" if "urgent" in message else "normal"
    return StatePatch(
        agent_id="classifier",
        target="tasks.classification",
        value={"priority": priority},
        reason="Classified by keyword match.",
    )
```

Rule-based agents compose with LLM agents in the same graph. A common pattern is to use a rule-based router to decide which LLM agent runs next.

---

## Grammar-constrained output

When using Ollama, you can pass a JSON schema in the `format` field to constrain sampling to outputs that match the schema. This reduces the number of malformed responses before they reach the retry loop.

The `OllamaAgent` does this automatically when `use_grammar=True` (the default):

```python
agent = OllamaAgent(
    agent_id="researcher",
    system_prompt="...",
    model="llama3:8b",
    use_grammar=True,   # default — constrains output to the StatePatch schema
)
```

To disable it:

```python
agent = OllamaAgent(..., use_grammar=False)
```

Grammar constraints are not available in all providers. OpenAI and Groq have a `response_format: {"type": "json_object"}` mode that serves a similar purpose and is enabled by default in the example agents.

---

## Retry-with-correction loop

Grammar constraints reduce failures but do not eliminate them. A model can still produce output that passes syntax but fails `StatePatch` validation. That is why `LLMAgent` includes a retry-with-correction loop.

If the model's response fails to parse as JSON or fails schema validation, the next prompt automatically includes the error message and asks for corrected JSON only. The default is 3 attempts. You can change this:

```python
agent = OllamaAgent(..., max_retries=5)
```

The retry loop is the main reason the library is useful for local models specifically: smaller or quantized models are more likely to produce malformed output, and the correction loop recovers from those failures transparently.

---

## Choosing a model

The best model is usually the smallest one that is reliable enough for your task. Structured-output tasks (returning a `StatePatch`) are less demanding than open-ended generation, so smaller models often work fine.

| Model | VRAM required | Notes |
|---|---:|---|
| Mistral 7B | ~5 GB | Fast structured output, lightweight reasoning |
| Llama3 8B | ~6 GB | Strong general-purpose choice |
| Phi-3 Mini 3.8B | ~3 GB | Surprisingly capable for its size |
| Gemma 2 2B | ~2 GB | Very fast, best for routing and classification |
| Llama3 70B | ~40 GB | Higher quality, much slower — needs a good GPU |

If you are unsure, start with `llama3:8b` with `use_grammar=True`. Run the benchmark in the examples directory to measure success rate and latency on your hardware before building a multi-agent workflow on top of it.

---

## Mixed-model workflows

You do not need to use one model for everything. A practical workflow might use a cloud model as a planner, a local model as a researcher, and a rule-based function for cheap deterministic routing. Because every agent returns the same `StatePatch` type, the coordination layer does not care what is behind each agent.

```python
from examples.models.openai_agent import OpenAIAgent
from examples.models.ollama_agent import OllamaAgent
from examples.models.rule_based_agent import classify

planner  = OpenAIAgent(agent_id="planner",     system_prompt="...", model="gpt-4o")
research = OllamaAgent(agent_id="researcher",  system_prompt="...", model="llama3:8b")

graph.node("planner",    planner)
graph.node("researcher", research)
graph.node("classifier", classify)   # plain async function, no class needed
```

High-value reasoning goes to the strongest model; repetitive or cheap steps stay local. The state layer stays the same regardless of the model mix.

---

## Quick-reference: which example to use

| Your setup | Example file |
|---|---|
| Ollama local | [`examples/models/ollama_agent.py`](../../examples/models/ollama_agent.py) |
| Ollama via ngrok / Docker / remote | [`examples/models/ollama_agent.py`](../../examples/models/ollama_agent.py) — change `base_url` |
| LM Studio / vLLM / Llamafile / LocalAI | [`examples/models/openai_agent.py`](../../examples/models/openai_agent.py) — change `base_url` |
| OpenAI | [`examples/models/openai_agent.py`](../../examples/models/openai_agent.py) |
| Anthropic | [`examples/models/anthropic_agent.py`](../../examples/models/anthropic_agent.py) |
| Groq | [`examples/models/groq_agent.py`](../../examples/models/groq_agent.py) |
| Together AI / Fireworks / Azure | [`examples/models/openai_agent.py`](../../examples/models/openai_agent.py) — change `base_url` + `api_key` |
| No model (deterministic) | [`examples/models/rule_based_agent.py`](../../examples/models/rule_based_agent.py) |
