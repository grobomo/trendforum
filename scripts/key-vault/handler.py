import json, os, base64
from urllib.parse import unquote_plus
import boto3

PASSPHRASE = os.environ.get('PASSPHRASE', 'daemon-squad')
SECRET_NAME = os.environ.get('SECRET_NAME', 'daemon-squad/tailscale-auth-key')

HTML = """\
<html><body style="font-family:sans-serif;max-width:500px;margin:40px auto">
<h2>🔐 Daemon Squad Key Vault</h2>
<p>Stores to Secrets Manager: {sn}</p>
<form method=POST>
  <label>Passphrase</label><br>
  <input name=p type=password style="width:100%;margin:4px 0 12px"><br>
  <label>Secret value</label><br>
  <textarea name=s rows=4 style="width:100%"></textarea><br><br>
  <button type=submit>Store → AWS</button>
</form>
{status}
</body></html>""".format(sn=SECRET_NAME, status="{status}")

def handler(event, context):
    method = (event.get('requestContext') or {}).get('http', {}).get('method', 'GET')
    if method == 'GET':
        return resp(HTML.replace('{status}', ''))

    body = event.get('body', '')
    if event.get('isBase64Encoded'):
        body = base64.b64decode(body).decode()
    params = {k: unquote_plus(v) for k, v in (p.split('=',1) for p in body.split('&') if '=' in p)}
    pp, secret = params.get('p',''), params.get('s','')

    if pp != PASSPHRASE:
        return resp(HTML.replace('{status}', '<p style="color:red">❌ Wrong passphrase</p>'))
    if not secret.strip():
        return resp(HTML.replace('{status}', '<p style="color:red">❌ Secret is empty</p>'))

    try:
        sm = boto3.client('secretsmanager')
        try:
            sm.put_secret_value(SecretId=SECRET_NAME, SecretString=secret.strip())
        except sm.exceptions.ResourceNotFoundException:
            sm.create_secret(Name=SECRET_NAME, SecretString=secret.strip(),
                             Tags=[{'Key':'Purpose','Value':'daemon-squad'},
                                   {'Key':'TeardownNote','Value':'Tailscale auth key - delete after EC2 setup'}])
        return resp(HTML.replace('{status}', f'<p style="color:green">✓ Stored at {SECRET_NAME}</p>'))
    except Exception as e:
        return resp(HTML.replace('{status}', f'<p style="color:red">❌ {e}</p>'))

def resp(body):
    return {'statusCode':200,'headers':{'Content-Type':'text/html'},'body':body}
