"""Recap demo server (Python stdlib only).

Run:  python3 server.py            -> http://127.0.0.1:8765
Env:  ANTHROPIC_API_KEY            -> enables Claude-written brief and Q&A
      RECAP_PORT                   -> port (default 8765)
"""
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import engine
import llm

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "data", "patient.json"), encoding="utf-8") as f:
    RECORD = json.load(f)

STATE = {"consent": [], "granted_at": None, "brief": None, "brief_source": None}
LOCK = threading.Lock()


def sources_meta():
    return [{"id": s["id"], "name": s["name"], "kind": s["kind"],
             "counts": {"meds": len(s["prescriptions"]), "visits": len(s["encounters"]), "labs": len(s["labs"])}}
            for s in RECORD["sources"]]


def current():
    merged = engine.merge(RECORD, set(STATE["consent"]))
    return merged, engine.alerts(merged)


def make_brief(merged, found):
    if llm.available():
        try:
            return llm.brief(merged, found), "claude"
        except Exception as e:  # keep the demo running if the API fails
            print("LLM brief failed:", repr(e))
    return engine.fallback_brief(merged, found), "template"


def offline_answer(merged, found, q):
    ql = q.lower()
    if any(w in ql for w in ("pressure", "bp", "hypertens")):
        ms = [m for m in merged["active_meds"] if "calcium" in m["class"]]
        return "Blood pressure meds: " + "; ".join("%s %s [%s]" % (m["drug"], m["dose"], m["source"]) for m in ms) + ". Two drugs of the same class from two prescribers."
    if any(w in ql for w in ("bruis", "bleed", "inr")):
        return "Warfarin 5 mg [Sunrise Medical Center] plus ibuprofen 400 mg TID since 2026-11-02 [Harbor City Hospital]. Last INR 2.4 on 2026-09-20 [Sunrise Medical Center], before the NSAID. Check INR today."
    if any(w in ql for w in ("rash", "allerg", "itch")):
        return "Penicillin allergy with hives [Sunrise Medical Center]. Amoxicillin-clavulanate given 2026-11-02 to 11-08 [Harbor City Hospital]; rash started about 5 days ago. Consider drug reaction."
    if any(w in ql for w in ("kidney", "renal", "egfr")):
        return "eGFR 62 on 2025-12-05 [Sunrise Medical Center] → 48 on 2026-08-22 [Maple Family Clinic]. On metformin and an NSAID."
    return "Offline mode: set ANTHROPIC_API_KEY for free-form questions. Try asking about bruising, rash, blood pressure or kidney function."


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype + ("; charset=utf-8" if "json" in ctype or "html" in ctype else ""))
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            with open(os.path.join(HERE, "static", "index.html"), "rb") as f:
                return self._send(200, f.read(), "text/html")
        if self.path == "/api/state":
            with LOCK:
                merged, found = current()
                return self._send(200, {
                    "patient": RECORD["patient"], "today": RECORD["today"], "sources": sources_meta(),
                    "consent": STATE["consent"], "granted_at": STATE["granted_at"],
                    "llm": llm.available(), "model": llm.MODEL if llm.available() else None,
                    "merged": merged if STATE["consent"] else None,
                    "alerts": found if STATE["consent"] else [],
                    "brief": STATE["brief"], "brief_source": STATE["brief_source"],
                })
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/api/consent":
            ids = [i for i in self._body().get("sources", []) if i in {s["id"] for s in RECORD["sources"]}]
            with LOCK:
                STATE.update(consent=ids, granted_at=time.time() if ids else None, brief=None, brief_source=None)
                merged, found = current()
            if ids:
                text, src = make_brief(merged, found)
                with LOCK:
                    STATE.update(brief=text, brief_source=src)
            return self._send(200, {"ok": True})
        if self.path == "/api/reset":
            with LOCK:
                STATE.update(consent=[], granted_at=None, brief=None, brief_source=None)
            return self._send(200, {"ok": True})
        if self.path == "/api/ask":
            q = (self._body().get("question") or "").strip()[:500]
            if not q:
                return self._send(400, {"error": "empty question"})
            with LOCK:
                if not STATE["consent"]:
                    return self._send(403, {"error": "No patient consent yet."})
                merged, found = current()
            if llm.available():
                try:
                    return self._send(200, {"answer": llm.ask(merged, found, q), "source": "claude"})
                except Exception as e:
                    print("LLM ask failed:", repr(e))
            return self._send(200, {"answer": offline_answer(merged, found, q), "source": "template"})
        return self._send(404, {"error": "not found"})


if __name__ == "__main__":
    port = int(os.environ.get("RECAP_PORT", "8765"))
    print("Recap on http://127.0.0.1:%d  (LLM: %s)" % (port, llm.MODEL if llm.available() else "offline template"))
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
