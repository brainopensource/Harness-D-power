"""Util module."""


def greet(name: str) -> str:
    """Return a greeting."""
    return f"hello {name}"


class Greeter:
    def shout(self, name: str) -> str:
        return greet(name).upper()
