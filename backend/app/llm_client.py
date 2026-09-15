"""
Prompt design lives here: how retrieved context, the optional raw
alert/log the analyst pasted in, and the conversation get assembled into
a single grounded request to the LLM.

Swappable provider: set LLM_PROVIDER=anthropic or openai in .env. Both
paths share the same system prompt and context-formatting logic so the
grounding behavior doesn't depend on which vendor you use.
"""
from app.config import settings

SYSTEM_PROMPT = """You are a defensive security assistant embedded in a SOC analyst's console.
Your job is to explain security alerts, logs, and terminology clearly and accurately.

Rules you must follow:
1. Answer ONLY using the CONTEXT provided below and the analyst's pasted alert/log, if any.
   If the context does not contain enough information to answer, say so explicitly instead
   of guessing.
2. Every factual claim about attack techniques, log fields, or terminology must be
   traceable to the provided CONTEXT. Cite sources inline like [source: <filename>].
3. You explain and help TRIAGE. You do not write exploit code, malware, offensive tooling,
   or step-by-step attack instructions, even if asked to "for education" or "for a CTF".
   If asked for that, decline and redirect to defensive framing (what to detect, how to
   respond, how to remediate).
4. Be precise and concise. Prefer short paragraphs and bullet points for indicators,
   recommended actions, and severity assessment.
5. If the analyst's pasted log/alert contains an indicator (IP, hash, domain, CVE) that
   isn't explained in the CONTEXT, say you don't have enrichment data for it rather than
   inventing an explanation.
"""


def build_user_prompt(user_message: str, log_context: str | None, retrieved_hits: list[dict]) -> str:
    context_block = "\n\n".join(
        f"[source: {hit['source']}]\n{hit['text']}" for hit in retrieved_hits
    ) or "(no relevant context retrieved)"

    parts = [f"CONTEXT:\n{context_block}"]

    if log_context:
        parts.append(f"ALERT / LOG PASTED BY ANALYST:\n{log_context}")

    parts.append(f"ANALYST QUESTION:\n{user_message}")
    return "\n\n---\n\n".join(parts)


def call_llm(user_message: str, log_context: str | None, retrieved_hits: list[dict]) -> str:
    prompt = build_user_prompt(user_message, log_context, retrieved_hits)

    if settings.llm_provider == "anthropic":
        return _call_anthropic(prompt)
    elif settings.llm_provider == "openai":
        return _call_openai(prompt)
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {settings.llm_provider}")


def _call_anthropic(prompt: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def _call_openai(prompt: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=settings.openai_model,
        max_tokens=1000,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content
