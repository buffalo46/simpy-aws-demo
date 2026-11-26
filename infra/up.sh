#!/bin/bash
# Create (or update) the AWS stack, point GitHub Actions at it, and deploy the app.
# Usage: bash infra/up.sh [allowed-ip]    (default: this machine's public IP)
# Needs: aws CLI logged in (aws login --profile demo), gh logged in as the repo owner.
set -euo pipefail
cd "$(dirname "$0")/.."
export MSYS_NO_PATHCONV=1 # Git Bash: keep /simpy-aws-demo/... as-is

STACK=simpy-aws-demo
REGION=us-east-1
PROFILE=${AWS_PROFILE:-demo}
PARAM=/simpy-aws-demo/auth-hash

if command -v aws >/dev/null; then AWS_BIN=aws
elif command -v aws.cmd >/dev/null; then AWS_BIN=aws.cmd
else AWS_BIN="$HOME/.local/bin/aws.cmd"; fi
awsc() { "$AWS_BIN" --profile "$PROFILE" --region "$REGION" "$@" | tr -d '\r'; }
output() {
  awsc cloudformation describe-stacks --stack-name "$STACK" \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text
}

echo "== Checks"
awsc sts get-caller-identity --query Account --output text >/dev/null ||
  { echo "AWS login expired: run  aws login --profile $PROFILE"; exit 1; }
if ! awsc ssm get-parameter --name "$PARAM" --query Parameter.Name --output text >/dev/null 2>&1; then
  echo "No login password hash in SSM ($PARAM). Create it once:"
  echo "  python -m uv run --with bcrypt python -c \"import bcrypt,getpass;print(bcrypt.hashpw(getpass.getpass().encode(),bcrypt.gensalt()).decode())\""
  echo "  aws ssm put-parameter --name $PARAM --type SecureString --value '<hash>' --profile $PROFILE --region $REGION"
  exit 1
fi
ip=${1:-$(curl -fsS https://checkip.amazonaws.com | tr -d '\r\n')}
echo "Allowed IP: $ip"

echo "== Stack (about 5 minutes when new)"
awsc cloudformation deploy --template-file infra/stack.yml --stack-name "$STACK" \
  --capabilities CAPABILITY_IAM --no-fail-on-empty-changeset \
  --parameter-overrides "AllowedCidr=$ip/32"

instance=$(output InstanceId)
site=$(output SiteName)
role=$(output GitHubDeployRoleArn)

echo "== Waiting for the server to check in with SSM"
for _ in $(seq 60); do
  ping=$(awsc ssm describe-instance-information --filters "Key=InstanceIds,Values=$instance" \
    --query "InstanceInformationList[0].PingStatus" --output text)
  [ "$ping" = Online ] && break
  sleep 10
done
[ "$ping" = Online ] || { echo "Instance $instance is not online in SSM"; exit 1; }

echo "== GitHub repo variables"
gh variable set AWS_ROLE_ARN --body "$role"
gh variable set INSTANCE_ID --body "$instance"
gh variable set SITE_NAME --body "$site"

echo "== Deploy (CD workflow)"
gh workflow run CD --ref main
sleep 10
run=$(gh run list --workflow CD --limit 1 --json databaseId -q '.[0].databaseId')
gh run watch "$run" --exit-status --interval 15 >/dev/null ||
  { echo "Deploy failed: gh run view $run --log-failed"; exit 1; }

echo
echo "Up: https://$site  (user: demo)"
