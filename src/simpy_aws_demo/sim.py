"""Generic production line: jobs flow through fixed stations in order."""

import random

import simpy

# Station name -> mean process time in minutes. Fixed in code to keep the form small.
STATIONS = {"Cut": 4.0, "Assemble": 6.0, "Test": 3.0}


def run_line(
    machines: dict[str, int],
    arrivals_per_hour: float,
    hours: float,
    seed: int = 1,
) -> dict:
    """Run the line and return jobs finished, utilization and the bottleneck.

    machines: number of machines at each station, e.g. {"Cut": 1, "Assemble": 2, "Test": 1}.
    Process and arrival times are exponential, so results vary with the seed.
    """
    for name in STATIONS:
        if machines.get(name, 0) < 1:
            raise ValueError(f"{name} needs at least 1 machine")
    if arrivals_per_hour <= 0 or hours <= 0:
        raise ValueError("arrivals_per_hour and hours must be positive")

    rng = random.Random(seed)
    env = simpy.Environment()
    end = hours * 60  # minutes
    resources = {n: simpy.Resource(env, capacity=machines[n]) for n in STATIONS}
    busy = {n: 0.0 for n in STATIONS}  # machine-minutes spent working
    finished = 0

    def job():
        nonlocal finished
        for name, mean in STATIONS.items():
            with resources[name].request() as req:
                yield req
                t = rng.expovariate(1 / mean)
                busy[name] += min(t, end - env.now)  # only count time inside the run
                yield env.timeout(t)
        finished += 1

    def source():
        while True:
            yield env.timeout(rng.expovariate(arrivals_per_hour / 60))
            env.process(job())

    env.process(source())
    env.run(until=end)

    utilization = {n: round(busy[n] / (end * machines[n]), 3) for n in STATIONS}
    return {
        "jobs_finished": finished,
        "utilization": utilization,
        "bottleneck": max(utilization, key=utilization.get),
    }
