"""Utility helpers for generating Excel files for templates."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Sequence

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill, Protection

from app.domain.entities import TemplateColumn


_BASE_DIRECTORY = Path(__file__).resolve().parents[2] / "Files" / "digital_file"


def _sanitize_filename(name: str) -> str:
    """Return ``name`` transformed into a filesystem-safe slug."""

    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", name.strip())
    cleaned = cleaned.strip("_")
    return cleaned or "template"


def template_excel_path(template_id: int, template_name: str) -> Path:
    """Return the expected filesystem path for a template Excel file."""

    filename = f"{template_id}_{_sanitize_filename(template_name)}.xlsx"
    return _BASE_DIRECTORY / filename


def relative_to_project_root(path: Path) -> str:
    """Return ``path`` relative to the project root directory."""

    project_root = Path(__file__).resolve().parents[2]
    return str(path.relative_to(project_root))


def create_template_excel(
    template_id: int, template_name: str, columns: Sequence[TemplateColumn]
) -> Path:
    """Create an Excel workbook containing the template column headers."""

    path = template_excel_path(template_id, template_name)
    path.parent.mkdir(parents=True, exist_ok=True)

    workbook = Workbook()
    workbook.security.lockStructure = True
    worksheet = workbook.active
    worksheet.title = "Datos"

    headers = [column.name for column in columns]
    if headers:
        worksheet.append(headers)
        header_fill = PatternFill(fill_type="solid", fgColor="4F81BD")
        header_font = Font(color="FFFFFFFF", bold=True)
        header_alignment = Alignment(horizontal="center", vertical="center")
        for cell in worksheet[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_alignment
            cell.protection = Protection(locked=True)

        worksheet.freeze_panes = "A2"

        # Allow data entry without altering the structure of the sheet.
        max_col = len(headers)
        for row in worksheet.iter_rows(min_row=2, max_row=1000, max_col=max_col):
            for cell in row:
                cell.protection = Protection(locked=False)

    worksheet.protection.enable()
    worksheet.protection.insertColumns = False
    worksheet.protection.deleteColumns = False
    worksheet.protection.insertRows = True
    worksheet.protection.deleteRows = False
    worksheet.protection.formatColumns = False
    worksheet.protection.formatRows = False
    worksheet.protection.sort = False
    worksheet.protection.autoFilter = False
    worksheet.protection.insertHyperlinks = False

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
    "relative_to_project_root",
    "template_excel_path",
]

