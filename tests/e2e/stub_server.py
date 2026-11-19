#!/usr/bin/env python3
"""
A stand-in Brain Server for the CLI integration tests.

It answers what a ``jarvis`` model config talks to, records every chat request it gets and
always replies with the same text, so a test checks what the CLI *sent* (system prompt,
files, task, images, history) instead of what a model happened to answer.

    python3 stub_server.py STATE_DIR

- listens on a free port on 127.0.0.1 and writes it to STATE_DIR/port
- POST /api/v1/chat/completions: the JSON body goes to STATE_DIR/requests/NNNN.json (and
  STATE_DIR/last.json); the answer, streamed (SSE) or not, is the first of:
    1. the oldest file in STATE_DIR/replies/ (consumed: a scripted turn, e.g. an agent tool call)
    2. STATE_DIR/reply.txt (kept: the same answer every time)
    3. STUB_REPLY ("STUB_OK")
  STATE_DIR/delay.txt (seconds), when present, delays every answer
- GET /api/health, GET /api/v1/model-configs: minimal answers, enough for clients and relays
- stops on SIGTERM / SIGINT

Standard library only: it must run with any Python, without the project's venv.
"""

import json
import os
import signal
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

STUB_REPLY = os.environ.get("STUB_REPLY", "STUB_OK")
STUB_MODEL = "stub"


class Handler(BaseHTTPRequestHandler):
    state_dir = "."
    counter = 0
    lock = threading.Lock()

    def log_message(self, fmt, *args):  # keep the test output clean
        pass

    def _json(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/api/health":
            self._json(200, {"status": "online", "model": STUB_MODEL, "loaded": True,
                             "available": [STUB_MODEL], "relay": None, "api_level": 2})
        elif self.path.startswith("/api/v1/model-configs"):
            self._json(200, [{"key": STUB_MODEL, "name": STUB_MODEL, "loadable": True, "vision": True}])
        else:
            self._json(404, {"detail": "Not found"})

    def do_POST(self):
        if not self.path.startswith("/api/v1/chat"):
            self._json(404, {"detail": "Not found"})
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            self._json(400, {"detail": "invalid JSON"})
            return
        self._record(payload)
        self._delay()
        reply = self._next_reply()
        if payload.get("stream"):
            self._stream(reply)
        else:
            self._json(200, {"choices": [{"message": {"role": "assistant", "content": reply}}]})

    def _delay(self):
        """STATE_DIR/delay.txt (seconds): wait before answering, e.g. to interrupt a run mid-request."""
        path = os.path.join(self.state_dir, "delay.txt")
        try:
            with open(path, encoding="utf-8") as f:
                seconds = float(f.read().strip() or 0)
        except (OSError, ValueError):
            return
        time.sleep(max(0.0, min(seconds, 120.0)))

    def _next_reply(self):
        with Handler.lock:
            queue = os.path.join(self.state_dir, "replies")
            if os.path.isdir(queue):
                names = sorted(n for n in os.listdir(queue) if not n.startswith("."))
                if names:
                    path = os.path.join(queue, names[0])
                    with open(path, encoding="utf-8") as f:
                        text = f.read()
                    os.remove(path)
                    return text
            fixed = os.path.join(self.state_dir, "reply.txt")
            if os.path.isfile(fixed):
                with open(fixed, encoding="utf-8") as f:
                    return f.read()
        return STUB_REPLY

    def _record(self, payload):
        with Handler.lock:
            Handler.counter += 1
            number = Handler.counter
        requests_dir = os.path.join(self.state_dir, "requests")
        os.makedirs(requests_dir, exist_ok=True)
        text = json.dumps(payload, indent=2, ensure_ascii=False)
        with open(os.path.join(requests_dir, f"{number:04d}.json"), "w", encoding="utf-8") as f:
            f.write(text)
        with open(os.path.join(self.state_dir, "last.json"), "w", encoding="utf-8") as f:
            f.write(text)

    def _stream(self, reply):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        chunk = {"choices": [{"delta": {"content": reply}}]}
        self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


def main():
    if len(sys.argv) != 2:
        print("usage: stub_server.py STATE_DIR", file=sys.stderr)
        sys.exit(2)
    state_dir = os.path.abspath(sys.argv[1])
    os.makedirs(state_dir, exist_ok=True)
    Handler.state_dir = state_dir

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    tmp = os.path.join(state_dir, "port.tmp")
    with open(tmp, "w") as f:
        f.write(str(port))
    os.replace(tmp, os.path.join(state_dir, "port"))  # appears whole: readers never see a partial port

    def stop(*_):
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    server.serve_forever()


if __name__ == "__main__":
    main()
