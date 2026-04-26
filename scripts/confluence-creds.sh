#!/usr/bin/env bash
# confluence-creds.sh — Pull Confluence API creds from Windows Credential Manager
# Usage: eval "$(bash scripts/confluence-creds.sh)"
# Or source it: source <(bash scripts/confluence-creds.sh)
#
# Credentials are stored via Python keyring on Windows (service: claude-code)
# This script calls Windows Python to resolve them and exports as env vars.

set -euo pipefail

WIN_PYTHON="/mnt/c/Users/joelg/AppData/Local/Programs/Python/Python312/python.exe"

if [[ ! -x "$WIN_PYTHON" ]]; then
  echo "ERROR: Windows Python not found at $WIN_PYTHON" >&2
  exit 1
fi

# Pull credentials from Windows keyring via Python keyring module
CREDS=$("$WIN_PYTHON" -c "
import keyring, json, sys

service = 'claude-code'
creds = {}

# Confluence API token
token = keyring.get_password(service, 'wiki-lite/CONFLUENCE_API_TOKEN')
if token:
    creds['CONFLUENCE_API_TOKEN'] = token
else:
    print('WARN: CONFLUENCE_API_TOKEN not found in Windows keyring', file=sys.stderr)

# Username is in the .env, not credential store
creds['CONFLUENCE_USERNAME'] = 'joel_ginsberg@trendmicro.com'
creds['CONFLUENCE_URL'] = 'https://trendmicro.atlassian.net/wiki'

json.dump(creds, sys.stdout)
" 2>&1)

if [[ $? -ne 0 ]]; then
  echo "ERROR: Failed to retrieve credentials from Windows keyring" >&2
  echo "$CREDS" >&2
  exit 1
fi

# Parse JSON and emit export statements
python3 -c "
import json, sys, shlex
creds = json.loads(sys.argv[1])
for k, v in creds.items():
    print(f'export {k}={shlex.quote(v)}')
" "$CREDS"
