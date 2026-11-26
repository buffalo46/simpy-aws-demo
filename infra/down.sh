#!/bin/bash
# Delete the whole AWS stack (server, IP, disk, images, roles). Cost goes to $0.
# The login password hash in SSM Parameter Store is kept (free) for the next up.sh.
# Usage: bash infra/down.sh
set -euo pipefail
export MSYS_NO_PATHCONV=1

STACK=simpy-aws-demo
REGION=us-east-1
PROFILE=${AWS_PROFILE:-demo}

if command -v aws >/dev/null; then AWS_BIN=aws
elif command -v aws.cmd >/dev/null; then AWS_BIN=aws.cmd
else AWS_BIN="$HOME/.local/bin/aws.cmd"; fi
awsc() { "$AWS_BIN" --profile "$PROFILE" --region "$REGION" "$@"; }

read -r -p "Delete stack $STACK and everything in it? Type 'delete' to confirm: " answer
[ "$answer" = delete ] || { echo "Cancelled."; exit 1; }

awsc cloudformation delete-stack --stack-name "$STACK"
echo "Deleting (about 5 minutes)..."
awsc cloudformation wait stack-delete-complete --stack-name "$STACK"
echo "Down: stack $STACK deleted. Run  bash infra/up.sh  to bring it back."
