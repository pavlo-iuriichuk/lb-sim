from pathlib import Path

from click.testing import CliRunner

from lb_sim.cli import cli


def test_cli_runs_smoke_simulation(tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "run",
            "--machines",
            "3",
            "--ticks",
            "5",
            "--clients-per-tick",
            "2",
            "--policy",
            "round_robin",
            "--seed",
            "42",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0, result.output
    summary_path = tmp_path / "summary.json"
    assert summary_path.exists()
    assert (tmp_path / "connections_timeline.png").exists()
    assert (tmp_path / "load_timeline.png").exists()
