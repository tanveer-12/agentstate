# Connecting LLMs to agentstatelib

agentstatelib never calls a model. Your agent functions do.

## The minimal pattern

The smallest possible integration is simple: take a context dict, build a prompt, call your model, parse the result, and return a `StatePatch`. That pattern works with any provider, whether it is OpenAI-compatible, Anthropic, Ollama, or a local rule-based function. In practice, the model call is just one step inside a larger agent function.

A minimal shape looks like this:

```python
async def agent(context: dict) -> StatePatch:
    prompt = build_prompt(context)
    raw = await call_model(prompt)
    data = json.loads(raw)
    return StatePatch(agent_id="planner", **data)
```

## The retry-with-correction pattern

LLMs do not always return valid JSON on the first try. That is why `agentstatelib.contrib.base_agent.LLMAgent` exists: it wraps the common pattern of prompt construction, JSON parsing, validation, and retry-with-correction. If the model returns malformed output, the next prompt includes the error message and asks for corrected JSON only.

The subclass pattern is intentionally small. You implement one method, `_call_model`, and inherit the retry loop from the base class. This keeps provider-specific code at the edge and makes the failure behavior consistent across all models.

## Provider examples

For OpenAI and other OpenAI-compatible endpoints, see [`examples/models/openai_agent.py`]. For Anthropic, see [`examples/models/anthropic_agent.py`]. For Ollama, see [`examples/models/ollama_agent.py`]. For Groq, see [`examples/models/groq_agent.py`]. For deterministic workflows, see [`examples/models/rule_based_agent.py`].

Each example shows the same idea from a different angle: the agent receives a context dict and returns a `StatePatch`. The only real difference is how `_call_model` talks to the provider. That makes it easy to swap vendors without changing the surrounding coordination layer.

## Structured output reliability

Structured output reliability is one of the main reasons to use `agentstatelib`. Local models can be unreliable about JSON formatting, especially when prompts get more complex. The Ollama example demonstrates grammar-constrained output by passing a small JSON schema to `format`, which narrows sampling to outputs matching the schema.

For the current benchmark, the simplified grammar path was reliable:
- `llama3:8b`: 1.00 success with grammar, 1.00 without.
- `mistral:7b`: 1.00 success with grammar, 1.00 without.
- Grammar was slightly faster in both cases.

Ollama’s structured outputs are especially useful for local models because they reduce parsing failures before they reach your state layer. The retry loop still matters, because even constrained models can produce bad output occasionally.

## Mixed-model workflows

You do not need one model for everything. A practical workflow might use GPT-4o as a planner, Llama3-8B as a researcher, and a rule-based classifier for cheap deterministic routing. `agentstatelib` is designed for that kind of mixed environment because every agent still returns the same structured patch type.

That makes it easy to compose workflows by task difficulty and cost. High-value reasoning can go to the strongest model, while repetitive classification can stay local and cheap. The coordination layer stays the same even as the model mix changes.

## Production concerns

In production, add token counting, Redis caching, semaphore-based rate limiting, and cost tracking around your agent calls. Those concerns belong outside the model-specific subclass, so the same agent code can run in development and production. The result is a system where model calls are just one part of a larger, observable pipeline.

The practical rule is simple: keep model integration thin, and keep orchestration, retries, and observability in the coordination layer. That separation is what makes multi-agent workflows easier to debug and easier to recover when something fails.