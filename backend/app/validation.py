"""
Lightweight guardrails for a *defensive* security assistant.

These are heuristic, not a substitute for a real content-safety pipeline,
but they demonstrate the pattern examiners are looking for:
  1. Input validation (catch obvious prompt-injection / scope-abuse attempts
     before they reach the LLM).
  2. Output validation (catch cases where the model drifted from a
     defensive/explanatory answer into something it shouldn't produce).
  3. Grounding check (did the answer actually rely on retrieved context,
     or is the model unsupported / hallucinating?).

Everything here is intentionally conservative: on ambiguity, log and flag
rather than silently pass or silently block.
"""
import re

# Phrases that suggest someone is trying to override the system prompt or
# extract operational secrets rather than ask a legitimate SOC question.
INJECTION_PATTERNS = [
    r"ignore (all|previous|the) instructions",
    r"disregard (all|previous|the) instructions",
    r"you are now",
    r"system prompt",
    r"reveal your (instructions|prompt|rules)",
    r"act as (an? )?(unrestricted|jailbroken|dan)",
]

# Requests that push the assistant from *explaining* an alert toward
# *producing offensive tooling* — out of scope for a defensive assistant.
OFFENSIVE_INTENT_PATTERNS = [
    r"write (me )?(a |an )?(exploit|malware|ransomware|virus|keylogger)",
    r"how (do|can) i (hack|breach|exploit|bypass) (into )?",
    r"generate.*payload",
    r"step[- ]by[- ]step.*attack",
]


def check_input(message: str) -> tuple[bool, str]:
    """Returns (flagged, reason)."""
    lower = message.lower()

    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, lower):
            return True, "possible_prompt_injection"

    for pattern in OFFENSIVE_INTENT_PATTERNS:
        if re.search(pattern, lower):
            return True, "possible_offensive_request"

    return False, ""


def check_output(response: str) -> tuple[bool, str]:
    """
    Sanity-check the model's own answer. This is a second line of defense
    in case the system prompt didn't fully hold.
    """
    lower = response.lower()

    for pattern in OFFENSIVE_INTENT_PATTERNS:
        if re.search(pattern, lower):
            return True, "output_resembles_offensive_content"

    # Extremely short/empty answers on a substantive question are also
    # worth flagging for review rather than silently returning them.
    if len(response.strip()) < 3:
        return True, "empty_or_degenerate_response"

    return False, ""


def is_grounded(retrieved_hits: list[dict], distance_threshold: float = 0.8) -> bool:
    """
    Heuristic grounding check: if we retrieved nothing, or the closest
    match is too dissimilar (cosine distance above the threshold), the
    answer is likely not well-supported by the knowledge base and should
    be flagged in the UI / audit log as "ungrounded".
    """
    if not retrieved_hits:
        return False
    best_distance = min(h["distance"] for h in retrieved_hits)
    return best_distance <= distance_threshold
