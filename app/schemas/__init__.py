"""Reusable JSON Schemas for assistant responses."""
from __future__ import annotations

from importlib import resources
import json
from functools import lru_cache
from typing import Any


@lru_cache(maxsize=None)
def load_regla_de_campo_schema() -> dict[str, Any]:
    """Return the JSON schema that defines a 'Regla de Campo'."""
    with resources.files(__name__).joinpath("regla_de_campo.schema.json").open(
        "r", encoding="utf-8"
    ) as fp:
        return json.load(fp)
