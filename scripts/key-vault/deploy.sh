#!/bin/bash
set -euo pipefail
REGION="${AWS_DEFAULT_REGION:-us-east-1}"
PASSPHRASE="${KEY_VAULT_PASSPHRASE:-daemon-squad}"

# Package
cd /tmp/key-vault
zip -q function.zip handler.py

# IAM role
ROLE_NAME="daemon-squad-key-vault"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

aws iam create-role --role-name "$ROLE_NAME" \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}' \
  --tags '[{"Key":"Purpose","Value":"daemon-squad"},{"Key":"TeardownNote","Value":"Key vault for Tailscale auth - delete after EC2 setup"}]' 2>/dev/null || echo "role exists"

aws iam attach-role-policy --role-name "$ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole 2>/dev/null || true

aws iam put-role-policy --role-name "$ROLE_NAME" --policy-name secrets-write \
  --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["secretsmanager:CreateSecret","secretsmanager:PutSecretValue"],"Resource":"*"}]}'

echo "Waiting 12s for role propagation..."
sleep 12

# Deploy Lambda
aws lambda create-function \
  --function-name daemon-squad-key-vault \
  --runtime python3.12 \
  --handler handler.handler \
  --role "$ROLE_ARN" \
  --zip-file fileb:///tmp/key-vault/function.zip \
  --environment "Variables={PASSPHRASE=${PASSPHRASE},SECRET_NAME=daemon-squad/tailscale-auth-key}" \
  --timeout 10 \
  --region "$REGION" \
  --tags "Purpose=daemon-squad,TeardownNote=delete after EC2 Tailscale auth complete" 2>/dev/null || \
aws lambda update-function-code \
  --function-name daemon-squad-key-vault \
  --zip-file fileb:///tmp/key-vault/function.zip \
  --region "$REGION"

# Function URL (no API Gateway needed)
aws lambda create-function-url-config \
  --function-name daemon-squad-key-vault \
  --auth-type NONE \
  --cors '{"AllowOrigins":["*"],"AllowMethods":["GET","POST"],"AllowHeaders":["content-type"]}' \
  --region "$REGION" 2>/dev/null || true

aws lambda add-permission \
  --function-name daemon-squad-key-vault \
  --action lambda:InvokeFunctionUrl \
  --principal "*" \
  --function-url-auth-type NONE \
  --statement-id FunctionURLPublic \
  --region "$REGION" 2>/dev/null || true

URL=$(aws lambda get-function-url-config \
  --function-name daemon-squad-key-vault \
  --region "$REGION" \
  --query FunctionUrl --output text)

echo ""
echo "✅ Key Vault live at: $URL"
echo "   Passphrase: $PASSPHRASE"
