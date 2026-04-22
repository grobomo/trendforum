#!/usr/bin/env python3
"""One-shot OAuth2 re-auth server.

1. Starts HTTP server on port 18790
2. Waits for Entra redirect with auth code
3. Exchanges code for tokens (with Tasks.ReadWrite scope)
4. Saves to ~/.msgraph/tokens.json
5. Exits
"""

import json
import os
import sys
import time
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

TENANT = '3e04753a-ae5b-42d4-a86d-d6f05460f9e4'
CLIENT = 'bd6209be-717c-41a1-add5-19095aeeebec'
REDIRECT = 'http://localhost:18790/auth/callback'
TOKEN_FILE = os.path.expanduser('~/.msgraph/tokens.json')

SCOPES = (
    'Mail.Read Mail.ReadWrite Mail.Send '
    'Chat.Read Chat.ReadWrite Chat.ReadWrite.All ChatMessage.Read ChatMessage.Send ChatMember.Read Chat.Create Chat.ReadBasic '
    'Calendars.Read Calendars.ReadWrite '
    'User.Read User.Read.All User.ReadBasic.All '
    'Files.Read Files.Read.All Files.ReadWrite.All '
    'Group.Read.All '
    'Channel.ReadBasic.All ChannelMember.Read.All ChannelMessage.Read.All ChannelMessage.ReadWrite ChannelMessage.Send ChannelSettings.Read.All '
    'Contacts.Read Contacts.ReadWrite '
    'People.Read '
    'Sites.Read.All Sites.ReadWrite.All Sites.Manage.All '
    'Schedule.Read.All '
    'TeamMember.Read.All TeamsActivity.Read TeamworkTag.ReadWrite '
    'OnlineMeetings.Read OnlineMeetingRecording.Read.All OnlineMeetingTranscript.Read.All OnlineMeetingArtifact.Read.All OnlineMeetingAiInsight.Read.All '
    'Insights-UserMetric.Read.All '
    'Tasks.ReadWrite '
    'offline_access'
)

got_token = False

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global got_token
        parsed = urlparse(self.path)
        if parsed.path != '/auth/callback':
            self.send_response(404)
            self.end_headers()
            return

        params = parse_qs(parsed.query)
        code = params.get('code', [None])[0]
        error = params.get('error', [None])[0]

        if error:
            self.send_response(400)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            desc = params.get('error_description', [''])[0]
            self.wfile.write(f'<h2>Auth failed</h2><p>{error}: {desc}</p>'.encode())
            print(f'ERROR: {error}: {desc}')
            return

        if not code:
            self.send_response(400)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<h2>No code received</h2>')
            return

        # Exchange code for tokens
        r = requests.post(
            f'https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/token',
            data={
                'grant_type': 'authorization_code',
                'client_id': CLIENT,
                'code': code,
                'redirect_uri': REDIRECT,
                'scope': SCOPES,
            },
            timeout=30,
        )

        if r.status_code == 200:
            resp = r.json()
            save_data = {
                'access_token': resp['access_token'],
                'refresh_token': resp.get('refresh_token', ''),
                'expires_in': resp.get('expires_in', 3600),
                'stored_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
            }
            os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
            with open(TOKEN_FILE, 'w') as f:
                json.dump(save_data, f)
            os.chmod(TOKEN_FILE, 0o600)

            # Verify scopes
            import base64
            parts = resp['access_token'].split('.')
            payload = parts[1] + '=' * (4 - len(parts[1]) % 4)
            decoded = json.loads(base64.b64decode(payload))
            scopes = decoded.get('scp', '').split(' ')
            tasks_scopes = [s for s in scopes if 'Task' in s]

            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(f'''<h2>✅ Token saved!</h2>
<p>Tasks scopes: {tasks_scopes}</p>
<p>Total scopes: {len(scopes)}</p>
<p>You can close this tab.</p>'''.encode())
            
            print(f'SUCCESS: Token saved with {len(scopes)} scopes, Tasks: {tasks_scopes}')
            got_token = True
        else:
            self.send_response(500)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(f'<h2>Token exchange failed</h2><pre>{r.text[:500]}</pre>'.encode())
            print(f'FAILED: {r.status_code} {r.text[:300]}')

    def log_message(self, format, *args):
        pass  # quiet

if __name__ == '__main__':
    print(f'Listening on http://localhost:18790 ...')
    print(f'Waiting for OAuth callback...')
    server = HTTPServer(('0.0.0.0', 18790), CallbackHandler)
    while not got_token:
        server.handle_request()
    print('Done.')
