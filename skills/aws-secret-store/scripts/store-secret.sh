#!/usr/bin/env bash
set -euo pipefail
REGION="us-east-1"
[ $# -lt 2 ] && echo "Usage: $0 <name> <value> [--region r]" >&2 && exit 1
SECRET_NAME="$1"; SECRET_VALUE="$2"; shift 2
while [[ $# -gt 0 ]]; do
  case "$1" in --region) REGION="$2"; shift 2;; *) exit 1;; esac
done
if aws secretsmanager put-secret-value --region "$REGION" \
   --secret-id "$SECRET_NAME" --secret-string "$SECRET_VALUE" \
   --output json 2>/tmp/sm-err.json; then
  ARN=$(aws secretsmanager describe-secret --region "$REGION" \
    --secret-id "$SECRET_NAME" --query ARN --output text)
  echo "✅ Updated: $SECRET_NAME — $ARN"; exit 0
fi
if grep -q "ResourceNotFoundException" /tmp/sm-err.json 2>/dev/null; then
  RESULT=$(aws secretsmanager create-secret --region "$REGION" \
    --name "$SECRET_NAME" --secret-string "$SECRET_VALUE" --output json)
  ARN=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['ARN'])")
  echo "✅ Created: $SECRET_NAME — $ARN"; exit 0
fi
echo "❌ Failed" >&2; cat /tmp/sm-err.json >&2; exit 1
