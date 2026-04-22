import { SecretsManagerClient, CreateSecretCommand, PutSecretValueCommand } from "@aws-sdk/client-secrets-manager";

const sm = new SecretsManagerClient({});

const html = `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>🌴 Coconut Secrets Vault</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0d1117; color: #e6edf3; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
  .card { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 2rem; max-width: 480px; width: 90%; }
  h1 { font-size: 1.4rem; margin-bottom: 0.5rem; }
  .sub { color: #8b949e; font-size: 0.85rem; margin-bottom: 1.5rem; }
  label { display: block; font-size: 0.85rem; color: #8b949e; margin-bottom: 0.3rem; margin-top: 1rem; }
  input, textarea { width: 100%; background: #0d1117; border: 1px solid #30363d; border-radius: 6px; color: #e6edf3; padding: 0.6rem; font-size: 0.9rem; font-family: inherit; }
  input:focus, textarea:focus { outline: none; border-color: #58a6ff; }
  textarea { resize: vertical; min-height: 80px; }
  button { margin-top: 1.5rem; width: 100%; padding: 0.7rem; background: #238636; border: none; border-radius: 6px; color: #fff; font-size: 1rem; cursor: pointer; font-weight: 600; }
  button:hover { background: #2ea043; }
  button:disabled { background: #30363d; cursor: not-allowed; }
  .result { margin-top: 1rem; padding: 0.8rem; border-radius: 6px; font-size: 0.85rem; display: none; }
  .result.ok { background: #0d2818; border: 1px solid #238636; color: #3fb950; display: block; }
  .result.err { background: #2d1117; border: 1px solid #da3633; color: #f85149; display: block; }
</style>
</head>
<body>
<div class="card">
  <h1>🌴 Coconut Secrets Vault</h1>
  <p class="sub">Paste a secret value below. It goes straight to AWS Secrets Manager — nothing logged, nothing stored locally.</p>
  <form id="f">
    <label for="name">Secret Name</label>
    <input id="name" name="name" placeholder="e.g. daemon-squad/tailscale-auth-key" required>
    <label for="secret">Secret Value</label>
    <textarea id="secret" name="secret" placeholder="Paste the secret here..." required></textarea>
    <button type="submit" id="btn">Store Secret 🔐</button>
  </form>
  <div id="result" class="result"></div>
</div>
<script>
document.getElementById('f').addEventListener('submit', async e => {
  e.preventDefault();
  const btn = document.getElementById('btn');
  const res = document.getElementById('result');
  btn.disabled = true; btn.textContent = 'Storing...';
  res.className = 'result'; res.style.display = 'none';
  try {
    const r = await fetch(window.location.pathname.replace(/\\/$/, '') + '/store', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: document.getElementById('name').value, secret: document.getElementById('secret').value })
    });
    const d = await r.json();
    if (r.ok) {
      res.className = 'result ok'; res.textContent = '✅ ' + d.message;
      document.getElementById('secret').value = '';
    } else {
      res.className = 'result err'; res.textContent = '❌ ' + (d.error || 'Unknown error');
    }
  } catch(err) {
    res.className = 'result err'; res.textContent = '❌ Network error: ' + err.message;
  }
  btn.disabled = false; btn.textContent = 'Store Secret 🔐';
});
</script>
</body>
</html>`;

export const handler = async (event) => {
  const method = event.requestContext?.http?.method || event.httpMethod || 'GET';
  const path = event.rawPath || event.path || '/';

  // Serve the UI
  if (method === 'GET') {
    return { statusCode: 200, headers: { 'Content-Type': 'text/html' }, body: html };
  }

  // Handle store request
  if (method === 'POST' && path.endsWith('/store')) {
    try {
      const body = JSON.parse(event.body || '{}');
      const { name, secret } = body;

      if (!name || !secret) {
        return { statusCode: 400, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ error: 'Missing name or secret' }) };
      }

      // Validate name: only allow daemon-squad/ prefix for safety
      if (!name.startsWith('daemon-squad/')) {
        return { statusCode: 400, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ error: 'Secret name must start with daemon-squad/' }) };
      }

      try {
        await sm.send(new CreateSecretCommand({ Name: name, SecretString: secret, Description: `Stored via Coconut Secrets UI` }));
      } catch (e) {
        if (e.name === 'ResourceExistsException') {
          await sm.send(new PutSecretValueCommand({ SecretId: name, SecretString: secret }));
        } else throw e;
      }

      return { statusCode: 200, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: `Secret "${name}" stored successfully.` }) };
    } catch (e) {
      return { statusCode: 500, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ error: e.message }) };
    }
  }

  return { statusCode: 404, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ error: 'Not found' }) };
};
