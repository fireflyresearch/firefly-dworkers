"""Tests for the firefly-dworkers CLI commands."""

from __future__ import annotations

from typer.testing import CliRunner

from firefly_dworkers_cli.app import app

runner = CliRunner()


class TestAppRegistration:
    """Verify that all expected subcommands are registered on the Typer app."""

    def test_init_command_registered(self) -> None:
        result = runner.invoke(app, ["init", "--help"])
        assert result.exit_code == 0
        assert "tenant-id" in result.output

    def test_serve_command_registered(self) -> None:
        result = runner.invoke(app, ["serve", "--help"])
        assert result.exit_code == 0
        assert "host" in result.output

    def test_install_command_registered(self) -> None:
        result = runner.invoke(app, ["install", "--help"])
        assert result.exit_code == 0
        assert "extra" in result.output.lower()

    def test_check_command_registered(self) -> None:
        result = runner.invoke(app, ["check", "--help"])
        assert result.exit_code == 0
        assert "environment" in result.output.lower() or "check" in result.output.lower()


class TestHelp:
    """Verify the top-level --help output."""

    def test_help_shows_description(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Firefly Dworkers" in result.output

    def test_help_lists_commands(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "init" in result.output
        assert "serve" in result.output
        assert "install" in result.output
        assert "check" in result.output


class TestCheck:
    """Verify the check command runs without error."""

    def test_check_runs_successfully(self) -> None:
        result = runner.invoke(app, ["check"])
        assert result.exit_code == 0
        assert "Environment Check" in result.output

    def test_check_shows_python_version(self) -> None:
        result = runner.invoke(app, ["check"])
        assert result.exit_code == 0
        assert "Python version" in result.output


class TestInitHelp:
    """Verify the init command help shows expected options."""

    def test_init_help_shows_tenant_id(self) -> None:
        result = runner.invoke(app, ["init", "--help"])
        assert result.exit_code == 0
        assert "--tenant-id" in result.output

    def test_init_help_shows_tenant_name(self) -> None:
        result = runner.invoke(app, ["init", "--help"])
        assert result.exit_code == 0
        assert "--tenant-name" in result.output

    def test_init_help_shows_output_dir(self) -> None:
        result = runner.invoke(app, ["init", "--help"])
        assert result.exit_code == 0
        assert "--output-dir" in result.output


class TestVersion:
    """Verify the --version flag."""

    def test_version_flag_shows_banner(self) -> None:
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "DWORKERS" in result.output or "Digital Workers" in result.output

    def test_no_args_shows_banner(self) -> None:
        result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "DWORKERS" in result.output or "Digital Workers" in result.output
