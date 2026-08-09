"""Entity-based attribution checking using spaCy.

Checks that factual claims in targets trace back to the visible input,
verified state, or authorized tool results — never to hidden generator context.

ADR §7.3.1(4): every factual claim in targets must be supported by visible
input, verified state, or authorized tool result. Substring-only heuristics
are insufficient; entity extraction is required.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Entity types treated as fact-bearing for attribution purposes.
# These cover persons, organizations, locations, dates, quantities,
# products, and numbers — the kinds of things a generator might fabricate.
_ENTITY_TYPES = frozenset({
    "PERSON", "ORG", "GPE", "LOC", "DATE", "TIME", "MONEY",
    "QUANTITY", "CARDINAL", "ORDINAL", "PRODUCT", "EVENT",
})

_MODEL_NAME = "en_core_web_sm"
_model: Any = None


def _get_nlp():
    global _model
    if _model is None:
        import spacy as _spacy
        try:
            _model = _spacy.load(_MODEL_NAME, enable=["ner"])
        except OSError as exc:
            logger.warning(
                "spaCy model %s not found — attribution degrades to substring check", _MODEL_NAME
            )
            _model = object()  # sentinel
    return _model


def _extract_entities(text: str) -> dict[str, set[str]]:
    """Extract named entities from text grouped by type.

    Returns dict mapping entity_type → set of normalized surface forms.
    Falls back to empty dict if NLP unavailable.
    """
    nlp = _get_nlp()
    if isinstance(nlp, object):
        return {}  # degraded mode
    doc = nlp(text)[:5000]  # practical length cap
    result: dict[str, set[str]] = {}
    for ent in doc.ents:
        if ent.label_ in _ENTITY_TYPES:
            result.setdefault(ent.label_, set()).add(ent.text.lower())
    return result


def check_attribution(row: Any) -> tuple[bool, str]:
    """Check a single row's target against its visible input.

    Returns (passed, reason) where reason is descriptive on failure.
    """
    visible_text = row._text_of_messages() if hasattr(row, "_text_of_messages") else str(row.visible_input)
    target_text = row.target if hasattr(row, "target") else getattr(row, "target", "")

    if not target_text.strip():
        return True, "no_target"

    # Approach A: entity-level grounding
    vis_entities = _extract_entities(visible_text)
    tgt_entities = _extract_entities(target_text)

    if vis_entities and tgt_entities:
        ungrounded = []
        for etype, evalues in tgt_entities.items():
            vis_of_same = vis_entities.get(etype)
            for ev in evalues:
                if vis_of_same:
                    # Check surface-form overlap or substring containment
                    covered = any(ev in vv or vv in ev for vv in vis_of_same)
                    if not covered:
                        # Also check lowercase token intersection
                        ev_tokens = set(ev.split())
                        vis_tokens_flat = set(vv.split() for vv in vis_of_same)
                        if not ev_tokens & vis_tokens_flat:
                            ungrounded.append(f"{etype}:{ev}")
                else:
                    # No entities of this type in visible input at all
                    ungrounded.append(f"{etype}:{ev}")

        if ungrounded:
            return False, f"ungrounded_entities:{','.join(ungrounded)}"

    # Approach B: fallback to stop-word-filtered token overlap when no entities found
    # (short text, non-English, etc.)
    from .checks import _STOP_WORDS

    def _content_tokens(text: str) -> set[str]:
        words = [w.lower().strip(".,!?\'\"()[]{}:;") for w in text.split()]
        return {w for w in words if len(w) >= 2 and w not in _STOP_WORDS}

    vis_tokens = _content_tokens(visible_text)
    tgt_tokens = _content_tokens(target_text)

    if tgt_tokens:
        grounded = tgt_tokens & vis_tokens
        if not grounded:
            return False, f"no_token_overlap:visible_tokens={sorted(vis_tokens)[:5]}"

    return True, "ok"
