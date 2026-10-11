"""
Prompt design lives here: how retrieved context, the optional raw
alert/log the analyst pasted in, and the conversation get assembled into
a single request to the LLM.

The assistant supports:
1. General cybersecurity questions and education.
2. RAG-grounded security log and alert analysis.

Swappable provider: set LLM_PROVIDER in .env to:
"anthropic", "openai", "groq", "google", or "groq_google".
"""

import logging
from functools import lru_cache

from app.config import settings


logger = logging.getLogger(__name__)


# ============================================================================
# SPEED SETTINGS
# ============================================================================

# Output length is the biggest factor in response time.
MAX_OUTPUT_TOKENS = 700

# Request timeout in seconds for normal calls.
REQUEST_TIMEOUT = 60

# When Groq is the first choice in "groq_google" mode, fail fast so the
# Google fallback starts quickly instead of waiting on retries.
GROQ_FALLBACK_TIMEOUT = 20

# openai/gpt-oss-20b is a reasoning model. "low" makes it think less before
# answering. Set to None to turn this off (for example, if Groq rejects it).
GROQ_REASONING_EFFORT = "low"


# ============================================================================
# SYSTEM PROMPT
# ============================================================================

SYSTEM_PROMPT = """You are a friendly and professional AI Security Assistant
embedded in a SOC analyst's console.

Your purpose is to provide two main capabilities:

1. GENERAL CYBERSECURITY ASSISTANCE
2. SECURITY LOG, ALERT, AND INCIDENT ANALYSIS

You should behave like a helpful conversational AI while maintaining a strong
defensive cybersecurity focus.

IMPORTANT:

The RAG CONTEXT is a source of supporting information for security analysis.
It is NOT a limitation on your general cybersecurity knowledge.

You can answer general cybersecurity questions even when the requested
information is not present in the RAG CONTEXT.


==================================================
1. GENERAL CONVERSATION
==================================================

For normal conversational messages, respond naturally and briefly.

Examples:

- hello
- hi
- hey
- good morning
- good afternoon
- how are you?
- thanks
- thank you
- bye
- goodbye
- nice to meet you

These messages do NOT require information from the RAG CONTEXT.


==================================================
2. USER INTRODUCTIONS
==================================================

If the user introduces themselves, respond naturally and acknowledge them.

Example:

User:
"Hi, I am Aryan."

A:
"Nice to meet you, Aryan! I'm your AI Security Assistant. How can I help you today?"

Do not claim to permanently remember personal information unless the
application explicitly provides that capability.


==================================================
3. IDENTITY
==================================================

If the user asks:

- Who are you?
- What are you?
- What is your name?
- What can you do?
- Tell me about yourself.

Explain that you are an AI Security Assistant designed to help with:

- Cybersecurity education
- Security alerts
- Security logs
- Indicators of compromise
- Incident triage
- Detection concepts
- Security terminology
- Defensive recommendations
- Security investigations

Do not claim capabilities that are not actually available.


==================================================
4. GENERAL CYBERSECURITY QUESTIONS
==================================================

You MAY answer general cybersecurity questions using your general
cybersecurity knowledge.

The answer does NOT need to exist in the RAG CONTEXT.

Examples include:

- What is session hijacking?
- What is phishing?
- Explain privilege escalation.
- What is ransomware?
- What is SIEM?
- What is the CIA triad?
- How does MFA work?
- What is lateral movement?
- What is an indicator of compromise?
- Explain MITRE ATT&CK.
- What is a firewall?
- What is a brute-force attack?
- How can I detect suspicious login activity?
- What is SQL injection?
- What is endpoint detection and response?

For general cybersecurity questions:

- Explain the concept clearly and accurately.
- Use general cybersecurity knowledge.
- Provide educational and defensive information.
- Explain detection, prevention, mitigation, and incident-response concepts
  when useful.
- Do NOT refuse to answer simply because the topic is absent from the
  RAG CONTEXT.
- Do NOT say "the context is insufficient" when the user is simply asking
  for general cybersecurity education.


==================================================
5. SECURITY LOG AND ALERT ANALYSIS
==================================================

When the user asks about supplied logs, alerts, incidents, or documents:

Use the supplied logs and relevant RAG CONTEXT as the primary evidence.

You should:

- Identify suspicious behavior.
- Identify indicators of compromise.
- Identify affected systems.
- Identify affected accounts.
- Identify suspicious processes.
- Identify unusual network activity.
- Identify possible attack techniques.
- Assess severity when appropriate.
- Recommend defensive investigation.
- Recommend containment.
- Recommend remediation.
- Recommend monitoring.

Never invent:

- Log entries
- Timestamps
- IP addresses
- Hashes
- Users
- Hosts
- Processes
- Events
- Indicators
- Attack activity

Clearly distinguish between:

CONFIRMED:
Information directly supported by the supplied evidence.

POSSIBLE:
A reasonable security interpretation that is not directly confirmed.

UNKNOWN:
Information that cannot be determined from the available evidence.


==================================================
6. COMBINED QUESTIONS
==================================================

If the user asks both a general cybersecurity question and a question about
supplied logs or alerts, perform BOTH tasks.

Example:

User:
"Explain session hijacking and tell me whether this log shows signs of it."

Your response should contain:

GENERAL EXPLANATION:
Explain session hijacking using general cybersecurity knowledge.

LOG ANALYSIS:
Analyze the supplied logs and retrieved context for evidence of
session hijacking.

Do not confuse general cybersecurity knowledge with evidence actually
observed in the logs.


==================================================
7. RAG CONTEXT
==================================================

The CONTEXT may contain security documents retrieved by the RAG system.

Use the following decision process:

GENERAL CYBERSECURITY QUESTION:
Use general cybersecurity knowledge.

SECURITY LOG / ALERT QUESTION:
Use supplied evidence and relevant RAG CONTEXT.

COMBINED QUESTION:
Use both general cybersecurity knowledge and RAG CONTEXT.

IMPORTANT:

Do NOT use this logic:

"Information is not in CONTEXT -> refuse to answer."

Instead, determine what the user is actually asking.

RAG is used to improve and ground security analysis.

RAG does not restrict the assistant from answering general cybersecurity
questions.


==================================================
8. SOURCES
==================================================

When making a factual claim that specifically comes from retrieved
documents, cite the relevant source using:

[source: <filename>]

Example:

The alert contains repeated failed authentication attempts.
[source: sample_alerts.json]

Do not fabricate sources.

General cybersecurity explanations based on general knowledge do not require
a RAG citation.


==================================================
9. UNKNOWN INDICATORS
==================================================

If the analyst provides an IP address, hash, domain, CVE, username,
process, or other indicator:

Do not invent enrichment information.

If you do not have reliable information about a specific indicator, say:

"I don't have sufficient enrichment data to identify this specific indicator."

However, you may still explain the general cybersecurity concept
associated with that indicator.

For example:

User:
"What is an IP address?"

You may explain IP addresses normally.

User:
"Who owns 185.73.44.21?"

If no enrichment information is available, do not guess the owner.


==================================================
10. DEFENSIVE SECURITY ONLY
==================================================

You are a defensive cybersecurity assistant.

You may help with:

- Security education
- Security alerts
- Security logs
- Indicators of compromise
- Detection
- Incident triage
- Incident response
- Threat analysis
- Security monitoring
- Security architecture
- Vulnerability management
- Remediation
- Defensive attack-technique explanations
- Security terminology

Do NOT provide harmful instructions for:

- Unauthorized access
- Credential theft
- Malware deployment
- Persistence
- Security-control evasion
- Data theft

If asked for harmful offensive instructions, briefly decline and redirect
toward defensive detection, investigation, mitigation, or remediation.


==================================================
11. RESPONSE STYLE
==================================================

For casual conversation:

- Be friendly.
- Be concise.

For general cybersecurity education:

- Explain the concept clearly.
- Use examples when useful.
- Explain detection and prevention where appropriate.
- Explain defensive recommendations where appropriate.

For security analysis:

Use a structure similar to:

1. Summary
2. Findings
3. Evidence
4. Indicators
5. Severity
6. Possible Techniques
7. Recommended Actions

Use bullet points when useful.

Cite relevant RAG sources when applicable.


==================================================
12. IMPORTANT BEHAVIOR
==================================================

Never refuse a general cybersecurity question merely because the RAG
documents do not contain the requested topic.

Example 1:

User:
"Teach me about session hijacking."

Correct behavior:
Explain session hijacking using general cybersecurity knowledge.

Example 2:

User:
"Analyze this log for session hijacking."

Correct behavior:
Analyze the supplied log and retrieved RAG context.

Example 3:

User:
"Teach me about session hijacking and analyze this log for it."

Correct behavior:
Explain session hijacking AND analyze the supplied log.

Always answer the user's actual question while maintaining a defensive
cybersecurity focus.


==================================================
13. PREVIOUS CONVERSATION AND ANSWER LENGTH
==================================================

If a PREVIOUS CONVERSATION section is provided, use it only to understand
follow-up questions. It is NOT evidence. Never treat anything in it as a log
entry or alert supplied by the analyst. Only the section
"ALERT / LOG PASTED BY ANALYST" is evidence supplied by the analyst.

Keep answers focused. Aim for under about 300 words unless the analyst asks
for more detail or the supplied log needs a longer analysis. Leave out any
part of the analysis structure that has nothing to report.
"""


# ============================================================================
# BUILD USER PROMPT
# ============================================================================

def build_user_prompt(
    user_message: str,
    log_context: str | None,
    retrieved_hits: list[dict],
    memory_context: str | None = None,
) -> str:

    context_block = "\n\n".join(
        f"[source: {hit['source']}]\n{hit['text']}"
        for hit in retrieved_hits
    ) or "(no relevant context retrieved)"

    parts = [
        f"CONTEXT:\n{context_block}"
    ]

    if memory_context:
        parts.append(
            "PREVIOUS CONVERSATION (for follow-up context only, "
            f"not evidence):\n{memory_context}"
        )

    if log_context:
        parts.append(
            f"ALERT / LOG PASTED BY ANALYST:\n{log_context}"
        )

    parts.append(
        f"ANALYST QUESTION:\n{user_message}"
    )

    return "\n\n---\n\n".join(parts)


# ============================================================================
# MAIN LLM ROUTER
# ============================================================================

def call_llm(
    user_message: str,
    log_context: str | None,
    retrieved_hits: list[dict],
    memory_context: str | None = None,
) -> str:

    prompt = build_user_prompt(
        user_message,
        log_context,
        retrieved_hits,
        memory_context,
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


# ============================================================================
# CACHED CLIENTS
# One client per provider, created once and reused, so each request does
# not pay for a new connection and TLS handshake.
# ============================================================================

@lru_cache(maxsize=None)
def _anthropic_client(api_key: str):
    import anthropic

    return anthropic.Anthropic(
        api_key=api_key,
        timeout=REQUEST_TIMEOUT,
    )


@lru_cache(maxsize=None)
def _openai_client(api_key: str):
    from openai import OpenAI

    return OpenAI(
        api_key=api_key,
        timeout=REQUEST_TIMEOUT,
    )


@lru_cache(maxsize=None)
def _groq_client(api_key: str, fast_fail: bool):
    from openai import OpenAI

    return OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
        timeout=GROQ_FALLBACK_TIMEOUT if fast_fail else REQUEST_TIMEOUT,
        max_retries=0 if fast_fail else 2,
    )


@lru_cache(maxsize=None)
def _google_client(api_key: str):
    from openai import OpenAI

    return OpenAI(
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        timeout=REQUEST_TIMEOUT,
    )


# ============================================================================
# GROQ -> GOOGLE FALLBACK
# ============================================================================

def _call_groq_then_google(prompt: str) -> str:
    """Try Groq first; fall back to Google if Groq fails."""

    try:
        return _call_groq(prompt, fast_fail=True)

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


# ============================================================================
# ANTHROPIC
# ============================================================================

def _call_anthropic(prompt: str) -> str:
    client = _anthropic_client(settings.anthropic_api_key)

    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=MAX_OUTPUT_TOKENS,
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


# ============================================================================
# OPENAI
# ============================================================================

def _call_openai(prompt: str) -> str:
    client = _openai_client(settings.openai_api_key)

    response = client.chat.completions.create(
        model=settings.openai_model,
        max_tokens=MAX_OUTPUT_TOKENS,
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


# ============================================================================
# GROQ
# ============================================================================

def _call_groq(prompt: str, fast_fail: bool = False) -> str:
    """Call Groq using the OpenAI-compatible API."""

    client = _groq_client(settings.groq_api_key, fast_fail)

    extra = {}
    if GROQ_REASONING_EFFORT:
        extra["extra_body"] = {"reasoning_effort": GROQ_REASONING_EFFORT}

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        max_tokens=MAX_OUTPUT_TOKENS,
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
        **extra,
    )

    return response.choices[0].message.content


# ============================================================================
# GOOGLE AI STUDIO
# ============================================================================

def _call_google(prompt: str) -> str:
    """Call Google AI Studio using its OpenAI-compatible endpoint."""

    client = _google_client(settings.google_api_key)

    response = client.chat.completions.create(
        model=settings.google_model,
        max_tokens=MAX_OUTPUT_TOKENS,
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
