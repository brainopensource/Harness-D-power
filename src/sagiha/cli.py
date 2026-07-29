"""SAGIHA command-line entry point.

Subcommands (run, replay, conformance, extensions) are added starting at S0 —
see docs/02-architecture/entry-points-and-piloting.md.
"""

import typer

app = typer.Typer(name="sagiha", help="SAGIHA — Super AGI Harness Agent")


@app.command()
def version() -> None:
    """Print the installed SAGIHA version."""
    from importlib.metadata import version as pkg_version

    typer.echo(pkg_version("sagiha"))


if __name__ == "__main__":
    app()
