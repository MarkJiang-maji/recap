"""Claude calls for the pre-visit brief and doctor Q&A.

Uses ANTHROPIC_API_KEY (or ANTHROPIC_AUTH_TOKEN) from the environment.
Without credentials, the server falls back to template text.
"""
import json
import os

MODEL = os.environ.get("RECAP_MODEL", "claude-opus-5-5")

BRIEF_SYSTEM = """You are Recap, a clinical summarizer used by a doctor in the 30 seconds before a visit.
You receive a patient's records merged from several hospitals (with the hospital name on every item),
plus safety alerts already computed by deterministic rules.

Write the pre-visit brief in English, at most 110 words, as 4-6 short bullet lines starting with "- ".
Lead with what matters for today's complaint. Connect findings across hospitals when they explain
today's complaint. Put the source hospital in square brackets after each fact, e.g. [Sunrise Medical Center].
Use only facts in the records. Do not diagnose with certainty; say "possible" or "consider".
No headings, no preamble."""

ASK_SYSTEM = """You are Recap, answering a doctor's question about one patient during a visit.
Answer only from the merged records and alerts provided. Put the source hospital in square brackets
after each fact. If the records do not contain the answer, say so plainly and suggest what to ask
the patient. At most 80 words, plain text."""


def available():
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


_client = None


def _get_client():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic(timeout=60.0)
    return _client


def _call(system, user_text):
    client = _get_client()
    resp = client.beta.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=system,
        messages=[{"role": "user", "content": user_text}],
        betas=["server-side-fallback-2026-07-01"],
        extra_body={"fallbacks": "default", "output_config": {"effort": "low"}},
    )
    if resp.stop_reason == "refusal":
        raise RuntimeError("Model declined this request.")
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    if not text:
        raise RuntimeError("Empty response (stop_reason=%s)." % resp.stop_reason)
    return text


def _context(merged, found):
    return "MERGED RECORDS:\n%s\n\nRULE-BASED ALERTS:\n%s" % (
        json.dumps(merged, ensure_ascii=False, indent=1),
        json.dumps(found, ensure_ascii=False, indent=1),
    )


def brief(merged, found):
    return _call(BRIEF_SYSTEM, _context(merged, found))


def ask(merged, found, question):
    return _call(ASK_SYSTEM, _context(merged, found) + "\n\nDOCTOR'S QUESTION:\n" + question)
