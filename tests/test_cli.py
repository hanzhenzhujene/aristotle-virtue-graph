from __future__ import annotations

from typer.testing import CliRunner

from aristotle_graph.cli import app


def test_sources_list_command_runs() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["sources", "list"])

    assert result.exit_code == 0
    assert "wikisource_ross_1908" in result.stdout
    assert "mit_archive_ross" in result.stdout
    assert "supported_books: 2, 3" in result.stdout


def test_annotations_validate_command_runs() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["annotations", "validate"])

    assert result.exit_code == 0
    assert '"mode": "candidate"' in result.stdout


def test_annotations_validate_strict_command_runs() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["annotations", "validate", "--strict-approved"])

    assert result.exit_code == 0
    assert '"mode": "strict_approved"' in result.stdout


def test_book3_annotations_validate_strict_command_runs() -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["annotations", "validate", "--book", "3", "--strict-approved"],
    )

    assert result.exit_code == 0
    assert '"book": 3' in result.stdout
    assert '"concept_count": 19' in result.stdout
    assert '"relation_count": 16' in result.stdout


def test_annotations_stats_command_runs() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["annotations", "stats"])

    assert result.exit_code == 0
    assert '"concept_count": 54' in result.stdout
