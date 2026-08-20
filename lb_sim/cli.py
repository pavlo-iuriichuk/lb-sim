from __future__ import annotations

import json
from pathlib import Path

import click

from .sim import POLICY_MAP, SimulationConfig, Simulator


@click.group()
def cli() -> None:
    """Stochastic simulator for load balancer policies."""


@cli.command()
@click.option("--machines", default=3, type=int, help="Number of backend instances.")
@click.option("--ticks", default=10, type=int, help="Simulation duration in ticks.")
@click.option("--clients-per-tick", default=3, type=int, help="Default client arrivals per tick for constant behavior.")
@click.option("--policy", default="round_robin", show_default=True, help="Load balancing policy name or experimental module path, e.g. least_connections or experimental.least_latency:LeastLatencyPolicy.")
@click.option("--client-behavior", default="constant", show_default=True, type=click.Choice(["constant", "linear", "exponential", "random"], case_sensitive=False), help="Traffic pattern used to simulate client spikes.")
@click.option("--seed", default=0, type=int, help="Random seed for deterministic simulation.")
@click.option("--failure-rate", default=0.0, type=float, help="per-instance probability of failure before each tick.")
@click.option("--unhealthy-instances", default="", help="Comma-separated machine names to mark unhealthy from the start, e.g. machine-1,machine-2.")
@click.option("--output-dir", default="output", show_default=True, type=click.Path(file_okay=False, path_type=Path), help="Directory to store simulation output.")
@click.option("--client-workload-mean", default=1.0, type=float, help="Mean client workload.")
@click.option("--client-workload-stddev", default=0.5, type=float, help="Standard deviation of client workload.")
def run(
    machines: int,
    ticks: int,
    clients_per_tick: int,
    policy: str,
    client_behavior: str,
    seed: int,
    failure_rate: float,
    unhealthy_instances: str,
    output_dir: Path,
    client_workload_mean: float,
    client_workload_stddev: float,
) -> None:
    config = SimulationConfig(
        machines=machines,
        ticks=ticks,
        clients_per_tick=clients_per_tick,
        policy_name=policy,
        client_behavior=client_behavior.lower(),
        seed=seed,
        failure_rate=failure_rate,
        unhealthy_instances=unhealthy_instances,
        output_dir=str(output_dir),
        client_workload_mean=client_workload_mean,
        client_workload_stddev=client_workload_stddev,
    )
    result = Simulator(config).run()

    click.echo(json.dumps(result.summary, indent=2))
    click.echo(f"Outputs written to: {output_dir}")


@cli.command()
def list_policies() -> None:
    """List built-in and experimental policies."""
    policies = sorted(POLICY_MAP.keys())
    click.echo("\n".join(policies))


if __name__ == "__main__":
    cli()
