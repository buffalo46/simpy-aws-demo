import pytest

from simpy_aws_demo.sim import STATIONS, run_line

ONE_EACH = {n: 1 for n in STATIONS}


def test_same_seed_same_result():
    assert run_line(ONE_EACH, 6, 8) == run_line(ONE_EACH, 6, 8)


def test_utilization_between_0_and_1():
    result = run_line(ONE_EACH, 8, 40)
    assert all(0 <= u <= 1 for u in result["utilization"].values())


def test_slowest_station_is_bottleneck():
    # Assemble has the longest process time, so with 1 machine each it is the bottleneck.
    assert run_line(ONE_EACH, 8, 200)["bottleneck"] == "Assemble"


def test_more_machines_more_jobs_when_overloaded():
    # 15 jobs/hour is more than one Assemble machine can handle (10/hour).
    base = run_line(ONE_EACH, 15, 40)["jobs_finished"]
    more = run_line({**ONE_EACH, "Assemble": 2, "Cut": 2}, 15, 40)["jobs_finished"]
    assert more > base


def test_rejects_zero_machines():
    with pytest.raises(ValueError):
        run_line({**ONE_EACH, "Test": 0}, 6, 8)
