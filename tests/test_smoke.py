from typer.testing import CliRunner

from lexo import __version__
from lexo.cli.app import app

runner = CliRunner()


def test_version_constant() -> None:
    assert __version__


def test_cli_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "lexo" in result.stdout


def test_cli_info() -> None:
    result = runner.invoke(app, ["info"])
    assert result.exit_code == 0
    assert "data dir" in result.stdout
