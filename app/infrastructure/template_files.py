"""Utility helpers for generating Excel files for templates."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Sequence

from openpyxl import Workbook

from app.domain.entities import TemplateColumn


_BASE_DIRECTORY = Path(__file__).resolve().parents[2] / "storage" / "templates"


def _sanitize_filename(name: str) -> str:
    """Return ``name`` transformed into a filesystem-safe slug."""

    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", name.strip())
    cleaned = cleaned.strip("_")
    return cleaned or "template"


def template_excel_path(template_id: int, template_name: str) -> Path:
    """Return the expected filesystem path for a template Excel file."""

    filename = f"{template_id}_{_sanitize_filename(template_name)}.xlsx"
    return _BASE_DIRECTORY / filename


def create_template_excel(
    template_id: int, template_name: str, columns: Sequence[TemplateColumn]
) -> Path:
    """Create an Excel workbook containing the template column headers."""

    path = template_excel_path(template_id, template_name)
    path.parent.mkdir(parents=True, exist_ok=True)

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Datos"

    headers = [column.name for column in columns]
    if headers:
        worksheet.append(headers)

    workbook.save(path)
    return path


def delete_template_excel(template_id: int, template_name: str) -> None:
    """Remove the Excel workbook associated with a template if it exists."""

    path = template_excel_path(template_id, template_name)
    if path.exists():
        path.unlink()


__all__ = [
    "create_template_excel",
    "delete_template_excel",
    "template_excel_path",
]

