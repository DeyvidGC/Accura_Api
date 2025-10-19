"""Use cases for producing greeting messages."""

from app.domain.entities.greeting import Greeting


DEFAULT_GREETING = "Hello World"


def create_greeting(name: str | None = None) -> Greeting:
    """Return a greeting for the provided name.

    When no name is provided, a generic greeting is returned.
    """

    if name:
        message = f"Hello {name}"
    else:
        message = DEFAULT_GREETING

    return Greeting(message=message)
