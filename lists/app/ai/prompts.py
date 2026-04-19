"""HA-lists — Spiciness-aware prompt templates.

All prompts request strict JSON output and embed household-context rules
(multilingual input, Finnish-first product names are NOT relevant here —
lists are generic tasks, not groceries).
"""

from __future__ import annotations

_SPICINESS_RULES = {
    1: (
        "Spiciness 1 (minimal): 2–3 subtasks, each a single clear action. "
        "Assumes high executive function; skip obvious prep steps."
    ),
    2: (
        "Spiciness 2 (light): 3–4 subtasks, slightly more concrete than 1. "
        "Still lean; no micro-steps."
    ),
    3: (
        "Spiciness 3 (default): 4–6 subtasks, average decomposition. "
        "Each should be actionable in under 30 minutes."
    ),
    4: (
        "Spiciness 4 (detailed): 6–9 subtasks. Break decision points into "
        "their own steps. Pre-commit easy wins first to build momentum."
    ),
    5: (
        "Spiciness 5 (maximum): 8–12 very small subtasks including setup, "
        "'stand up and get X', 'find Y', 'open Z'. Assume low executive "
        "function — Goblin Tools 'get out of bed'-level granularity."
    ),
}


def breakdown_prompt(title: str, notes: str | None, spiciness: int) -> str:
    spiciness = max(1, min(5, int(spiciness)))
    rules = _SPICINESS_RULES[spiciness]
    notes_block = f"\nContext/notes: {notes.strip()}" if notes and notes.strip() else ""
    return (
        "You break down personal tasks into concrete subtasks in the Goblin "
        "Tools Magic ToDo style.\n\n"
        f"Task: {title}{notes_block}\n\n"
        f"{rules}\n\n"
        "Keep each subtask short (<10 words), imperative mood, no numbering, "
        "no emojis. Reply with this exact JSON shape and nothing else:\n"
        '{"subtasks": ["step 1", "step 2", ...]}'
    )


def estimate_prompt(title: str, notes: str | None) -> str:
    notes_block = f"\nContext/notes: {notes.strip()}" if notes and notes.strip() else ""
    return (
        "You estimate how long a personal task will take. Give a realistic "
        "range in minutes for a typical adult, not worst or best case.\n\n"
        f"Task: {title}{notes_block}\n\n"
        "Reply with this exact JSON shape and nothing else:\n"
        '{"estimate_min": 10, "estimate_max": 25}\n'
        "Both numbers are integers, estimate_min <= estimate_max."
    )


def compile_prompt(brain_dump: str) -> str:
    return (
        "You convert a messy brain-dump into a clean ordered list of actionable "
        "items. Group related thoughts, drop filler, keep the user's wording "
        "when useful but rewrite for clarity.\n\n"
        f"Brain dump:\n{brain_dump.strip()}\n\n"
        "Reply with this exact JSON shape and nothing else:\n"
        '{"items": [{"title": "…", "notes": "optional longer context"}, ...]}\n'
        "Each title <80 chars. `notes` is optional (omit if not useful)."
    )


_TONES = {
    "formal": "polished, professional, neutral — suitable for written correspondence",
    "casual": "friendly, conversational, warm — like texting a close friend",
    "concise": "short and direct, strip filler, keep meaning intact",
    "kind": "gentle, encouraging, non-judgmental — good for self-notes",
    "firm": "clear, assertive, no-nonsense — good for follow-ups",
}


def formalize_prompt(text: str, tone: str) -> str:
    tone_key = (tone or "formal").lower().strip()
    description = _TONES.get(tone_key, _TONES["formal"])
    return (
        f"Rewrite the following text in a {tone_key} tone: {description}. "
        "Preserve the meaning. Do not add new information. Match the "
        "original language.\n\n"
        f"Original:\n{text.strip()}\n\n"
        "Reply with this exact JSON shape and nothing else:\n"
        '{"text": "…"}'
    )


def available_tones() -> list[str]:
    return list(_TONES.keys())


# ── Notes prompts ─────────────────────────────────────────────────────────────

_LANG_RULE = (
    "Match the language of the input. Do not translate."
)


def note_summarize_prompt(body: str) -> str:
    return (
        "You summarize personal notes. Produce a 3–5 sentence tl;dr that "
        "preserves the key points.\n\n"
        f"{_LANG_RULE}\n\n"
        f"Note body:\n{(body or '').strip()}\n\n"
        "Reply with this exact JSON shape and nothing else:\n"
        '{"summary": "…"}'
    )


def note_continue_prompt(body: str, user_prompt: str) -> str:
    hint = (user_prompt or "").strip()
    hint_block = f"\nUser hint: {hint}" if hint else ""
    return (
        "You continue writing from where a personal note leaves off. Pick up "
        "the thread naturally — do not repeat earlier content or add headings. "
        "Produce roughly 1–3 short paragraphs.\n\n"
        f"{_LANG_RULE}\n\n"
        f"Note body so far:\n{(body or '').strip()}{hint_block}\n\n"
        "Reply with this exact JSON shape and nothing else:\n"
        '{"continuation": "…"}'
    )


def note_rewrite_prompt(body: str, tone: str) -> str:
    tone_key = (tone or "formal").lower().strip()
    description = _TONES.get(tone_key, _TONES["formal"])
    return (
        f"Rewrite the following note in a {tone_key} tone: {description}. "
        "Preserve meaning and structure (headings, bullet points, code blocks). "
        "Do not add new information.\n\n"
        f"{_LANG_RULE}\n\n"
        f"Original note:\n{(body or '').strip()}\n\n"
        "Reply with this exact JSON shape and nothing else:\n"
        '{"body": "…"}'
    )


def note_extract_tasks_prompt(body: str) -> str:
    return (
        "Extract actionable tasks from the following personal note. Ignore "
        "background context, opinions, and purely informational sentences. "
        "Each task should be a concrete next action the author could take.\n\n"
        f"{_LANG_RULE}\n\n"
        f"Note body:\n{(body or '').strip()}\n\n"
        "Reply with this exact JSON shape and nothing else:\n"
        '{"tasks": [{"title": "…", "notes": "optional"}, ...]}\n'
        "`notes` is optional (omit if not useful). Each title <80 chars."
    )


def note_outline_prompt(body: str) -> str:
    return (
        "Produce a tight markdown outline of the following note. Use `##` for "
        "sections and `- ` for bullets. Keep only what structures the content; "
        "do not invent new information.\n\n"
        f"{_LANG_RULE}\n\n"
        f"Note body:\n{(body or '').strip()}\n\n"
        "Reply with this exact JSON shape and nothing else:\n"
        '{"outline": "## Heading\\n- bullet\\n..."}'
    )
