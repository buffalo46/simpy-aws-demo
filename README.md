# simpy-aws-demo

A small SimPy web app hosted on AWS with CI/CD. It simulates a made-up production line: jobs arrive and pass through three stations in order (Cut → Assemble → Test), each with N machines. On the web page you set machines per station, arrival rate and hours to simulate, press Run, and get jobs finished, utilization per station and the bottleneck.

The app is a Flask web page plus a Redis job queue (RQ) and a separate worker that runs the simulation, so long runs never block the page.

## Architecture

![Architecture diagram](docs/architecture.svg)

**Running a simulation**

1. A viewer opens `https://<ip>.sslip.io`. The security group only lets in port 443 from allowed IPs.
2. Caddy handles HTTPS, asks for a password and passes the request to the Flask web app.
3. Pressing Run puts a job on the Redis queue.
4. The worker takes the job, runs the SimPy model and saves the results to Redis for the page to show.
5. Let's Encrypt checks the site over port 80, and Caddy gets and renews the certificate on its own.

**Shipping a change**

6. Every push runs CI on GitHub Actions (ruff + pytest).
7. On merge to main, Actions gets a one-hour AWS login from the deploy role through OIDC. No AWS keys are stored anywhere, and only this repo's main branch can use the role.
8. Actions builds the Docker image and pushes it to ECR.
9. Actions sends an SSM Run Command to the instance: `docker compose pull && docker compose up -d`.
10. The instance pulls the new image from ECR and restarts the containers.

## AWS services and cost

All AWS resources are in one CloudFormation template, [`infra/stack.yml`](infra/stack.yml), in us-east-1.

| Service | What it does here | Est. cost / month |
|---|---|---|
| EC2 (t3.small, x86) | One server running Docker Compose: caddy, web, redis, worker. x86 so GitHub's normal runners build the image without cross-building. | $15.18 |
| EBS (20 GB gp3, encrypted) | The server's disk | $1.60 |
| Elastic IP | Fixed public address, so the `<ip>.sslip.io` name and HTTPS certificate stay valid | $3.65 |
| ECR | Private Docker image repository. Keeps the last 10 images and scans each push. | under $0.50 |
| IAM | GitHub OIDC login + deploy role (push images, send deploy commands to this one instance); instance role (SSM + read images) | $0 |
| Systems Manager | Run Command for deploys; Session Manager for an admin shell, so SSH (port 22) stays closed | $0 |
| CloudFormation | Creates and deletes everything above with one command | $0 |
| VPC + security group | Default VPC; 443 from allowed IPs, 80 open for the certificate check | $0 |
| **Total** | | **about $21** |

Outside AWS (all free): GitHub Actions for CI/CD, Let's Encrypt for the certificate, and [sslip.io](https://sslip.io) for a DNS name that points at the IP, so no domain has to be bought.

Costs are us-east-1 on-demand list prices for a server running all month (730 hours). Data out is covered by the 100 GB/month free allowance. Deleting the stack brings the cost to $0.

## Run locally

Needs [uv](https://docs.astral.sh/uv/) and a Redis server on `localhost:6379` (or set `REDIS_URL`).

```sh
uv run flask --app simpy_aws_demo.app run      # web page on http://127.0.0.1:5000
uv run flask --app simpy_aws_demo.app worker   # in a second terminal
uv run pytest
uv run ruff check
```

## Create and delete the AWS stack

```sh
aws cloudformation deploy --template-file infra/stack.yml --stack-name simpy-aws-demo \
  --capabilities CAPABILITY_IAM --parameter-overrides AllowedCidr=<your ip>/32

aws cloudformation delete-stack --stack-name simpy-aws-demo
```

`aws cloudformation describe-stacks --stack-name simpy-aws-demo` shows the instance ID, IP, site name, ECR URI and deploy role ARN.
