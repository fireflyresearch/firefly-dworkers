"""Tests for CLI flag parsing."""
from __future__ import annotations


class TestCLIFlags:
    def test_resume_option_exists(self):
        from firefly_dworkers_cli.app import app
        from typer.testing import CliRunner
        runner = CliRunner()
        result = runner.invoke(app, ["--help"])
        assert "--resume" in result.output or "-r" in result.output

    def test_project_option_exists(self):
        from firefly_dworkers_cli.app import app
        from typer.testing import CliRunner
        runner = CliRunner()
        result = runner.invoke(app, ["--help"])
        assert "--project" in result.output or "-p" in result.output
