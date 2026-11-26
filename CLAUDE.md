# CLAUDE.md

Public demo repo (github.com/buffalo46/simpy-aws-demo, Shiro's personal GitHub account) that shows a SimPy web app hosted on Shiro's personal AWS account with CI/CD. It is a stand-in for the company app (VulcanForms ae-factory-flow-sim-app), so it uses the same shape: Flask web app, Redis queue (RQ), separate worker.

## Rules

- **Keep it generic.** No company names, layouts, numbers or code copied from the company repo. Only a made-up demo factory.
- **Work step by step.** Propose one small step, explain it, give Shiro the commands to run, then check the result together. Shiro runs the commands (git, gh, aws, uv) themselves.
- **Plain English** when Shiro asks for it: one plain line per option, name each term once, say your pick.
- Shiro's token budget is limited: narrow reads, few agents, cheap checks.
- Run Python through uv (`uv run ...`). Claude's shell may not have `uv` on PATH: use `python -m uv run ...` there.
- Two GitHub accounts on this laptop: **buffalo46** (this repo) and **sushijima-vf** (work). git pushes with the active one: `gh auth switch --user buffalo46` before pushing here. Commit email for this repo is buffalo46's noreply address (set in this repo's git config only).
- Never commit secrets (Caddy password hashes go in AWS, not the repo). No AWS access keys anywhere: GitHub Actions uses OIDC.

## Design (agreed 2026-11-25)

- **App (changed 2026-11-25):** a generic production line. Jobs arrive and pass through 3 fixed stations in order (Cut → Assemble → Test), each with N machines and an average process time. A web page takes machines per station, arrival rate and hours to simulate; Run queues a job; the worker runs SimPy; the page shows jobs finished, utilization per station and the bottleneck.
- **Local:** `uv run flask run` + `uv run rq worker` (or a `flask worker` command), Redis in WSL. Docker is not installed on the laptop: GitHub Actions builds the images.
- **AWS:** one EC2 instance (x86, t3.small, so GitHub's normal runners build the image without cross-building) with Docker Compose: caddy (HTTPS + password login), web, redis, worker. Elastic IP; HTTPS on a free `<ip>.sslip.io` name via Let's Encrypt; security group 443 from allowed IPs, 80 open for the cert check, 22 closed; admin through SSM Session Manager; ECR for images; budget alert. All AWS pieces in one CloudFormation template in the repo, so one command creates and one deletes everything.
- **CI/CD (GitHub Actions):** on push: pytest + ruff. On merge to main: build image, push to ECR, deploy by SSM send-command (`docker compose pull && docker compose up -d`). AWS login by GitHub OIDC role, limited to this repo's main branch, ECR push and SSM on this instance.
- Cost: about $21/month while up (EC2 $15, Elastic IP $3.65, disk $1.60; see README), $0 after deleting the stack.

## Steps

1. App + tests, run locally. Done 2026-11-25 (Flask on Windows, `flask worker`, Redis in WSL; keep a WSL terminal open or WSL stops Redis).
2. CI workflow. Done 2026-11-25 (`.github/workflows/ci.yml`, green).
3. AWS CLI installed, login profile for the personal account. Done 2026-11-25: CLI v2 unpacked to the user folder (no admin rights on the laptop); IAM user `shiro-admin` (console password, AdministratorAccess, no access keys); `aws login --profile demo` (us-east-1, 12-hour sessions). No Identity Center: it would end the free plan and its credits. No budget alert (Shiro's choice).
4. CloudFormation stack. Done 2026-11-25: `infra/stack.yml`, stack `simpy-aws-demo` in us-east-1. Deploy/update: `aws cloudformation deploy --template-file infra/stack.yml --stack-name simpy-aws-demo --capabilities CAPABILITY_IAM --parameter-overrides AllowedCidr=<home ip>/32 --profile demo --region us-east-1`. Delete: `aws cloudformation delete-stack --stack-name simpy-aws-demo --profile demo --region us-east-1`. Scripts (2026-11-26): `bash infra/up.sh` (deploy stack, set repo variables, run CD; a new stack means a new IP and site name) and `bash infra/down.sh` (delete; keeps the SSM password hash). Outputs give instance ID, Elastic IP, sslip.io name, ECR URI, GitHub deploy role ARN (`aws cloudformation describe-stacks --stack-name simpy-aws-demo --profile demo --region us-east-1`).
5. CD workflow. Done 2026-11-26: `.github/workflows/cd.yml` runs after CI passes on main (or by hand: `gh workflow run CD`). Repo variables AWS_ROLE_ARN, INSTANCE_ID, SITE_NAME. The repo uses GitHub's immutable OIDC subject (`repo:buffalo46@25193094/simpy-aws-demo@1472622232:...`), so the stack's GitHubRepo parameter uses that form.
6. Caddy login + HTTPS. Done 2026-11-26: https://34.203.120.233.sslip.io, user `demo`. The bcrypt hash is in SSM Parameter Store `/simpy-aws-demo/auth-hash`; `deploy/remote-deploy.sh` writes it to `/opt/app/.env` on the instance. Compose file and Caddyfile ship inside the image.
