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
@click.option("--clients-per-tick", default=3, type=int, help="Client arrivals per tick.")
@click.option("--policy", default="round_robin", show_default=True, type=click.Choice(sorted(POLICY_MAP.keys())), help="Load balancing policy.")
@click.option("--seed", default=0, type=int, help="Random seed for deterministic simulation.")
@click.option("--output-dir", default="output", show_default=True, type=click.Path(file_okay=False, path_type=Path), help="Directory to store simulation output.")
@click.option("--client-workload-mean", default=1.0, type=float, help="Mean client workload.")
@click.option("--client-workload-stddev", default=0.5, type=float, help="Standard deviation of client workload.")
def run(
    machines: int,
    ticks: int,
    clients_per_tick: int,
    policy: str,
    seed: int,
    output_dir: Path,
    client_workload_mean: float,
    client_workload_stddev: float,
) -> None:
    config = SimulationConfig(
        machines=machines,
        ticks=ticks,
        clients_per_tick=clients_per_tick,
        policy_name=policy,
        seed=seed,
        output_dir=str(output_dir),
        client_workload_mean=client_workload_mean,
        client_workload_stddev=client_workload_stddev,
    )
    result = Simulator(config).run()

    click.echo(json.dumps(result.summary, indent=2))
    click.echo(f"Outputs written to: {output_dir}")


@cli.command()
def list_policies() -> None:
    """List built-in policies."""
    click.echo("\n".join(sorted(POLICY_MAP.keys())))


if __name__ == "__main__":
    cli()
