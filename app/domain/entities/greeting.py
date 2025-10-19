from dataclasses import dataclass


@dataclass(frozen=True)
class Greeting:
    """Represents the message returned by greeting endpoints."""

    message: str
