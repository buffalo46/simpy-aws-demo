#!/bin/bash
# Runs on the EC2 instance through SSM Run Command (sent by .github/workflows/cd.yml).
# The workflow puts IMAGE, SITE_NAME and AWS_REGION in front of this script.
set -euo pipefail
cloud-init status --wait >/dev/null || true # a new server may still be installing Docker
cd /opt/app

registry="${IMAGE%%/*}"
aws ecr get-login-password --region "$AWS_REGION" |
  docker login --username AWS --password-stdin "$registry"
docker pull "$IMAGE"

# The compose file and Caddyfile ship inside the image, so they match the code.
docker run --rm "$IMAGE" cat /app/deploy/compose.yml > compose.yml
docker run --rm "$IMAGE" cat /app/deploy/Caddyfile > Caddyfile

# The login password hash lives in SSM Parameter Store, never in the repo.
hash=$(aws ssm get-parameter --region "$AWS_REGION" --name /simpy-aws-demo/auth-hash \
  --with-decryption --query Parameter.Value --output text)
umask 077
{
  printf "IMAGE=%s\n" "$IMAGE"
  printf "SITE_NAME=%s\n" "$SITE_NAME"
  printf "AUTH_USER=demo\n"
  printf "AUTH_HASH='%s'\n" "$hash" # single quotes: compose keeps the $ signs as-is
} > .env

docker compose pull --quiet
docker compose up -d --remove-orphans
docker image prune -f
docker compose ps
