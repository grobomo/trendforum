#!/usr/bin/env python3
"""Local web-based credential manager for Entra ID → Linux keyring.

Opens a browser tab on Windows with a simple form. Values are POSTed
to a local HTTP server running in WSL, which stores them via secret-tool.
"""

import http.server
import json
import subprocess
import sys
import threading
import urllib.parse

PORT = 18799
KEYRING_ATTR = "application"
KEYRING_APP = "openclaw"

FIELDS = [
    ("ENTRA_TENANT_ID", "Tenant ID (Directory ID)"),
    ("ENTRA_CLIENT_ID", "Client ID (Application ID)"),
    ("ENTRA_CLIENT_SECRET", "Client Secret"),
]

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>🥥 Coconut — Entra Credential Manager</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', system-ui, sans-serif; background: #1a1a2e; color: #e0e0e0;
         display: flex; justify-content: center; align-items: center; min-height: 100vh; }
  .card { background: #16213e; border-radius: 16px; padding: 40px; width: 520px;
          box-shadow: 0 8px 32px rgba(0,0,0,.4); }
  h1 { text-align: center; font-size: 1.5rem; margin-bottom: 8px; }
  .sub { text-align: center; color: #8899aa; font-size: 0.9rem; margin-bottom: 28px; }
  label { display: block; font-weight: 600; margin-bottom: 6px; margin-top: 18px; font-size: 0.95rem; }
  input[type=text], input[type=password] {
    width: 100%; padding: 10px 14px; border: 1px solid #2a3a5a; border-radius: 8px;
    background: #0f3460; color: #e0e0e0; font-size: 0.95rem; font-family: 'Cascadia Code', monospace;
  }
  input:focus { outline: none; border-color: #e94560; }
  .btn-row { display: flex; gap: 12px; margin-top: 28px; justify-content: center; }
  button { padding: 10px 24px; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer;
           font-weight: 600; transition: transform .1s; }
  button:active { transform: scale(.97); }
  .save { background: #e94560; color: white; }
  .save:hover { background: #c73850; }
  .toggle { background: #2a3a5a; color: #ccc; }
  .toggle:hover { background: #3a4a6a; }
  .result { text-align: center; margin-top: 20px; padding: 12px; border-radius: 8px; display: none; }
  .ok { background: #1a4a2a; color: #6fef8d; }
  .err { background: #4a1a1a; color: #ef6f6f; }
</style>
</head>
<body>
<div class="card">
  <h1>🌴 Entra ID Credentials</h1>
  <p class="sub">Paste each value below. They go straight into the Linux keyring — nothing touches disk.</p>
  <form id="f">
    FIELD_HTML
    <div class="btn-row">
      <button type="button" class="toggle" onclick="toggleVis()">👁 Show</button>
      <button type="submit" class="save">💾 Save to Keyring</button>
    </div>
  </form>
  <div id="result" class="result"></div>
</div>
<script>
  let showing = false;
  function toggleVis() {
    showing = !showing;
    document.querySelectorAll('.secret').forEach(i => i.type = showing ? 'text' : 'password');
    document.querySelector('.toggle').textContent = showing ? '🙈 Hide' : '👁 Show';
  }
  document.getElementById('f').onsubmit = async (e) => {
    e.preventDefault();
    const data = {};
    document.querySelectorAll('.secret').forEach(i => { data[i.name] = i.value.trim(); });
    const empty = Object.entries(data).filter(([,v]) => !v);
    if (empty.length) { show('Fill in all fields first.', false); return; }
    try {
      const r = await fetch('/save', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) });
      const j = await r.json();
      show(j.message, j.ok);
    } catch(err) { show('Connection error: ' + err, false); }
  };
  function show(msg, ok) {
    const el = document.getElementById('result');
    el.textContent = msg; el.className = 'result ' + (ok ? 'ok' : 'err'); el.style.display = 'block';
  }
</script>
</body>
</html>"""


def build_html():
    parts = []
    for key, label in FIELDS:
        parts.append(f'<label for="{key}">{label}</label>')
        parts.append(f'<input type="password" class="secret" name="{key}" id="{key}" autocomplete="off" spellcheck="false">')
    return HTML_PAGE.replace("FIELD_HTML", "\n    ".join(parts))


def store_secret(key: str, value: str) -> bool:
    try:
        proc = subprocess.run(
            ["secret-tool", "store", "--label", f"openclaw/{key}", KEYRING_ATTR, KEYRING_APP, "key", key],
            input=value.encode(), capture_output=True, timeout=10,
        )
        return proc.returncode == 0
    except Exception as e:
        print(f"Error storing {key}: {e}", file=sys.stderr)
        return False


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(build_html().encode())

    def do_POST(self):
        if self.path != "/save":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        errors = []
        for key, label in FIELDS:
            val = body.get(key, "").strip()
            if val and not store_secret(key, val):
                errors.append(label)
        if errors:
            resp = {"ok": False, "message": f"Failed to store: {', '.join(errors)}"}
        else:
            resp = {"ok": True, "message": "✅ All credentials saved to Linux keyring!"}
        payload = json.dumps(resp).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)
        if resp["ok"]:
            # Shut down after successful save
            threading.Thread(target=self.server.shutdown, daemon=True).start()

    def log_message(self, fmt, *args):
        print(f"[cred-store] {fmt % args}")


def main():
    server = http.server.HTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://localhost:{PORT}"
    print(f"[cred-store] Listening on {url}")
    # Try to open browser on Windows side
    try:
        subprocess.Popen(
            ["cmd.exe", "/c", "start", url],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        print("[cred-store] Opened browser on Windows")
    except Exception:
        print(f"[cred-store] Open {url} manually in your browser")
    server.serve_forever()
    print("[cred-store] Done — shutting down")


if __name__ == "__main__":
    main()
