import json
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

    summary = json.loads(summary_path.read_text())
    assert "patterns" in summary
    assert set(summary["patterns"]) == {
        "fairness",
        "failure_recovery",
        "spikes",
        "selection_distribution",
    }


def test_cli_analyze_reads_timeline_and_writes_report(tmp_path):
    runner = CliRunner()
    run_dir = tmp_path / "run"
    runner.invoke(
        cli,
        [
            "run",
            "--machines",
            "3",
            "--ticks",
            "5",
            "--clients-per-tick",
            "2",
            "--seed",
            "1",
            "--output-dir",
            str(run_dir),
        ],
    )

    analysis_path = tmp_path / "analysis.json"
    result = runner.invoke(
        cli,
        [
            "analyze",
            "--timeline",
            str(run_dir / "timeline.json"),
            "--output",
            str(analysis_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert analysis_path.exists()
    report = json.loads(analysis_path.read_text())
    assert set(report) == {
        "fairness",
        "failure_recovery",
        "spikes",
        "selection_distribution",
    }


def test_cli_stress_test_runs_multiple_seeds_and_writes_report(tmp_path):
    runner = CliRunner()
    output_dir = tmp_path / "stress"
    result = runner.invoke(
        cli,
        [
            "stress-test",
            "--policy",
            "least_connections",
            "--machines",
            "3",
            "--ticks",
            "10",
            "--runs",
            "3",
            "--failure-rate",
            "0.1",
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    report_path = output_dir / "stress_test.json"
    assert report_path.exists()
    report = json.loads(report_path.read_text())
    assert report["runs"] == 3
    assert len(report["per_run"]) == 3
