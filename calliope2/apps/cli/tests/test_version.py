from typer.testing import CliRunner

from calliope2_cli.__main__ import app


def test_version_command() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "calliope2-cli" in result.stdout
    assert "calliope2" in result.stdout
