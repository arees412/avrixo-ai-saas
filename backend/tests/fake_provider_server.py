"""Test-only OpenAI-compatible HTTP fixture. Never included in app imports."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        assert body["model"] == "test-model"
        payload = json.dumps(
            {
                "choices": [{"message": {"content": "Test provider: task completed."}}],
                "usage": {
                    "prompt_tokens": 12,
                    "completion_tokens": 8,
                    "total_tokens": 20,
                },
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        # Keep prompts, headers, and outputs out of CI logs.
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 9001), Handler).serve_forever()
