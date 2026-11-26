import fakeredis
import pytest

from simpy_aws_demo.app import create_app

FORM = {
    "machines_Cut": "1",
    "machines_Assemble": "2",
    "machines_Test": "1",
    "arrivals_per_hour": "8",
    "hours": "40",
}


@pytest.fixture
def client():
    # Fake Redis + synchronous queue: the job runs right away, no worker needed.
    app = create_app({"REDIS_CONN": fakeredis.FakeRedis(), "RQ_ASYNC": False})
    return app.test_client()


def test_form_page(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"Assemble machines" in r.data


def test_run_shows_result(client):
    r = client.post("/run", data=FORM, follow_redirects=True)
    assert r.status_code == 200
    assert b"jobs finished" in r.data
    assert b"Bottleneck" in r.data


def test_bad_input_rejected(client):
    r = client.post("/run", data={**FORM, "machines_Test": "0"})
    assert r.status_code == 400
    assert b"between 1 and 20" in r.data


def test_unknown_job_404(client):
    assert client.get("/jobs/nope").status_code == 404
