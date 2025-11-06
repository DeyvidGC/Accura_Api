"""Validation helpers for rule use cases."""

from typing import Any

from app.infrastructure.repositories import RuleRepository


def _collect_rule_names(rule_data: Any, names: list[str]) -> None:
    from collections.abc import Mapping, Sequence as Seq

    if isinstance(rule_data, Mapping):
        raw_name = rule_data.get("Nombre de la regla")
        if isinstance(raw_name, str):
            stripped = raw_name.strip()
            if stripped:
                names.append(stripped)
        for value in rule_data.values():
            _collect_rule_names(value, names)
        return

    if isinstance(rule_data, Seq) and not isinstance(rule_data, (str, bytes)):
        for entry in rule_data:
            _collect_rule_names(entry, names)


def gather_rule_names(rule_data: Any) -> list[str]:
    """Return a list of unique, normalized rule names found in ``rule_data``."""

    collected: list[str] = []
    _collect_rule_names(rule_data, collected)

    unique_names: list[str] = []
    seen: set[str] = set()
    for name in collected:
        normalized = name.lower()
        if normalized not in seen:
            seen.add(normalized)
            unique_names.append(name)
    return unique_names


def ensure_unique_rule_names(
    rule_data: Any,
    repository: RuleRepository,
    *,
    exclude_rule_id: int | None = None,
) -> None:
    """Validate that the provided rule names are not already registered."""

    rule_names = gather_rule_names(rule_data)
    if not rule_names:
        raise ValueError("La regla debe incluir un 'Nombre de la regla' válido")

    conflict = repository.find_conflicting_rule_name(
        rule_names, exclude_rule_id=exclude_rule_id
    )
    if conflict is not None:
        raise ValueError(f"Ya existe una regla con el nombre '{conflict}'")


__all__ = ["ensure_unique_rule_names", "gather_rule_names"]
