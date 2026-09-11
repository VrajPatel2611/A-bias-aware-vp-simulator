"""
A fake LLM gateway (BUILD_PLAN T-002).

Tests must never call a real model. It costs money, it is slow, and it is
non-deterministic — the same input can produce a different reply, so a test
built on one fails at random and is then ignored, which is worse than not
having it.

This fake replaces `call_llm`. It returns scripted replies and records every
call, so a test can assert on what the application *asked* the model as well as
on what it did with the answer.
"""


class FakeLLMError(Exception):
    """Raised by FakeLLM when scripted to fail, standing in for a provider outage."""


class FakeLLM:
    """
    Scriptable stand-in for nidan.infra.llm.gateway.call_llm.

        llm = FakeLLM(["Doctor, my chest hurts."])
        llm("...", "...")           -> "Doctor, my chest hurts."

    Replies are returned in order. When the script runs out, `default` is
    returned — so a test that only cares about the first reply need not script
    every subsequent one.
    """

    def __init__(self, replies=None, default="(fake patient reply)", fail_with=None):
        self.replies = list(replies or [])
        self.default = default
        self.fail_with = fail_with
        self.calls = []          # every call, for assertions

    def __call__(self, messages, system_instruction, *, purpose="patient",
                 max_tokens=200, temperature=0.7, max_retries=3):
        self.calls.append({
            "messages": list(messages),
            "system_instruction": system_instruction,
            "purpose": purpose,
            "max_tokens": max_tokens,
            "temperature": temperature,
        })
        if self.fail_with is not None:
            raise self.fail_with
        if self.replies:
            return self.replies.pop(0)
        return self.default

    # ── assertion helpers ────────────────────────────────────────────
    @property
    def call_count(self):
        return len(self.calls)

    @property
    def last_prompt(self):
        """The text of the last user message sent to the model."""
        if not self.calls:
            return None
        msgs = self.calls[-1]["messages"]
        return msgs[-1]["content"] if msgs else None

    def purposes_used(self):
        return [c["purpose"] for c in self.calls]
