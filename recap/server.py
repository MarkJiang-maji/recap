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
with open(os.path.join(HERE, "data", "cached_llm.json"), encoding="utf-8") as f:
    CACHED = json.load(f)
ALL_SOURCES = {s["id"] for s in RECORD["sources"]}


def ai_mode():
    return "live" if llm.available() else "cached"

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
    if set(STATE["consent"]) == ALL_SOURCES:
        return CACHED["brief"], "cached"
    return engine.fallback_brief(merged, found), "template"


def cached_answer(q):
    ql = q.lower()
    best, score = None, 0
    for item in CACHED["answers"]:
        s = sum(1 for k in item["keywords"] if k in ql)
        if s > score:
            best, score = item, s
    if best and set(STATE["consent"]) == ALL_SOURCES:
        return best["a"]
    return "This demo build has no API key, so it answers a fixed set of questions. Try one of the suggested questions below."


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
                    "llm": llm.available(), "model": llm.MODEL, "ai_mode": ai_mode(),
                    "suggestions": [a["q"] for a in CACHED["answers"]],
                    "extraction": CACHED["extraction"] if CACHED["extraction"]["source_id"] in STATE["consent"] else None,
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
            return self._send(200, {"answer": cached_answer(q), "source": "cached"})
        return self._send(404, {"error": "not found"})


if __name__ == "__main__":
    port = int(os.environ.get("RECAP_PORT", "8765"))
    print("Recap on http://127.0.0.1:%d  (AI: %s)" % (port, llm.MODEL + " live" if llm.available() else "cached Claude outputs"))
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
