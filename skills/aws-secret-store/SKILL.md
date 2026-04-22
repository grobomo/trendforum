---
name: aws-secret-store
description: Store or update a secret in AWS Secrets Manager via the AWS CLI. Handles upsert automatically — creates if missing, updates if present. Requires AWS CLI authed (IAM role, env vars, or credentials file).
---
# AWS Secret Store
Upsert a secret to Secrets Manager via the bundled script.
## Usage
bash scripts/store-secret.sh <secret-name> <secret-value> [--region <region>]
## Behavior
1. put-secret-value (update) → if ResourceNotFoundException → create-secret
2. Prints ARN on success, error on failure
