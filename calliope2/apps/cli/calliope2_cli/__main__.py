import typer

from calliope2 import __version__ as core_version
from calliope2_cli import __version__ as cli_version

app = typer.Typer(help="Operational CLI for Calliope v2.", no_args_is_help=True)


@app.callback()
def _root() -> None:
    """Calliope v2 operational CLI."""


@app.command()
def version() -> None:
    """Print the CLI and core package versions."""
    typer.echo(f"calliope2-cli {cli_version} (core: calliope2 {core_version})")


if __name__ == "__main__":
    app()
