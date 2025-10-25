"""Use cases orchestrating load executions for templates."""

from __future__ import annotations

import json
import math
import re
import unicodedata
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path
from typing import Any, Callable

import pandas as pd
from pandas import DataFrame
from sqlalchemy import MetaData, Table, insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.domain.entities import Load, LoadedFile, Template, TemplateColumn, User
from app.infrastructure.database import engine
from app.infrastructure.repositories import (
    LoadRepository,
    LoadedFileRepository,
    RuleRepository,
    TemplateRepository,
    TemplateUserAccessRepository,
)
from app.infrastructure.template_files import relative_to_project_root

_REPORT_DIRECTORY = Path(__file__).resolve().parents[2] / "Files" / "Reports"

_SUPPORTED_EXTENSIONS = {".xlsx", ".xls", ".csv"}


def upload_template_load(
    session: Session,
    *,
    template_id: int,
    user: User,
    file_bytes: bytes,
    filename: str,
) -> Load:
    """Execute a new load for ``template_id`` using ``file_bytes``."""

    template = _get_template(session, template_id)
    _ensure_user_has_access(session, template, user)

    if not filename:
        raise ValueError("Nombre de archivo no proporcionado")

    suffix = Path(filename).suffix.lower()
    if suffix not in _SUPPORTED_EXTENSIONS:
        raise ValueError(
            "Formato de archivo no soportado. Usa archivos .xlsx, .xls o .csv"
        )

    columns = _ordered_active_columns(template)
    if not columns:
        raise ValueError("La plantilla no tiene columnas activas para importar")

    load_repo = LoadRepository(session)
    now = datetime.utcnow()
    load = load_repo.create(
        Load(
            id=None,
            template_id=template.id,
            user_id=user.id,
            status="processing",
            file_name=filename,
            total_rows=0,
            error_rows=0,
            report_path=None,
            created_at=now,
            started_at=now,
            finished_at=None,
        )
    )

    try:
        dataframe = _read_source_file(file_bytes, suffix)
        dataframe = _normalize_dataframe(dataframe)
        _validate_headers(dataframe, columns)

        rules = _load_rules(session, columns)
        validated_df, row_is_valid = _validate_dataframe(dataframe, columns, rules)

        inserted_rows = _persist_valid_rows(validated_df, row_is_valid, template.table_name)

        report_path = _generate_report(load.id, validated_df, template.table_name)

        total_rows = len(validated_df.index)
        error_rows = total_rows - inserted_rows

        final_status = "completed"
        finished_at = datetime.utcnow()
        relative_report_path = relative_to_project_root(report_path)
        load = load_repo.update(
            Load(
                id=load.id,
                template_id=load.template_id,
                user_id=load.user_id,
                status=final_status,
                file_name=load.file_name,
                total_rows=total_rows,
                error_rows=error_rows,
                report_path=relative_report_path,
                created_at=load.created_at,
                started_at=load.started_at,
                finished_at=finished_at,
            )
        )

        _register_loaded_file(
            session,
            load_repo=load_repo,
            load=load,
            template=template,
            user=user,
            report_path=report_path,
            relative_report_path=relative_report_path,
        )
    except Exception as exc:  # pragma: no cover - defensive path
        _mark_load_as_failed(load_repo, load, str(exc))
        if isinstance(exc, (ValueError, PermissionError)):
            raise
        raise ValueError(str(exc)) from exc

    return load


def list_loads(
    session: Session,
    *,
    current_user: User,
    template_id: int | None = None,
    skip: int = 0,
    limit: int | None = 100,
) -> Sequence[Load]:
    """Return loads visible to ``current_user``."""

    repository = LoadRepository(session)
    if current_user.is_admin():
        return repository.list(template_id=template_id, skip=skip, limit=limit)
    return repository.list(
        template_id=template_id, user_id=current_user.id, skip=skip, limit=limit
    )


def get_load(
    session: Session,
    *,
    load_id: int,
    current_user: User,
) -> Load:
    """Return the load identified by ``load_id`` if accessible to ``current_user``."""

    repository = LoadRepository(session)
    load = repository.get(load_id)
    if load is None:
        raise ValueError("Carga no encontrada")
    if not current_user.is_admin() and load.user_id != current_user.id:
        raise PermissionError("No autorizado")
    return load


def get_load_report(
    session: Session,
    *,
    load_id: int,
    current_user: User,
) -> tuple[Load, Path]:
    """Return the filesystem path to the report generated for ``load_id``."""

    load = get_load(session, load_id=load_id, current_user=current_user)
    loaded_file = LoadedFileRepository(session).get_latest_by_load(load.id)
    if loaded_file is None:
        raise FileNotFoundError("Reporte no disponible para esta carga")

    if not current_user.is_admin() and loaded_file.created_user_id != current_user.id:
        raise PermissionError("No autorizado")

    project_root = Path(__file__).resolve().parents[2]
    path = project_root / loaded_file.path
    if not path.exists():
        raise FileNotFoundError("Reporte no encontrado en el sistema de archivos")
    return load, path


def _get_template(session: Session, template_id: int) -> Template:
    template = TemplateRepository(session).get(template_id)
    if template is None:
        raise ValueError("Plantilla no encontrada")
    return template


def _ensure_user_has_access(session: Session, template: Template, user: User) -> None:
    if user.is_admin():
        return
    access = TemplateUserAccessRepository(session).get_active_access(
        user_id=user.id, template_id=template.id
    )
    if access is None:
        raise PermissionError("El usuario no tiene acceso a la plantilla solicitada")


def _ordered_active_columns(template: Template) -> list[TemplateColumn]:
    active_columns = [column for column in template.columns if column.is_active]
    return sorted(active_columns, key=lambda col: col.id or 0)


def _read_source_file(file_bytes: bytes, suffix: str) -> DataFrame:
    buffer = BytesIO(file_bytes)
    if suffix == ".csv":
        return pd.read_csv(buffer, dtype=object)
    return pd.read_excel(buffer, dtype=object)


def _normalize_dataframe(dataframe: DataFrame) -> DataFrame:
    df = dataframe.copy()
    df.columns = [str(column).strip() for column in df.columns]
    df.replace({"": pd.NA}, inplace=True)
    df.replace(to_replace=r"^\s+$", value=pd.NA, regex=True, inplace=True)
    df.dropna(how="all", inplace=True)
    df = df.reset_index(drop=True)
    return df


def _validate_headers(dataframe: DataFrame, columns: Sequence[TemplateColumn]) -> None:
    expected = [column.name for column in columns]
    observed = list(dataframe.columns)
    if expected != observed:
        raise ValueError(
            "Los encabezados del archivo no coinciden con la plantilla configurada"
        )


def _load_rules(
    session: Session, columns: Sequence[TemplateColumn]
) -> dict[int, dict[str, Any] | list[Any]]:
    rule_ids = {column.rule_id for column in columns if column.rule_id is not None}
    if not rule_ids:
        return {}
    repository = RuleRepository(session)
    rules: dict[int, dict[str, Any] | list[Any]] = {}
    for rule_id in rule_ids:
        rule = repository.get(rule_id)
        if rule and rule.is_active:
            rules[rule_id] = rule.rule
    return rules


def _validate_dataframe(
    dataframe: DataFrame,
    columns: Sequence[TemplateColumn],
    rules: dict[int, dict[str, Any] | list[Any]],
) -> tuple[DataFrame, list[bool]]:
    df = dataframe.copy()
    observations: list[list[str]] = [[] for _ in range(len(df.index))]
    row_is_valid = [True] * len(df.index)

    for column in columns:
        normalized_type = _normalize_type_label(column.data_type)
        parser = _TYPE_PARSERS.get(normalized_type)
        if parser is None and (column.rule_id is None or column.rule_id not in rules):
            raise ValueError(
                f"Tipo de dato desconocido para la columna '{column.name}'"
            )

        series = df[column.name] if column.name in df.columns else pd.Series(dtype=object)
        rule_definition = rules.get(column.rule_id or -1)

        for idx, raw_value in enumerate(series.tolist()):
            normalized_value = _normalize_cell_value(raw_value)
            df.at[idx, column.name] = normalized_value
            row_snapshot = df.iloc[idx].to_dict()
            row_snapshot[column.name] = normalized_value

            column_errors: list[str] = []
            converted_value = normalized_value

            if rule_definition is not None:
                candidate_value, rule_errors = _validate_value_with_rule(
                    column.name,
                    normalized_value,
                    rule_definition,
                    row_snapshot,
                    parser,
                )
                column_errors.extend(rule_errors)
                if not rule_errors:
                    converted_value = candidate_value
            elif parser is not None:
                parsed_value, parse_error = parser(normalized_value)
                if parse_error:
                    column_errors.append(f"{column.name}: {parse_error}")
                else:
                    converted_value = parsed_value

            if column_errors:
                observations[idx].extend(column_errors)
                row_is_valid[idx] = False
            else:
                df.at[idx, column.name] = converted_value

    df["Observaciones"] = [
        "; ".join(messages) if messages else "" for messages in observations
    ]
    return df, row_is_valid


def _normalize_cell_value(value: Any) -> Any:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return value


def _persist_valid_rows(
    dataframe: DataFrame, row_is_valid: Sequence[bool], table_name: str
) -> int:
    if not len(dataframe.index):
        return 0

    valid_indices = [index for index, flag in enumerate(row_is_valid) if flag]
    if not valid_indices:
        return 0

    payload_df = dataframe.loc[valid_indices, dataframe.columns[:-1]]
    normalized_df = payload_df.where(pd.notnull(payload_df), None)
    records = []
    for row in normalized_df.to_dict(orient="records"):
        normalized_row: dict[str, Any] = {}
        for key, value in row.items():
            if isinstance(value, pd.Timestamp):
                normalized_row[key] = _coerce_timestamp(value)
            elif value is None:
                normalized_row[key] = None
            else:
                normalized_row[key] = value
        records.append(normalized_row)

    metadata = MetaData()
    table = Table(table_name, metadata, autoload_with=engine)
    try:
        with engine.begin() as connection:
            connection.execute(insert(table), records)
    except SQLAlchemyError as exc:  # pragma: no cover - defensive passthrough
        raise RuntimeError(
            f"No se pudo insertar la información validada en la tabla '{table_name}'"
        ) from exc

    return len(records)


def _generate_report(load_id: int, dataframe: DataFrame, table_name: str) -> Path:
    report_directory = _REPORT_DIRECTORY / table_name
    report_directory.mkdir(parents=True, exist_ok=True)
    report_path = report_directory / f"load_{load_id}_reporte.xlsx"
    dataframe.to_excel(report_path, index=False)
    return report_path


def _register_loaded_file(
    session: Session,
    *,
    load_repo: LoadRepository,
    load: Load,
    template: Template,
    user: User,
    report_path: Path,
    relative_report_path: str,
) -> None:
    loaded_file_repo = LoadedFileRepository(session)
    num_load = load_repo.count_completed_by_user_and_template(
        user_id=user.id, template_id=template.id
    )
    size_bytes = report_path.stat().st_size if report_path.exists() else 0
    loaded_file_repo.create(
        LoadedFile(
            id=None,
            load_id=load.id,
            name=report_path.name,
            path=relative_report_path,
            size_bytes=size_bytes,
            num_load=num_load,
            created_user_id=user.id,
            created_at=None,
        )
    )


def _mark_load_as_failed(repository: LoadRepository, load: Load, message: str) -> None:
    finished_at = datetime.utcnow()
    repository.update(
        Load(
            id=load.id,
            template_id=load.template_id,
            user_id=load.user_id,
            status="failed",
            file_name=load.file_name,
            total_rows=load.total_rows,
            error_rows=load.error_rows,
            report_path=load.report_path,
            created_at=load.created_at,
            started_at=load.started_at,
            finished_at=finished_at,
        )
    )


def _validate_value_with_rule(
    column_name: str,
    value: Any,
    rule_definition: dict[str, Any] | list[Any],
    row_context: Mapping[str, Any],
    base_parser: Callable[[Any], tuple[Any, str | None]] | None,
) -> tuple[Any, list[str]]:
    if isinstance(rule_definition, list):
        current_value = value
        all_errors: list[str] = []
        for definition in rule_definition:
            current_value, definition_errors = _validate_value_with_rule(
                column_name,
                current_value,
                definition,
                row_context,
                base_parser,
            )
            if definition_errors:
                all_errors.extend(definition_errors)
        return current_value, all_errors

    if not isinstance(rule_definition, dict):
        return value, [f"{column_name}: configuración de regla inválida"]

    message = rule_definition.get("Mensaje de error")
    normalized_message = message.strip() if isinstance(message, str) else None
    required = bool(rule_definition.get("Campo obligatorio"))

    if value is None:
        if required:
            return None, [_compose_error(normalized_message, f"{column_name}: es obligatorio")]
        return None, []

    tipo = rule_definition.get("Tipo de dato")
    normalized_tipo = _normalize_type_label(tipo or "")
    rule_config = rule_definition.get("Regla")
    if not isinstance(rule_config, dict):
        rule_config = {}

    validator = _RULE_VALIDATORS.get(normalized_tipo)
    if validator is None:
        parsed_value, parse_errors = _apply_base_parser(
            value, column_name, base_parser, normalized_message
        )
        return parsed_value, parse_errors

    parsed_value, validator_errors = validator(
        value=value,
        column_name=column_name,
        rule_definition=rule_definition,
        rule_config=rule_config,
        message=normalized_message,
        row_context=row_context,
        base_parser=base_parser,
    )
    return parsed_value, validator_errors


def _apply_base_parser(
    value: Any,
    column_name: str,
    base_parser: Callable[[Any], tuple[Any, str | None]] | None,
    message: str | None,
) -> tuple[Any, list[str]]:
    if base_parser is None:
        return value, []
    parsed_value, parse_error = base_parser(value)
    if parse_error:
        return value, [_compose_error(message, f"{column_name}: {parse_error}")]
    return parsed_value, []


def _compose_error(message: str | None, fallback: str) -> str:
    if message:
        return f"{message} ({fallback})"
    return fallback


def _normalize_type_label(label: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(label))
    ascii_label = "".join(char for char in normalized if not unicodedata.combining(char))
    return ascii_label.lower().strip()


def _validate_text_rule(
    *,
    value: Any,
    column_name: str,
    rule_config: Mapping[str, Any],
    message: str | None,
    **_: Any,
) -> tuple[str, list[str]]:
    text_value = str(value)
    errors: list[str] = []
    min_length = rule_config.get("Longitud minima")
    max_length = rule_config.get("Longitud maxima")
    if isinstance(min_length, int) and len(text_value) < min_length:
        errors.append(
            _compose_error(
                message,
                f"{column_name}: longitud mínima {min_length} caracteres",
            )
        )
    if isinstance(max_length, int) and len(text_value) > max_length:
        errors.append(
            _compose_error(
                message,
                f"{column_name}: longitud máxima {max_length} caracteres",
            )
        )
    return text_value, errors


def _validate_document_rule(
    *,
    value: Any,
    column_name: str,
    rule_config: Mapping[str, Any],
    message: str | None,
    **_: Any,
) -> tuple[str, list[str]]:
    text_value = str(value)
    errors: list[str] = []
    min_length = rule_config.get("Longitud minima")
    max_length = rule_config.get("Longitud maxima")
    if isinstance(min_length, int) and len(text_value) < min_length:
        errors.append(
            _compose_error(
                message,
                f"{column_name}: longitud mínima {min_length} caracteres",
            )
        )
    if isinstance(max_length, int) and len(text_value) > max_length:
        errors.append(
            _compose_error(
                message,
                f"{column_name}: longitud máxima {max_length} caracteres",
            )
        )
    return text_value, errors


def _validate_number_rule(
    *,
    value: Any,
    column_name: str,
    rule_config: Mapping[str, Any],
    message: str | None,
    **_: Any,
) -> tuple[Any, list[str]]:
    errors: list[str] = []
    try:
        numeric_value = Decimal(str(value))
    except (InvalidOperation, ValueError):
        errors.append(_compose_error(message, f"{column_name}: debe ser numérico"))
        return value, errors

    decimals_allowed = rule_config.get("Número de decimales")
    if isinstance(decimals_allowed, int):
        actual_decimals = max(-numeric_value.as_tuple().exponent, 0)
        if actual_decimals > decimals_allowed:
            errors.append(
                _compose_error(
                    message,
                    f"{column_name}: máximo {decimals_allowed} decimales",
                )
            )

    min_value = rule_config.get("Valor mínimo")
    if min_value is not None:
        try:
            if numeric_value < Decimal(str(min_value)):
                errors.append(
                    _compose_error(
                        message,
                        f"{column_name}: valor mínimo {min_value}",
                    )
                )
        except (InvalidOperation, ValueError):
            errors.append(
                _compose_error(message, f"{column_name}: límite mínimo inválido"),
            )

    max_value = rule_config.get("Valor máximo")
    if max_value is not None:
        try:
            if numeric_value > Decimal(str(max_value)):
                errors.append(
                    _compose_error(
                        message,
                        f"{column_name}: valor máximo {max_value}",
                    )
                )
        except (InvalidOperation, ValueError):
            errors.append(
                _compose_error(message, f"{column_name}: límite máximo inválido"),
            )

    if errors:
        return value, errors

    if isinstance(decimals_allowed, int) and decimals_allowed == 0:
        return int(numeric_value), []
    return float(numeric_value), []


def _validate_list_rule(
    *,
    value: Any,
    column_name: str,
    rule_config: Mapping[str, Any],
    message: str | None,
    **_: Any,
) -> tuple[str, list[str]]:
    text_value = str(value)
    allowed_values = _extract_allowed_values(rule_config)
    if not allowed_values:
        return text_value, []
    normalized_choices = {str(choice) for choice in allowed_values}
    if text_value not in normalized_choices:
        return text_value, [
            _compose_error(
                message,
                f"{column_name}: valor no permitido ({', '.join(sorted(normalized_choices))})",
            )
        ]
    return text_value, []


def _validate_phone_rule(
    *,
    value: Any,
    column_name: str,
    rule_config: Mapping[str, Any],
    message: str | None,
    **_: Any,
) -> tuple[str, list[str]]:
    text_value = str(value)
    digits = re.sub(r"[^0-9]", "", text_value)
    if not digits:
        return text_value, [
            _compose_error(message, f"{column_name}: debe contener solo números"),
        ]

    country_code = str(rule_config.get("Código de país") or "")
    code_digits = re.sub(r"[^0-9]", "", country_code)
    local_digits = digits
    if code_digits:
        if not digits.startswith(code_digits):
            return text_value, [
                _compose_error(
                    message,
                    f"{column_name}: debe iniciar con el código de país {country_code}",
                )
            ]
        local_digits = digits[len(code_digits) :]

    min_length = rule_config.get("Longitud minima")
    if isinstance(min_length, int) and len(local_digits) < min_length:
        return text_value, [
            _compose_error(
                message,
                f"{column_name}: longitud mínima de {min_length} dígitos",
            )
        ]

    formatted = f"+{code_digits}{local_digits}" if code_digits else local_digits
    return formatted, []


def _validate_email_rule(
    *,
    value: Any,
    column_name: str,
    rule_config: Mapping[str, Any],
    message: str | None,
    **_: Any,
) -> tuple[str, list[str]]:
    text_value = str(value)
    pattern = rule_config.get("Formato")
    if isinstance(pattern, str) and pattern.strip():
        if not re.fullmatch(pattern, text_value):
            return text_value, [
                _compose_error(message, f"{column_name}: formato de correo inválido"),
            ]

    max_length = rule_config.get("Longitud máxima")
    if isinstance(max_length, int) and len(text_value) > max_length:
        return text_value, [
            _compose_error(
                message,
                f"{column_name}: longitud máxima {max_length} caracteres",
            )
        ]

    return text_value.lower(), []


def _validate_date_rule(
    *,
    value: Any,
    column_name: str,
    rule_config: Mapping[str, Any],
    message: str | None,
    **_: Any,
) -> tuple[date, list[str]]:
    if isinstance(value, datetime):
        return value.date(), []

    format_alias = rule_config.get("Formato")
    format_map = {
        "yyyy-mm-dd": "%Y-%m-%d",
        "dd/mm/yyyy": "%d/%m/%Y",
        "mm-dd-yyyy": "%m-%d-%Y",
    }
    normalized_format = _normalize_type_label(format_alias or "")
    strptime_format = format_map.get(normalized_format)

    if strptime_format:
        try:
            parsed = datetime.strptime(str(value), strptime_format)
            return parsed.date(), []
        except (ValueError, TypeError):
            return value, [
                _compose_error(message, f"{column_name}: formato de fecha inválido"),
            ]

    try:
        timestamp = pd.to_datetime(value, errors="raise")
    except Exception:  # pragma: no cover - pandas raises multiple exceptions
        return value, [
            _compose_error(message, f"{column_name}: fecha inválida"),
        ]
    return timestamp.date(), []


def _validate_dependency_rule(
    *,
    value: Any,
    column_name: str,
    rule_config: Mapping[str, Any],
    message: str | None,
    row_context: Mapping[str, Any],
    base_parser: Callable[[Any], tuple[Any, str | None]] | None,
    **_: Any,
) -> tuple[Any, list[str]]:
    dependent_name = rule_config.get("Nombre dependiente")
    trigger_value = rule_config.get("valor")
    specific_rules = rule_config.get("reglas especifica")

    if not isinstance(dependent_name, str) or not dependent_name:
        parsed_value, base_errors = _apply_base_parser(
            value, column_name, base_parser, message
        )
        return parsed_value, base_errors

    dependent_current = _normalize_cell_value(row_context.get(dependent_name))
    if trigger_value is not None and str(dependent_current) != str(trigger_value):
        parsed_value, base_errors = _apply_base_parser(
            value, column_name, base_parser, message
        )
        return parsed_value, base_errors

    if not isinstance(specific_rules, list) or not specific_rules:
        parsed_value, base_errors = _apply_base_parser(
            value, column_name, base_parser, message
        )
        return parsed_value, base_errors

    current_value = value
    accumulated_errors: list[str] = []
    for entry in specific_rules:
        if not isinstance(entry, dict) or len(entry) != 1:
            accumulated_errors.append(
                _compose_error(message, f"{column_name}: configuración dependiente inválida")
            )
            continue
        key, config = next(iter(entry.items()))
        normalized_key = _normalize_type_label(key)
        handler = _DEPENDENCY_RULE_HANDLERS.get(normalized_key)
        if handler is None:
            accumulated_errors.append(
                _compose_error(
                    message,
                    f"{column_name}: tipo dependiente '{key}' no soportado",
                )
            )
            continue
        current_value, dependency_errors = handler(
            current_value,
            column_name,
            config if isinstance(config, Mapping) else {},
            message,
        )
        if dependency_errors:
            accumulated_errors.extend(dependency_errors)

    if accumulated_errors:
        return value, accumulated_errors

    parsed_value, base_errors = _apply_base_parser(
        current_value, column_name, base_parser, message
    )
    return parsed_value, base_errors


def _validate_joint_rule(
    *,
    value: Any,
    column_name: str,
    rule_config: Mapping[str, Any],
    message: str | None,
    row_context: Mapping[str, Any],
    base_parser: Callable[[Any], tuple[Any, str | None]] | None,
    **_: Any,
) -> tuple[Any, list[str]]:
    fields = []
    raw_fields = rule_config.get("Nombre de campos")
    if isinstance(raw_fields, list):
        fields = [str(field) for field in raw_fields if str(field).strip()]

    if column_name not in fields:
        fields.append(column_name)

    non_empty = 0
    for field in fields:
        current = value if field == column_name else row_context.get(field)
        normalized = _normalize_cell_value(current)
        if normalized is not None:
            non_empty += 1

    if 0 < non_empty < len(fields):
        return value, [
            _compose_error(
                message,
                f"{column_name}: completa todos los campos relacionados ({', '.join(fields)})",
            )
        ]

    parsed_value, base_errors = _apply_base_parser(
        value, column_name, base_parser, message
    )
    return parsed_value, base_errors


def _dependency_text_validator(
    value: Any, column_name: str, rule_config: Mapping[str, Any], message: str | None
) -> tuple[str, list[str]]:
    return _validate_text_rule(
        value=value,
        column_name=column_name,
        rule_config=rule_config,
        message=message,
    )


def _dependency_number_validator(
    value: Any, column_name: str, rule_config: Mapping[str, Any], message: str | None
) -> tuple[Any, list[str]]:
    return _validate_number_rule(
        value=value,
        column_name=column_name,
        rule_config=rule_config,
        message=message,
    )


def _extract_allowed_values(rule_config: Mapping[str, Any]) -> list[Any]:
    candidate_keys = [
        "Valores permitidos",
        "Valores",
        "Lista",
        "Opciones",
        "options",
        "choices",
    ]
    for key in candidate_keys:
        values = rule_config.get(key)
        if isinstance(values, list):
            return values
    return []


def _coerce_timestamp(value: Any) -> Any:
    if isinstance(value, pd.Timestamp):
        if value.tzinfo is not None:
            value = value.tz_convert(None)
        return value.to_pydatetime()
    return value


def _parse_string(value: Any) -> tuple[Any, str | None]:
    if value is None:
        return None, None
    return str(value), None


def _parse_text(value: Any) -> tuple[Any, str | None]:
    return _parse_string(value)


def _parse_integer(value: Any) -> tuple[Any, str | None]:
    if value is None:
        return None, None
    if isinstance(value, bool):
        return None, "debe ser un número entero"
    if isinstance(value, int):
        return value, None
    if isinstance(value, float) and value.is_integer():
        return int(value), None
    try:
        decimal_value = Decimal(str(value))
    except InvalidOperation:
        return None, "debe ser un número entero"
    if decimal_value != decimal_value.to_integral_value():
        return None, "debe ser un número entero"
    return int(decimal_value), None


def _parse_float(value: Any) -> tuple[Any, str | None]:
    if value is None:
        return None, None
    if isinstance(value, bool):
        return None, "debe ser un número"
    try:
        return float(value), None
    except (TypeError, ValueError):
        try:
            return float(Decimal(str(value))), None
        except (InvalidOperation, ValueError):
            return None, "debe ser un número"


_TRUTHY = {"true", "1", "yes", "si", "sí"}
_FALSY = {"false", "0", "no"}


def _parse_boolean(value: Any) -> tuple[Any, str | None]:
    if value is None:
        return None, None
    if isinstance(value, bool):
        return value, None
    if isinstance(value, (int, float)):
        if value in (0, 1):
            return bool(value), None
        return None, "debe ser un valor booleano"
    text = str(value).strip().lower()
    if text in _TRUTHY:
        return True, None
    if text in _FALSY:
        return False, None
    return None, "debe ser un valor booleano"


def _parse_date(value: Any) -> tuple[Any, str | None]:
    if value is None:
        return None, None
    if isinstance(value, datetime):
        return value.date(), None
    try:
        timestamp = pd.to_datetime(value, errors="raise")
    except Exception:  # pragma: no cover - pandas raises multiple exceptions
        return None, "debe ser una fecha válida"
    return timestamp.date(), None


def _parse_datetime(value: Any) -> tuple[Any, str | None]:
    if value is None:
        return None, None
    if isinstance(value, datetime):
        return value, None
    try:
        timestamp = pd.to_datetime(value, errors="raise")
    except Exception:  # pragma: no cover - pandas raises multiple exceptions
        return None, "debe ser una fecha y hora válida"
    return timestamp.to_pydatetime(), None


def _parse_json(value: Any) -> tuple[Any, str | None]:
    if value is None:
        return None, None
    if isinstance(value, (dict, list)):
        return value, None
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError:
        return None, "debe contener un JSON válido"
    return parsed, None


_TypeParser = Callable[[Any], tuple[Any, str | None]]

_TYPE_PARSERS: dict[str, _TypeParser] = {
    "string": _parse_string,
    "text": _parse_text,
    "integer": _parse_integer,
    "float": _parse_float,
    "boolean": _parse_boolean,
    "date": _parse_date,
    "datetime": _parse_datetime,
    "json": _parse_json,
    "texto": _parse_text,
    "numero": _parse_float,
    "documento": _parse_string,
    "lista": _parse_string,
    "telefono": _parse_string,
    "correo": _parse_string,
    "fecha": _parse_date,
    "dependencia": _parse_string,
    "validacion conjunta": _parse_string,
}


RuleValidator = Callable[..., tuple[Any, list[str]]]

_RULE_VALIDATORS: dict[str, RuleValidator] = {
    "texto": _validate_text_rule,
    "documento": _validate_document_rule,
    "numero": _validate_number_rule,
    "lista": _validate_list_rule,
    "telefono": _validate_phone_rule,
    "correo": _validate_email_rule,
    "fecha": _validate_date_rule,
    "dependencia": _validate_dependency_rule,
    "validacion conjunta": _validate_joint_rule,
}

_DEPENDENCY_RULE_HANDLERS: dict[
    str, Callable[[Any, str, Mapping[str, Any], str | None], tuple[Any, list[str]]]
] = {
    "texto": _dependency_text_validator,
    "numero": _dependency_number_validator,
}


__all__ = [
    "get_load",
    "get_load_report",
    "list_loads",
    "upload_template_load",
]
