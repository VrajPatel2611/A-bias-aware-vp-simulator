"""
LLM gateway.

The single place the application talks to a language model. Every call goes
through here so that retry, provider selection and (later) cost accounting have
one home.

Design rule (PR-1, ADR-0005): the model generates text only. It never produces a
flag, a score or a verdict. Those are computed by nidan.domain.assessment from
the learner's own actions, which is what makes results reproducible.

NOTE (BUILD_PLAN T-031): this will gain per-purpose model routing, a circuit
breaker, and llm_calls cost logging. The signature is deliberately shaped for
that now (`purpose`) so callers do not change later.
"""

import os
import time

from groq import Groq

from nidan.config import settings

_client = None


def _get_client() -> Groq:
    """Lazily construct the client so importing this module needs no API key."""
    global _client
    if _client is None:
        _client = Groq(api_key=settings.GROQ_API_KEY)
    return _client


def _model_for(purpose: str) -> str:
    """
    Per-purpose model selection (ADR-0011).

    Today every purpose resolves to the same model; the indirection exists so
    routing can be introduced without touching call sites.
    """
    # The per-purpose override stays an os.getenv: the variable name is built
    # from `purpose` at call time, so it cannot be a declared Settings field.
    # The default comes from validated configuration.
    return os.getenv(f"GROQ_MODEL_{purpose.upper()}", settings.GROQ_MODEL)


_TRANSIENT = ("429", "500", "502", "503", "over capacity",
              "rate limit", "Empty response")


def call_llm(messages, system_instruction, *, purpose="patient",
             max_tokens=200, temperature=0.7, max_retries=3):
    """
    Call the chat-completions API with retry on transient errors.

    Args:
        messages (list): [{"role": "user"|"assistant", "content": str}, ...],
                         oldest first.
        system_instruction (str): system prompt — the patient persona, or the
                         tutor instruction for feedback.
        purpose (str): 'patient' | 'feedback' | 'extraction' | 'judge'.
                       Selects the model and, later, the cost bucket.

    Returns:
        str: the assistant's reply text.

    Raises:
        The last exception if every attempt fails. Callers are expected to
        degrade gracefully rather than propagate this to the learner.
    """
    payload = [{"role": "system", "content": system_instruction}] + messages
    model = _model_for(purpose)

    last_err = None
    for attempt in range(max_retries):
        try:
            resp = _get_client().chat.completions.create(
                model=model,
                messages=payload,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            text = (resp.choices[0].message.content or "").strip()
            if not text:
                raise ValueError("Empty response from model")
            return text
        except Exception as e:
            last_err = e
            transient = any(s in str(e) for s in _TRANSIENT)
            if transient and attempt < max_retries - 1:
                wait = (attempt + 1) * 2   # 2 s, 4 s
                print(f"LLM transient error — retrying in {wait}s "
                      f"(attempt {attempt + 1}): {str(e)[:80]}")
                time.sleep(wait)
            else:
                raise
    raise last_err
