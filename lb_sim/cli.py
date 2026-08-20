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
@click.option(
    "--clients-per-tick",
    default=3,
    type=int,
    help="Default client arrivals per tick for constant behavior.",
)
@click.option(
    "--policy",
    default="round_robin",
    show_default=True,
    help="Load balancing policy name or experimental module path, e.g. least_connections or experimental.least_latency:LeastLatencyPolicy.",
)
@click.option(
    "--client-behavior",
    default="constant",
    show_default=True,
    type=click.Choice(
        ["constant", "linear", "exponential", "random"], case_sensitive=False
    ),
    help="Traffic pattern used to simulate client spikes.",
)
@click.option(
    "--seed", default=0, type=int, help="Random seed for deterministic simulation."
)
@click.option(
    "--failure-rate",
    default=0.0,
    type=float,
    help="per-instance probability of failure before each tick.",
)
@click.option(
    "--unhealthy-instances",
    default="",
    help="Comma-separated machine names to mark unhealthy from the start, e.g. machine-1,machine-2.",
)
@click.option(
    "--metrics-source",
    default=None,
    type=click.Path(exists=False, dir_okay=False, path_type=Path),
    help="Path to metrics JSON/CSV replay file to simulate or replay an incident from captured data.",
)
@click.option(
    "--metrics-format",
    default=None,
    type=str,
    help="Explicit metrics format name, e.g. json, csv, tsv, text, or a custom registered loader name.",
)
@click.option(
    "--output-dir",
    default="output",
    show_default=True,
    type=click.Path(file_okay=False, path_type=Path),
    help="Directory to store simulation output.",
)
@click.option(
    "--client-workload-mean", default=1.0, type=float, help="Mean client workload."
)
@click.option(
    "--client-workload-stddev",
    default=0.5,
    type=float,
    help="Standard deviation of client workload.",
)
def run(
    machines: int,
    ticks: int,
    clients_per_tick: int,
    policy: str,
    client_behavior: str,
    seed: int,
    failure_rate: float,
    unhealthy_instances: str,
    metrics_source: Path | None,
    metrics_format: str | None,
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
        metrics_source=str(metrics_source) if metrics_source else None,
        metrics_format=metrics_format.lower() if metrics_format else None,
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


@cli.command()
@click.option(
    "--metrics-source",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Metrics file to validate and replay.",
)
@click.option(
    "--metrics-format",
    default=None,
    type=str,
    help="Explicit metrics format name, e.g. json, csv, tsv, text, or a custom registered loader name.",
)
@click.option(
    "--policy",
    default="round_robin",
    show_default=True,
    help="Load balancing policy to use while replaying captured metrics.",
)
@click.option(
    "--output-dir",
    default="output",
    show_default=True,
    type=click.Path(file_okay=False, path_type=Path),
    help="Directory to store replay output.",
)
def replay(
    metrics_source: Path, metrics_format: str | None, policy: str, output_dir: Path
) -> None:
    """Validate and replay captured metrics as a timeline using the selected policy."""
    config = SimulationConfig(
        machines=1,
        ticks=1,
        policy_name=policy,
        metrics_source=str(metrics_source),
        metrics_format=metrics_format.lower() if metrics_format else None,
        output_dir=str(output_dir),
    )
    result = Simulator(config).run()
    click.echo(json.dumps(result.summary, indent=2))
    click.echo(f"Replay outputs written to: {output_dir}")


@cli.command()
@click.option(
    "--policy",
    "policies",
    multiple=True,
    default=("round_robin", "least_connections"),
    show_default=True,
    help="Policies to compare.",
)
@click.option("--machines", default=3, type=int, help="Number of backend instances.")
@click.option("--ticks", default=10, type=int, help="Simulation duration in ticks.")
@click.option(
    "--clients-per-tick", default=3, type=int, help="Client arrivals per tick."
)
@click.option(
    "--seed", default=0, type=int, help="Random seed for deterministic simulation."
)
def compare(
    policies: tuple[str, ...],
    machines: int,
    ticks: int,
    clients_per_tick: int,
    seed: int,
) -> None:
    """Compare multiple policies under the same scenario."""
    from .sim import compare_policies

    config = SimulationConfig(
        machines=machines, ticks=ticks, clients_per_tick=clients_per_tick, seed=seed
    )
    summary = compare_policies(policies, config=config)
    click.echo(json.dumps(summary, indent=2))


@cli.command()
@click.option(
    "--timeline",
    "timeline_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to a timeline.json file produced by a previous run or replay.",
)
@click.option(
    "--output",
    default=None,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Optional path to write the analysis report as JSON.",
)
def analyze(timeline_path: Path, output: Path | None) -> None:
    """Analyze a captured timeline for load fairness, failure-recovery, and spike-handling patterns."""
    from dataclasses import asdict

    from .analysis import analyze_run

    snapshots = json.loads(timeline_path.read_text())
    report = analyze_run(snapshots)
    rendered = json.dumps(asdict(report), indent=2)
    click.echo(rendered)
    if output:
        output.write_text(rendered)
        click.echo(f"Analysis written to: {output}")


@cli.command(name="stress-test")
@click.option(
    "--policy",
    default="round_robin",
    show_default=True,
    help="Load balancing policy name or experimental module path.",
)
@click.option("--machines", default=3, type=int, help="Number of backend instances.")
@click.option(
    "--ticks", default=50, type=int, help="Simulation duration in ticks per run."
)
@click.option(
    "--clients-per-tick", default=5, type=int, help="Client arrivals per tick."
)
@click.option(
    "--runs", default=20, type=int, help="Number of randomized runs (seeds) to execute."
)
@click.option(
    "--seed",
    default=0,
    type=int,
    help="Base random seed; each run uses seed + run index.",
)
@click.option(
    "--failure-rate",
    default=0.05,
    type=float,
    help="Per-instance probability of failure applied before each tick, enabling failure/recovery cycles.",
)
@click.option(
    "--client-behavior",
    default="random",
    show_default=True,
    type=click.Choice(
        ["constant", "linear", "exponential", "random"], case_sensitive=False
    ),
    help="Traffic pattern used to stress the policy.",
)
@click.option(
    "--client-workload-mean", default=1.0, type=float, help="Mean client workload."
)
@click.option(
    "--client-workload-stddev",
    default=0.5,
    type=float,
    help="Standard deviation of client workload.",
)
@click.option(
    "--output-dir",
    default="output",
    show_default=True,
    type=click.Path(file_okay=False, path_type=Path),
    help="Directory to store the full stress-test report.",
)
def stress_test(
    policy: str,
    machines: int,
    ticks: int,
    clients_per_tick: int,
    runs: int,
    seed: int,
    failure_rate: float,
    client_behavior: str,
    client_workload_mean: float,
    client_workload_stddev: float,
    output_dir: Path,
) -> None:
    """Run a policy across many randomized seeds and report aggregate fairness/failure/spike statistics."""
    from .sim import stress_test_policy

    report = stress_test_policy(
        policy,
        machines=machines,
        ticks=ticks,
        clients_per_tick=clients_per_tick,
        runs=runs,
        seed=seed,
        failure_rate=failure_rate,
        client_behavior=client_behavior.lower(),
        client_workload_mean=client_workload_mean,
        client_workload_stddev=client_workload_stddev,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "stress_test.json").write_text(json.dumps(report, indent=2))
    click.echo(json.dumps(report["aggregate"], indent=2))
    click.echo(f"Full stress-test report written to: {output_dir / 'stress_test.json'}")


if __name__ == "__main__":
    cli()
