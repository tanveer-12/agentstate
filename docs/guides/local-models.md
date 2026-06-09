# Local Models with agentstatelib

## Why local models

Local models give you privacy, lower marginal cost, and more control over runtime behavior. Your prompts and outputs stay on infrastructure you own or trust, and you can change hardware, quantization, and serving settings without waiting on a vendor. For some workflows, that tradeoff is worth more than raw model quality.

Local models also make experimentation cheaper. You can run repeated benchmarks, try prompt variants, and test structured-output reliability without paying per request. That matters when you are iterating on agent coordination logic rather than just single-turn chat.

## Setting up Ollama

The easiest place to start is [ollama.com](https://ollama.com). On Linux and macOS, Ollama provides a simple install script, and the basic workflow is: install, pull a model, run it, then call the HTTP API. Common commands are `ollama pull <model>`, `ollama run <model>`, `ollama serve`, and `ollama list`.

A typical first setup looks like this:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3:8b
ollama run llama3:8b
```

The Ollama API is served from `http://localhost:11434` by default, and the `/api/tags` endpoint lists installed models. That makes it easy to verify whether the server is alive before you wire it into your agents.

## Grammar-constrained output

Ollama supports structured outputs through the `format` parameter. Instead of asking the model to “please return JSON,” you can provide a JSON schema and let Ollama constrain the output format. This is especially useful for agents that must return a `StatePatch` every time.

For the benchmark in this project, a simplified patch schema worked better than a richer object model. Your benchmark numbers go here:
- With grammar: 100% success, 0.00 retries, 1.86 s for `llama3:8b`; 100% success, 0.00 retries, 1.44 s for `mistral:7b`.
- Without grammar: 100% success, 0.00 retries, 2.01 s for `llama3:8b`; 100% success, 0.00 retries, 1.86 s for `mistral:7b`.

Ollama’s structured outputs are documented as a JSON-schema-based feature, and the recommended practice is to pass the schema in the prompt too so the model stays grounded.

## Retry loop

Grammar constraints help, but they do not eliminate every failure. A model can still return malformed content, partial content, or an output that passes syntax but fails your state validation. That is why `agentstatelib` still uses a retry-with-correction loop.

The retry loop matters because it converts a hard failure into a recoverable one. If the first response is wrong, the next prompt can include the error and ask for corrected JSON only. In practice, that gives you a much more stable local-model workflow.

## Choosing a model

Different local models trade off speed, quality, and hardware requirements. For agent workflows, the best model is often the one that is “good enough” while still fitting comfortably on your hardware. Smaller models are usually better for routing, classification, and extraction; larger models are better for planning and synthesis.

| Model | Typical VRAM requirement | Observed reliability |
|---|---:|---|
| Mistral 7B | 5 GB+ | Good for fast local structured output and lightweight reasoning. |
| Llama3 8B | 6 GB+ | Strong general-purpose choice; good balance of quality and speed. |
| Llama3 70B | 40 GB+ | Higher quality, but much heavier and slower. |
| Smaller 3B-class models | 2–4 GB | Fast, but more likely to need retries and correction. |

For your own benchmark, replace the reliability notes with measured numbers from your run. The main thing to watch is not just success rate, but success rate under structured-output pressure.

## Remote Ollama

The nice thing about the `OllamaAgent` pattern is that `base_url` is the only thing that changes. The same code can point at `http://localhost:11434`, a Docker container, a remote VM, or an ngrok-exposed endpoint. That makes local and remote usage identical from the agent’s point of view.

A simple Docker one-liner looks like this:

```bash
docker run -d --name ollama -p 11434:11434 ollama/ollama
```

Any server IP or hostname works as long as the API is reachable at `/api/tags` and `/api/generate`. That is the main design advantage of keeping the transport details outside the agent logic.