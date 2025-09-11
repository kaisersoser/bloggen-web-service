"""Shared utility for generating concise blog topics/titles.

Provides a fast heuristic fallback plus (optional) OpenAI refinement.
The goal is to consistently produce a neutral, noun‑phrase style topic
of roughly 5–12 words summarizing the user's instructions without
imperative verbs ("Generate", "Write", etc.) and without surrounding quotes.
"""
from __future__ import annotations

from typing import Optional, Iterable
import os
import re
import logging

from core.model_config import get_default_model

logger = logging.getLogger(__name__)

FALLBACK_TOPIC = "AI Blog Topic"

_STOPWORDS = {
    "a","an","the","and","or","but","for","nor","so","of","on","in","to","with","by","about","into","over","after","before","from","at","as","is","are","be"
}

_LEADING_VERBS = {
    "generate","write","create","produce","explain","describe","outline","draft","develop","craft","compose","make","build","show","compare","analyze","explore","discuss"
}

def _clean_text(text: str) -> str:
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text

def _remove_leading_verbs(words: Iterable[str]) -> list[str]:
    w = list(words)
    while w and w[0].lower() in _LEADING_VERBS:
        w.pop(0)
    return w

def _heuristic_topic(instructions: str, max_words: int = 12) -> str:
    if not instructions:
        return FALLBACK_TOPIC
    text = _clean_text(instructions.lower())
    # Remove boilerplate phrases
    text = re.sub(r"\b(?:please|kindly)\b", "", text)
    text = re.sub(r"\b(?:an?|the) (?:article|blog|post) (?:about|on)\b", "", text)
    # Tokenize
    raw_words = re.findall(r"[a-zA-Z0-9][a-zA-Z0-9\-]*", text)
    if not raw_words:
        return FALLBACK_TOPIC
    raw_words = _remove_leading_verbs(raw_words)
    # Remove trailing directive words like 'including', 'detailing'
    while raw_words and raw_words[-1] in {"including","detailing","covering"}:
        raw_words.pop()
    # Keep order but drop stopwords if we exceed size and keep informative words first
    informative = [w for w in raw_words if w not in _STOPWORDS]
    chosen = informative if 4 <= len(informative) <= max_words else raw_words
    if len(chosen) > max_words:
        chosen = chosen[:max_words]
    # Capitalization (title style, keep some lowercase small words)
    lowercase_words = {"a","an","and","as","at","but","by","for","if","in","nor","of","on","or","so","the","to","up","yet"}
    words_title: list[str] = []
    for i, w in enumerate(chosen):
        if i > 0 and w in lowercase_words:
            words_title.append(w.lower())
        else:
            words_title.append(w.capitalize())
    topic = " ".join(words_title)
    # Basic length guard
    return topic or FALLBACK_TOPIC

def _openai_refine(base_topic: str, instructions: str, *, api_key: str, model: Optional[str]) -> str:
    try:  # Lazy import to avoid hard dependency
        import openai  # type: ignore
    except ImportError:  # pragma: no cover
        return base_topic
    try:
        client = openai.OpenAI(api_key=api_key)  # type: ignore[attr-defined]
        prompt_user = (
            "Instructions:\n" + instructions.strip()[:4000] +
            "\n\nExisting draft topic: " + base_topic +
            "\n\nRefine to a concise neutral blog topic (5-12 words, noun phrase, no imperative verbs, no quotes). Return ONLY the topic." )
        resp = client.chat.completions.create(
            model=model or get_default_model(),
            messages=[
                {"role": "system", "content": "You produce only refined concise blog topics."},
                {"role": "user", "content": prompt_user},
            ],
            max_tokens=24,
            temperature=0.3,
        )
        refined = resp.choices[0].message.content if resp.choices else None
        if not refined:
            return base_topic
        refined = refined.strip().strip('"').strip("'")
        # Remove leading verbs if model produced them
        words = refined.split()
        words = _remove_leading_verbs(words)
        if not (3 <= len(words) <= 14):  # sanity bounds
            return base_topic
        return " ".join(words)
    except Exception as e:  # pragma: no cover
        logger.warning("OpenAI refinement failed: %s", e)
        return base_topic

def generate_concise_topic(
    instructions: str,
    *,
    openai_api_key: Optional[str] = None,
    model: Optional[str] = None,
    enable_refine: bool = True,
) -> str:
    """Generate a concise topic.

    Steps:
    1. Heuristic extraction (fast, offline)
    2. Optional OpenAI refinement if key & library available
    """
    instructions = instructions or ""
    base = _heuristic_topic(instructions)
    if not enable_refine:
        return base
    api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return base
    return _openai_refine(base, instructions, api_key=api_key, model=model)

__all__ = ["generate_concise_topic", "FALLBACK_TOPIC"]
