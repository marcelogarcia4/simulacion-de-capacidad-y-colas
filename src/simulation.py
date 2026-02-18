from __future__ import annotations

from dataclasses import dataclass
import csv
import heapq
import json
import math
import random
from pathlib import Path
from typing import Iterable


@dataclass
class SimulationConfig:
    hours: int = 12
    max_queue: int = 12
    mean_service_minutes: float = 22.0
    price_per_service: float = 18.0
    server_cost_per_hour: float = 11.5
    seed: int = 42


DEFAULT_ARRIVAL_PROFILE = [10, 13, 18, 22, 26, 24, 23, 20, 18, 16, 14, 11]


def sample_poisson(lam: float, rng: random.Random) -> int:
    l = math.exp(-lam)
    k = 0
    p = 1.0
    while p > l:
        k += 1
        p *= rng.random()
    return k - 1


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * p
    low = math.floor(index)
    high = math.ceil(index)
    if low == high:
        return ordered[int(index)]
    return ordered[low] * (high - index) + ordered[high] * (index - low)


def generate_arrivals(arrival_rates_by_hour: Iterable[float], rng: random.Random) -> list[float]:
    arrivals: list[float] = []
    for hour, rate in enumerate(arrival_rates_by_hour):
        count = sample_poisson(float(rate), rng)
        for _ in range(max(0, count)):
            arrivals.append(hour * 3600.0 + rng.random() * 3600.0)
    arrivals.sort()
    return arrivals


def run_queue_simulation(
    servers: int,
    arrival_rates_by_hour: Iterable[float] = DEFAULT_ARRIVAL_PROFILE,
    config: SimulationConfig = SimulationConfig(),
) -> dict:
    rng = random.Random(config.seed + servers)
    arrivals = generate_arrivals(arrival_rates_by_hour, rng)

    server_available_at = [0.0 for _ in range(servers)]
    waits_minutes: list[float] = []
    served = 0
    rejected = 0
    customers_in_system: list[float] = []
    total_busy_inside_horizon = 0.0
    horizon = config.hours * 3600.0

    for arrival_time in arrivals:
        while customers_in_system and customers_in_system[0] <= arrival_time:
            heapq.heappop(customers_in_system)

        if len(customers_in_system) >= (servers + config.max_queue):
            rejected += 1
            continue

        next_server = min(range(servers), key=lambda i: server_available_at[i])
        service_start = max(arrival_time, server_available_at[next_server])
        wait_minutes = (service_start - arrival_time) / 60.0
        service_minutes = rng.expovariate(1.0 / config.mean_service_minutes)
        service_end = service_start + service_minutes * 60.0

        server_available_at[next_server] = service_end
        heapq.heappush(customers_in_system, service_end)

        overlap_start = min(max(0.0, service_start), horizon)
        overlap_end = min(max(0.0, service_end), horizon)
        total_busy_inside_horizon += max(0.0, overlap_end - overlap_start)

        waits_minutes.append(wait_minutes)
        served += 1

    total_arrivals = len(arrivals)
    rejection_rate = (rejected / total_arrivals) if total_arrivals else 0.0
    avg_wait = (sum(waits_minutes) / len(waits_minutes)) if waits_minutes else 0.0
    p90_wait = percentile(waits_minutes, 0.90)
    total_time_seconds = config.hours * 3600.0
    utilization = total_busy_inside_horizon / (servers * total_time_seconds) if servers > 0 else 0.0

    revenue = served * config.price_per_service
    costs = servers * config.server_cost_per_hour * config.hours
    net_margin = revenue - costs

    return {
        "servers": servers,
        "arrivals": total_arrivals,
        "served": served,
        "rejected": rejected,
        "rejection_rate": rejection_rate,
        "avg_wait_minutes": avg_wait,
        "p90_wait_minutes": p90_wait,
        "utilization": utilization,
        "revenue_usd": revenue,
        "cost_usd": costs,
        "net_margin_usd": net_margin,
    }


def evaluate_capacities(
    capacities: Iterable[int],
    arrival_rates_by_hour: Iterable[float] = DEFAULT_ARRIVAL_PROFILE,
    config: SimulationConfig = SimulationConfig(),
) -> list[dict]:
    return [run_queue_simulation(cap, arrival_rates_by_hour, config) for cap in capacities]


def recommend_capacity(results: list[dict], max_avg_wait: float = 10.0, max_rejection_rate: float = 0.05) -> dict:
    feasible = [
        row for row in results if row["avg_wait_minutes"] <= max_avg_wait and row["rejection_rate"] <= max_rejection_rate
    ]
    if not feasible:
        return sorted(results, key=lambda x: x["avg_wait_minutes"])[0]
    return sorted(feasible, key=lambda x: (x["net_margin_usd"], -x["avg_wait_minutes"]), reverse=True)[0]


def write_csv(results: list[dict], path: Path) -> None:
    if not results:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)


def write_json(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
