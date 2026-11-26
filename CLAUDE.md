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
- Cost: about $15-20/month while up, $0 after deleting the stack.

## Steps

1. App + tests, run locally. **(next)**
2. CI workflow.
3. AWS CLI installed (not yet on the laptop), login profile for the personal account, budget alert.
4. CloudFormation stack.
5. CD workflow.
6. Caddy login + HTTPS, demo.
