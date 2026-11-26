"""Flask web app: a form queues a simulation job on Redis (RQ); a worker runs it."""

import os

from flask import Flask, abort, redirect, render_template, request, url_for
from redis import Redis
from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Job

from simpy_aws_demo.sim import STATIONS, run_line

DEFAULTS = {"machines": {n: 1 for n in STATIONS}, "arrivals_per_hour": 8, "hours": 40}


def parse_form(form) -> dict:
    """Read and check the form. Raises ValueError with a message for the page."""
    try:
        machines = {n: int(form[f"machines_{n}"]) for n in STATIONS}
        arrivals = float(form["arrivals_per_hour"])
        hours = float(form["hours"])
    except (KeyError, ValueError):
        raise ValueError("Please fill in every field with a number.") from None
    if not all(1 <= m <= 20 for m in machines.values()):
        raise ValueError("Machines per station must be between 1 and 20.")
    if not 0 < arrivals <= 100:
        raise ValueError("Arrivals per hour must be between 0 and 100.")
    if not 0 < hours <= 1000:
        raise ValueError("Hours must be between 0 and 1000.")
    return {"machines": machines, "arrivals_per_hour": arrivals, "hours": hours}


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config["REDIS_URL"] = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    if test_config:
        app.config.update(test_config)

    conn = app.config.get("REDIS_CONN") or Redis.from_url(app.config["REDIS_URL"])
    queue = Queue("sim", connection=conn, is_async=app.config.get("RQ_ASYNC", True))

    @app.get("/")
    def index():
        return render_template(
            "index.html", stations=STATIONS, values=DEFAULTS, error=None
        )

    @app.post("/run")
    def run():
        try:
            params = parse_form(request.form)
        except ValueError as e:
            return render_template(
                "index.html", stations=STATIONS, values=DEFAULTS, error=str(e)
            ), 400
        job = queue.enqueue(run_line, **params, result_ttl=3600, job_timeout=120)
        return redirect(url_for("job_page", job_id=job.id))

    @app.get("/jobs/<job_id>")
    def job_page(job_id):
        try:
            job = Job.fetch(job_id, connection=conn)
        except NoSuchJobError:
            abort(404)
        return render_template(
            "job.html",
            job=job,
            status=job.get_status(),
            result=job.return_value() if job.is_finished else None,
        )

    @app.cli.command("worker")
    def worker():
        """Run an RQ worker for the sim queue (flask worker)."""
        if os.name == "nt":
            # Windows has no fork or SIGALRM: run jobs in-process with a timer timeout.
            from rq.timeouts import TimerDeathPenalty
            from rq.worker import SimpleWorker

            class WindowsWorker(SimpleWorker):
                death_penalty_class = TimerDeathPenalty

            WindowsWorker([queue], connection=conn).work()
        else:
            from rq import Worker

            Worker([queue], connection=conn).work()

    return app
