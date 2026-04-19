"""HA-lists — Wikilink extraction for notes.

Supports Obsidian-style links:

- ``[[Title]]`` → (Title, 'wikilink')
- ``[[Title|alias]]`` → (Title, 'wikilink'); the alias is discarded.
- ``![[Title]]`` → (Title, 'embed')

Ignores matches inside fenced code blocks (``` ... ```) and inline backticks.
The returned list is deduplicated while preserving first-seen order.
"""

from __future__ import annotations

import re

_EMBED_RE = re.compile(r"!\[\[([^\[\]\n|]+?)(?:\|[^\[\]\n]*)?\]\]")
_WIKI_RE = re.compile(r"(?<!\!)\[\[([^\[\]\n|]+?)(?:\|[^\[\]\n]*)?\]\]")
_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")


def _strip_inline_code(line: str) -> str:
    """Remove inline backtick spans so we don't match wikilinks inside them."""
    return _INLINE_CODE_RE.sub("", line)


def extract_wikilinks(body: str) -> list[tuple[str, str]]:
    """Return ``[(target_title, link_type), ...]`` from ``body``.

    ``link_type`` is either ``'wikilink'`` or ``'embed'``. Order is preserved
    and duplicates (same target + kind) are dropped.
    """
    if not body:
        return []

    results: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    in_fence = False

    for raw_line in body.splitlines():
        stripped = raw_line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        line = _strip_inline_code(raw_line)

        # Find embeds and wikilinks with positions so we can emit in order.
        matches: list[tuple[int, str, str]] = []
        for m in _EMBED_RE.finditer(line):
            title = m.group(1).strip()
            if title:
                matches.append((m.start(), title, "embed"))
        # Wikilinks — the (?<!\!) lookbehind makes them skip embeds.
        for m in _WIKI_RE.finditer(line):
            title = m.group(1).strip()
            if title:
                matches.append((m.start(), title, "wikilink"))

        matches.sort(key=lambda t: t[0])
        for _, title, kind in matches:
            key = (title, kind)
            if key in seen:
                continue
            seen.add(key)
            results.append(key)

    return results
