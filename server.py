#!/usr/bin/env python3
# Comma single-file demo + OpenAI proxy (stdlib only)
# Usage:
#   export OPENAI_API_KEY="sk-..."
#   python server.py
#
# Then open: http://localhost:8000/

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "8000"))
INDEX_PATH = os.path.join(os.path.dirname(__file__), "index.html")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

def build_prompt(mode: str, who: str, text: str) -> str:
    return "\n".join([
        "Du er en nøytral kommunikasjonsassistent for par.",
        "Du moraliserer aldri og dømmer aldri.",
        "Skriv på norsk bokmål. Kort, konkret, gjennomførbart.",
        f"MODUS: {mode}",
        f"AVSENDER: {'meg' if who=='me' else 'partner'}",
        "RÅ TEKST:",
        text,
        "",
        "Returner JSON med feltene: summary (string), suggestions (array med 3-5).",
        "Hvert forslag: {title, text, tone (valgfri), commarule (valgfri)}.",
        "Hvis modus=agreement: inkluder commarule."
    ])

def openai_request(payload: dict) -> dict:
    if not OPENAI_API_KEY:
        return {"summary":"Mangler OPENAI_API_KEY på serveren.", "suggestions":[{"title":"Feil","text":"Sett OPENAI_API_KEY og restart server.py"}], "warnings":["Missing OPENAI_API_KEY"]}

    req = Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type":"application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}",
        },
        method="POST"
    )
    with urlopen(req, timeout=45) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw)

def extract_output_text(resp_json: dict) -> str:
    out = resp_json.get("output")
    if isinstance(out, list):
        chunks = []
        for item in out:
            if item.get("type") != "message":
                continue
            for c in item.get("content", []):
                if c.get("type") == "output_text" and isinstance(c.get("text"), str):
                    chunks.append(c["text"])
        return "\n".join(chunks).strip()
    return (resp_json.get("output_text") or "").strip()

class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, ctype: str):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/index.html"):
            try:
                with open(INDEX_PATH, "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except FileNotFoundError:
                self._send(404, b"Missing index.html", "text/plain; charset=utf-8")
            return

        if self.path.startswith("/api/ping"):
            self._send(200, json.dumps({"ok":True, "time":__import__("datetime").datetime.utcnow().isoformat()+"Z"}).encode("utf-8"),
                       "application/json; charset=utf-8")
            return

        self._send(404, b"Not found", "text/plain; charset=utf-8")

    def do_POST(self):
        if not self.path.startswith("/api/assist"):
            self._send(404, b"Not found", "text/plain; charset=utf-8")
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            self._send(400, b"Bad JSON", "text/plain; charset=utf-8")
            return

        mode = str(body.get("mode","rewrite"))
        who = str(body.get("who","me"))
        text = str(body.get("text","")).strip()

        if not text:
            self._send(400, json.dumps({"summary":"Mangler tekst.", "suggestions":[]}).encode("utf-8"),
                       "application/json; charset=utf-8")
            return

        prompt = build_prompt(mode, who, text)

        schema = {
            "name": "comma_assist",
            "schema": {
                "type":"object",
                "additionalProperties": False,
                "properties":{
                    "summary":{"type":"string"},
                    "warnings":{"type":"array","items":{"type":"string"}},
                    "suggestions":{
                        "type":"array",
                        "minItems":3,
                        "maxItems":5,
                        "items":{
                            "type":"object",
                            "additionalProperties": False,
                            "properties":{
                                "title":{"type":"string"},
                                "text":{"type":"string"},
                                "tone":{"type":"string"},
                                "commarule":{"type":"string"}
                            },
                            "required":["title","text"]
                        }
                    }
                },
                "required":["summary","suggestions"]
            },
            "strict": True
        }

        payload = {
            "model": MODEL,
            "instructions": "Du er en nøytral kommunikasjonsassistent. Ingen moral. Ingen dom.",
            "input": prompt,
            "text": {"format": {"type":"json_schema", "json_schema": schema}},
            "temperature": 0.6,
            "max_output_tokens": 450
        }

        try:
            resp_json = openai_request(payload)
            txt = extract_output_text(resp_json)
            try:
                out = json.loads(txt)
            except json.JSONDecodeError:
                out = {"summary":"Mottok svar, men kunne ikke parse JSON.", "suggestions":[{"title":"Svar","text":txt}]}
            self._send(200, json.dumps(out).encode("utf-8"), "application/json; charset=utf-8")
        except HTTPError as e:
            self._send(500, json.dumps({"summary":"OpenAI-feil", "suggestions":[{"title":"HTTPError","text":str(e)}]}).encode("utf-8"),
                       "application/json; charset=utf-8")
        except URLError as e:
            self._send(500, json.dumps({"summary":"Nettverksfeil", "suggestions":[{"title":"URLError","text":str(e)}]}).encode("utf-8"),
                       "application/json; charset=utf-8")
        except Exception as e:
            self._send(500, json.dumps({"summary":"Ukjent feil", "suggestions":[{"title":"Error","text":str(e)}]}).encode("utf-8"),
                       "application/json; charset=utf-8")

def main():
    print(f"Serving on http://localhost:{PORT}/  (API proxy: /api/assist)")
    if not OPENAI_API_KEY:
        print("NOTE: OPENAI_API_KEY is not set. API mode will error until you set it.")
    HTTPServer((HOST, PORT), Handler).serve_forever()

if __name__ == "__main__":
    main()
