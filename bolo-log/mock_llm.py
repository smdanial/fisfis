"""Mock of an OpenAI-compatible /v1/chat/completions endpoint (test helper).

Returns a canned {"transcript": ..., "result": ...} JSON regardless of the
request body. Run with: .venv/bin/python mock_llm.py [port]
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

CANNED = {
    "id": "mock-1",
    "object": "chat.completion",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": json.dumps(
                    {
                        "transcript": "mock transcript romanized",
                        "result": "mock note result",
                    }
                ),
            },
        }
    ],
}


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("content-length", 0))
        self.rfile.read(length)
        body = json.dumps(CANNED).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8899
    print(f"mock LLM on :{port}")
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()
