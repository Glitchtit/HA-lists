"""HA-lists — AI subsystem.

Thin wrapper around the Goblin Tools features:
- `storage_client` — fetch AI provider config from HA-storage
- `provider` — unified Gemini / Claude / Ollama caller returning JSON
- `prompts` — spiciness-aware prompt builders
- `jobs` — single-flight in-memory job registry for long-running operations
"""
