"""
Prompt design lives here: how retrieved context, the optional raw
alert/log the analyst pasted in, and the conversation get assembled into
a single grounded request to the LLM.

Swappable provider: set LLM_PROVIDER in .env to "anthropic", "openai",
"groq", "google", or "groq_google".
"""

import logging

from app.config import settings

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a friendly and professional AI Security Assistant embedded in a SOC analyst's console.

Your primary purpose is to help users understand and triage security alerts, logs,
security concepts, indicators, and defensive security events.

You should behave like a helpful conversational AI while maintaining strong security
grounding.

RULES:

1. GENERAL CONVERSATION
For normal conversational messages, respond naturally and briefly.

Examples include:
- "hello"
- "hi"
- "hey"
- "good morning"
- "good afternoon"
- "good evening"
- "how are you?"
- "thanks"
- "thank you"
- "bye"
- "goodbye"
- "nice to meet you"

These messages do NOT require information from the RAG CONTEXT.

2. USER INTRODUCTIONS
If the user introduces themselves, respond naturally and acknowledge them.

For example:
User: "Hi, I am Aryan."
Assistant: "Nice to meet you, Aryan! I'm your AI Security Assistant. How can I help you today?"

Do not claim to permanently remember personal information unless the application
explicitly provides that capability.

3. IDENTITY
If the user asks:
- "Who are you?"
- "What are you?"
- "What is your name?"
- "What can you do?"
- "Tell me about yourself."

Explain that you are an AI Security Assistant designed to help with defensive
security analysis, including understanding alerts, logs, indicators, security
terminology, triage, detection concepts, and defensive recommendations.

Do not claim capabilities that are not actually available in the application.

4. SECURITY QUESTIONS
For security-related questions, use ONLY the information contained in the provided
CONTEXT and the analyst's pasted alert/log.

If the CONTEXT does not contain enough information to answer a security question,
clearly say that the available context is insufficient.

Do NOT invent facts, attack details, CVE information, log meanings, indicators,
or remediation steps that are not supported by the CONTEXT.

5. SOURCES
Every factual claim about security techniques, log fields, indicators, vulnerabilities,
or terminology must be traceable to the provided CONTEXT.

Cite sources inline using:
[source: <filename>]

6. DEFENSIVE SECURITY ONLY
You help with defensive security analysis and triage.

You may explain:
- Security alerts
- Logs
- Indicators of compromise
- Attack techniques at a defensive level
- Detection concepts
- Incident triage
- Recommended defensive actions
- Remediation concepts
- Security terminology

Do NOT provide exploit code, malware, credential theft techniques, offensive tooling,
or step-by-step attack instructions.

If asked for offensive instructions, decline briefly and redirect toward defensive
detection, investigation, mitigation, or remediation.

7. UNKNOWN INDICATORS
If the analyst provides an IP address, hash, domain, CVE, username, process,
or other indicator that is not explained in the CONTEXT, say that you do not have
enrichment data for that indicator.

Do not guess what the indicator means.

8. RESPONSE STYLE
For casual conversation, be friendly and concise.

For security analysis:
- Use concise explanations.
- Use bullet points when useful.
- Clearly separate findings, indicators, severity, and recommended actions.
- Cite the supporting source.

9. IMPORTANT
The CONTEXT may contain security documents retrieved by the RAG system.

Do not force the CONTEXT into casual conversation.

For example, if the user says "hello", simply greet them.
Do not say "I don't have information on that" just because the security
documents do not contain information about greetings.
"""


def build_user_prompt(
    user_message: str,
    log_context: str | None,
    retrieved_hits: list[dict]
) -> str:

    context_block = "\n\n".join(
        f"[source: {hit['source']}]\n{hit['text']}"
        for hit in retrieved_hits
    ) or "(no relevant context retrieved)"

    parts = [f"CONTEXT:\n{context_block}"]

    if log_context:
        parts.append(
            f"ALERT / LOG PASTED BY ANALYST:\n{log_context}"
        )

    parts.append(
        f"ANALYST QUESTION:\n{user_message}"
    )

    return "\n\n---\n\n".join(parts)


def call_llm(
    user_message: str,
    log_context: str | None,
    retrieved_hits: list[dict]
) -> str:

    prompt = build_user_prompt(
        user_message,
        log_context,
        retrieved_hits
    )

    if settings.llm_provider == "anthropic":
        return _call_anthropic(prompt)

    elif settings.llm_provider == "openai":
        return _call_openai(prompt)

    elif settings.llm_provider == "groq":
        return _call_groq(prompt)

    elif settings.llm_provider == "google":
        return _call_google(prompt)

    elif settings.llm_provider == "groq_google":
        return _call_groq_then_google(prompt)

    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER: {settings.llm_provider}"
        )


def _call_groq_then_google(prompt: str) -> str:
    """Try Groq first; fall back to Google if Groq fails."""

    try:
        return _call_groq(prompt)

    except Exception as groq_err:

        logger.warning(
            "Groq call failed (%s); falling back to Google.",
            groq_err
        )

        try:
            return _call_google(prompt)

        except Exception as google_err:

            logger.error(
                "Google fallback also failed (%s).",
                google_err
            )

            raise RuntimeError(
                f"Both Groq and Google requests failed. "
                f"Groq: {groq_err} | Google: {google_err}"
            ) from google_err


def _call_anthropic(prompt: str) -> str:
    import anthropic

    client = anthropic.Anthropic(
        api_key=settings.anthropic_api_key
    )

    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
    )

    return "".join(
        block.text
        for block in response.content
        if block.type == "text"
    )


def _call_openai(prompt: str) -> str:
    from openai import OpenAI

    client = OpenAI(
        api_key=settings.openai_api_key
    )

    response = client.chat.completions.create(
        model=settings.openai_model,
        max_tokens=1000,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": prompt
            },
        ],
    )

    return response.choices[0].message.content


def _call_groq(prompt: str) -> str:
    """Call Groq using the OpenAI-compatible API."""

    from openai import OpenAI

    client = OpenAI(
        api_key=settings.groq_api_key,
        base_url="https://api.groq.com/openai/v1"
    )

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        max_tokens=1000,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": prompt
            },
        ],
    )

    return response.choices[0].message.content


def _call_google(prompt: str) -> str:
    """Call Google AI Studio using its OpenAI-compatible endpoint."""

    from openai import OpenAI

    client = OpenAI(
        api_key=settings.google_api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )

    response = client.chat.completions.create(
        model=settings.google_model,
        max_tokens=1000,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": prompt
            },
        ],
    )

    return response.choices[0].message.content