"""Use cases orchestrating load executions for templates."""

from __future__ import annotations

import importlib
import json
import math
import re
import unicodedata
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Callable
from sqlalchemy import MetaData, Table, insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.application.use_cases.notifications import (
    notify_load_status_changed,
    notify_load_validated_success,
    notify_template_processing,
)
from app.domain.entities import (
    LOAD_STATUS_FAILED,
    LOAD_STATUS_PROCESSING,
    LOAD_STATUS_VALIDATED_SUCCESS,
    LOAD_STATUS_VALIDATED_WITH_ERRORS,
    Load,
    LoadedFile,
    Template,
    TemplateColumn,
    User,
)
from app.infrastructure.database import engine
from app.infrastructure.repositories import (
    LoadRepository,
    LoadedFileRepository,
    RuleRepository,
    TemplateRepository,
    TemplateUserAccessRepository,
    UserRepository,
)
from app.infrastructure.template_files import relative_to_project_root

_REPORT_DIRECTORY = Path(__file__).resolve().parents[3] / "Files" / "Reports"

_SUPPORTED_EXTENSIONS = {".xlsx", ".xls", ".csv"}


@lru_cache(maxsize=1)
def _get_pandas_module() -> Any:
    """Load :mod:`pandas` lazily to avoid import-time circular errors."""

    return importlib.import_module("pandas")


if TYPE_CHECKING:
    from pandas import DataFrame  # pragma: no cover
else:  # pragma: no cover
    DataFrame = Any


def upload_template_load(
    session: Session,
    *,
    template_id: int,
    user: User,
    file_bytes: bytes,
    filename: str,
) -> Load:
    """Register a new load for ``template_id`` and mark it as pending processing."""

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

    if not file_bytes:
        raise ValueError("El archivo proporcionado está vacío")

    load_repo = LoadRepository(session)
    now = datetime.utcnow()
    load = load_repo.create(
        Load(
            id=None,
            template_id=template.id,
            user_id=user.id,
            status=LOAD_STATUS_PROCESSING,
            file_name=filename,
            total_rows=0,
            error_rows=0,
            report_path=None,
            created_at=now,
            started_at=now,
            finished_at=None,
        )
    )

    notify_template_processing(
        session, load=load, template=template, user=user
    )
    return load


def process_template_load(
    session: Session,
    *,
    load_id: int,
    template_id: int,
    user_id: int,
    file_bytes: bytes,
    filename: str,
) -> Load:
    """Execute the validation flow for an existing load."""

    load_repo = LoadRepository(session)
    load = load_repo.get(load_id)
    if load is None:
        raise ValueError("Carga no encontrada")

    template = _get_template(session, template_id)
    user = UserRepository(session).get(user_id)
    if user is None:
        raise ValueError("Usuario no encontrado")

    _ensure_user_has_access(session, template, user)

    suffix = Path(filename).suffix.lower()
    if suffix not in _SUPPORTED_EXTENSIONS:
        raise ValueError(
            "Formato de archivo no soportado. Usa archivos .xlsx, .xls o .csv"
        )

    columns = _ordered_active_columns(template)
    if not columns:
        raise ValueError("La plantilla no tiene columnas activas para importar")

    try:
        dataframe = _read_source_file(file_bytes, suffix)
        dataframe = _normalize_dataframe(dataframe)
        _validate_headers(dataframe, columns)

        rules = _load_rules(session, columns)
        validated_df, row_is_valid = _validate_dataframe(dataframe, columns, rules)

        operation_number = load.id or 0
        if not operation_number:
            raise ValueError("Identificador de carga inválido")
        processed_rows = _persist_rows(
            validated_df,
            row_is_valid,
            template.table_name,
            operation_number=operation_number,
        )

        report_df = _prepare_report_dataframe(validated_df)
        source_df = _prepare_original_dataframe(validated_df)

        report_path = _generate_report(load.id, report_df, template.table_name)
        _generate_original_file(
            load.id,
            source_df,
            template.table_name,
            suffix,
        )

        total_rows = len(validated_df.index)
        error_rows = total_rows - processed_rows

        final_status = (
            LOAD_STATUS_VALIDATED_SUCCESS
            if error_rows == 0
            else LOAD_STATUS_VALIDATED_WITH_ERRORS
        )
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
        notify_load_status_changed(
            session, load=load, template=template, user=user
        )
        notify_load_validated_success(session, load=load, template=template)
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

    project_root = Path(__file__).resolve().parents[3]
    path = project_root / loaded_file.path
    if not path.exists():
        raise FileNotFoundError("Reporte no encontrado en el sistema de archivos")
    return load, path


def get_load_original_file(
    session: Session,
    *,
    load_id: int,
    current_user: User,
) -> tuple[Load, Path]:
    """Return the original data file without status/observations columns for ``load_id``."""

    load = get_load(session, load_id=load_id, current_user=current_user)
    template = _get_template(session, load.template_id)

    suffix = Path(load.file_name).suffix.lower()
    extension = ".csv" if suffix == ".csv" else ".xlsx"

    directory = _REPORT_DIRECTORY / template.table_name
    path = directory / f"load_{load.id}_original{extension}"
    if not path.exists():
        raise FileNotFoundError("Archivo original no disponible para esta carga")

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
    pd = _get_pandas_module()
    buffer = BytesIO(file_bytes)
    if suffix == ".csv":
        return pd.read_csv(buffer, dtype=object)
    return pd.read_excel(buffer, dtype=object)


def _normalize_dataframe(dataframe: DataFrame) -> DataFrame:
    pd = _get_pandas_module()
    pd.set_option('future.no_silent_downcasting', True)
    df = dataframe.copy()
    df.columns = [str(column).strip() for column in df.columns]
    def _replace_blank_strings(value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return pd.NA
        return value
    if len(df.columns):
        df = df.apply(lambda col: col.map(_replace_blank_strings) if col.dtype == "object" else col)
    df = df.infer_objects(copy=False)
    df.dropna(how="all", inplace=True)
    df = df.reset_index(drop=True)
    df = df.astype("object")
    return df


def _validate_headers(dataframe: DataFrame, columns: Sequence[TemplateColumn]) -> None:
    expected = [column.name for column in columns]
    observed = list(dataframe.columns)
    if len(observed) != len(expected):
        raise ValueError(
            "El archivo no contiene la misma cantidad de columnas que la plantilla"
        )

    missing = [column for column in expected if column not in observed]
    extra = [column for column in observed if column not in expected]
    if missing or extra:
        details: list[str] = []
        if missing:
            details.append(
                "faltan columnas: " + ", ".join(f"'{name}'" for name in missing)
            )
        if extra:
            details.append(
                "hay columnas no esperadas: " + ", ".join(f"'{name}'" for name in extra)
            )
        raise ValueError("; ".join(details))

    if expected != observed:
        raise ValueError(
            "El orden de las columnas no coincide con la plantilla configurada"
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
    pd = _get_pandas_module()
    df = dataframe.copy().astype("object")
    observations: list[list[str]] = [[] for _ in range(len(df.index))]
    row_is_valid = [True] * len(df.index)
    duplicate_rules: list[dict[str, Any]] = []
    seen_duplicate_configs: set[tuple[tuple[str, ...], str | None, str | None, bool]] = set()

    normalized_column_lookup: dict[str, str] = {}
    column_token_lookup: dict[str, tuple[str, ...]] = {}

    for column in columns:
        normalized_name = _normalize_type_label(column.name)
        if normalized_name and normalized_name not in normalized_column_lookup:
            normalized_column_lookup[normalized_name] = column.name
        column_token_lookup[column.name] = _tokenize_label(column.name)

    for column in columns:
        normalized_type = _normalize_type_label(column.data_type)
        parser = _TYPE_PARSERS.get(normalized_type)
        if parser is None and (column.rule_id is None or column.rule_id not in rules):
            raise ValueError(
                f"Tipo de dato desconocido para la columna '{column.name}'"
            )

        if column.name not in df.columns:
            df[column.name] = pd.Series([None] * len(df.index), dtype=object)
        series = df[column.name]
        rule_definition = rules.get(column.rule_id or -1)

        if rule_definition is not None:
            duplicate_configs = _gather_duplicate_rule_configs(
                rule_definition, column.name
            )
            for config in duplicate_configs:
                key = (
                    tuple(config["fields"]),
                    config.get("name"),
                    config.get("message"),
                    config.get("ignore_empty", False),
                )
                if key not in seen_duplicate_configs:
                    seen_duplicate_configs.add(key)
                    duplicate_rules.append(config)

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
                    normalized_column_lookup,
                    column_token_lookup,
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

    if duplicate_rules:
        _apply_duplicate_rules(df, duplicate_rules, observations, row_is_valid)

    df["observaciones"] = [
        _summarize_observations(messages) for messages in observations
    ]
    df["status"] = [
        "Procesado" if is_valid else "No procesado" for is_valid in row_is_valid
    ]

    ordered_columns = [
        column
        for column in df.columns
        if column not in {"status", "observaciones"}
    ]
    ordered_columns.extend(["status", "observaciones"])
    df = df.loc[:, ordered_columns]

    return df, row_is_valid


def _normalize_cell_value(value: Any) -> Any:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return value


def _summarize_observations(messages: Sequence[str]) -> str:
    if not messages:
        return ""

    summary: list[str] = []
    seen: set[str] = set()
    for raw_message in messages:
        simplified = _simplify_error_message(raw_message)
        if simplified and simplified not in seen:
            seen.add(simplified)
            summary.append(simplified)
    return " | ".join(summary)


def _simplify_error_message(message: str) -> str:
    text = str(message or "").strip()
    if not text:
        return ""

    text = re.sub(r"\s+", " ", text)

    if "(" in text and text.endswith(")"):
        prefix, suffix = text.rsplit("(", 1)
        candidate = suffix.rstrip(")").strip()
        if candidate and not prefix.strip():
            text = candidate
        elif candidate:
            text = prefix.strip() or candidate

    if ":" in text:
        label, detail = text.split(":", 1)
        label = label.strip()
        detail = detail.strip()
        if label and detail:
            return f"{label}: {detail}"
        return label or detail

    return text


def _persist_rows(
    dataframe: DataFrame,
    row_is_valid: Sequence[bool],
    table_name: str,
    *,
    operation_number: int,
) -> int:
    pd = _get_pandas_module()
    if not len(dataframe.index):
        return 0

    working_df = dataframe.copy()
    working_df["numero_operacion"] = operation_number
    normalized_df = working_df.where(pd.notnull(working_df), None)
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

    return sum(1 for flag in row_is_valid if flag)


def _generate_report(load_id: int, dataframe: DataFrame, table_name: str) -> Path:
    report_directory = _REPORT_DIRECTORY / table_name
    report_directory.mkdir(parents=True, exist_ok=True)
    report_path = report_directory / f"load_{load_id}_reporte.xlsx"
    dataframe.to_excel(report_path, index=False)
    return report_path


def _prepare_report_dataframe(dataframe: DataFrame) -> DataFrame:
    df = dataframe.copy()
    renamed = df.rename(columns={"status": "Status", "observaciones": "Observaciones"})
    ordered_columns = [
        column
        for column in renamed.columns
        if column not in {"Status", "Observaciones"}
    ]
    ordered_columns.extend(["Status", "Observaciones"])
    return renamed.loc[:, ordered_columns]


def _prepare_original_dataframe(dataframe: DataFrame) -> DataFrame:
    drop_columns = [
        column
        for column in ("status", "observaciones", "numero_operacion")
        if column in dataframe.columns
    ]
    return dataframe.drop(columns=drop_columns, errors="ignore")


def _generate_original_file(
    load_id: int, dataframe: DataFrame, table_name: str, suffix: str
) -> Path:
    directory = _REPORT_DIRECTORY / table_name
    directory.mkdir(parents=True, exist_ok=True)

    base_path = directory / f"load_{load_id}_original"
    extension = ".csv" if suffix == ".csv" else ".xlsx"
    path = base_path.with_suffix(extension)

    if extension == ".csv":
        dataframe.to_csv(path, index=False)
    else:
        dataframe.to_excel(path, index=False)

    return path


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
            status=LOAD_STATUS_FAILED,
            file_name=load.file_name,
            total_rows=load.total_rows,
            error_rows=load.error_rows,
            report_path=load.report_path,
            created_at=load.created_at,
            started_at=load.started_at or finished_at,
            finished_at=finished_at,
        )
    )


def _validate_value_with_rule(
    column_name: str,
    value: Any,
    rule_definition: dict[str, Any] | list[Any],
    row_context: Mapping[str, Any],
    base_parser: Callable[[Any], tuple[Any, str | None]] | None,
    column_lookup: Mapping[str, str],
    column_tokens: Mapping[str, tuple[str, ...]],
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
                column_lookup,
                column_tokens,
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
        column_lookup=column_lookup,
        column_tokens=column_tokens,
    )
    return parsed_value, validator_errors


def _gather_duplicate_rule_configs(
    rule_definition: Any, column_name: str
) -> list[dict[str, Any]]:
    if isinstance(rule_definition, list):
        configs: list[dict[str, Any]] = []
        for definition in rule_definition:
            configs.extend(_gather_duplicate_rule_configs(definition, column_name))
        return configs

    if not isinstance(rule_definition, Mapping):
        return []

    rule_type = _normalize_type_label(rule_definition.get("Tipo de dato", ""))
    if rule_type != "duplicados":
        return []

    message = rule_definition.get("Mensaje de error")
    normalized_message = None
    if isinstance(message, str):
        stripped_message = message.strip()
        if stripped_message:
            normalized_message = stripped_message

    rule_name = rule_definition.get("Nombre de la regla")
    normalized_name = None
    if isinstance(rule_name, str):
        stripped_name = rule_name.strip()
        if stripped_name:
            normalized_name = stripped_name

    raw_config = rule_definition.get("Regla")
    config: Mapping[str, Any] = raw_config if isinstance(raw_config, Mapping) else {}

    candidate_keys = ["Campos", "Columnas", "Fields", "fields"]
    fields: list[str] = []
    for key in candidate_keys:
        raw_fields = config.get(key)
        if isinstance(raw_fields, Sequence) and not isinstance(raw_fields, (str, bytes)):
            for field in raw_fields:
                if isinstance(field, str):
                    normalized = field.strip()
                    if normalized:
                        fields.append(normalized)
            if fields:
                break

    if not fields and column_name:
        fields = [column_name]

    unique_fields: list[str] = []
    seen_fields: set[str] = set()
    for field in fields:
        if field not in seen_fields:
            seen_fields.add(field)
            unique_fields.append(field)

    if not unique_fields:
        return []

    ignore_empty = bool(
        config.get("Ignorar vacios")
        or config.get("Ignorar vacíos")
        or config.get("Ignorar vacias")
        or config.get("Ignorar vacías")
        or config.get("Ignore empty")
        or config.get("Ignore empties")
    )

    return [
        {
            "fields": unique_fields,
            "message": normalized_message,
            "name": normalized_name,
            "ignore_empty": ignore_empty,
        }
    ]


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


def _apply_duplicate_rules(
    dataframe: DataFrame,
    duplicate_rules: Sequence[Mapping[str, Any]],
    observations: list[list[str]],
    row_is_valid: list[bool],
) -> None:
    if not duplicate_rules or not len(dataframe.index):
        return

    for rule in duplicate_rules:
        raw_fields = rule.get("fields")
        if not isinstance(raw_fields, Sequence):
            continue
        fields = [field for field in raw_fields if isinstance(field, str) and field]
        if not fields:
            continue

        missing_fields = [field for field in fields if field not in dataframe.columns]
        if missing_fields:
            detail = (
                f"{rule.get('name') or 'Regla de duplicados'}: "
                f"campos no encontrados ({', '.join(missing_fields)})"
            )
            for idx in range(len(observations)):
                observations[idx].append(detail)
                row_is_valid[idx] = False
            continue

        subset = dataframe[fields]
        duplicated_mask = subset.duplicated(keep=False)
        if not duplicated_mask.any():
            continue

        ignore_empty = bool(rule.get("ignore_empty"))
        if ignore_empty:
            non_empty_mask = subset.notna().any(axis=1)
            duplicated_mask = duplicated_mask & non_empty_mask

        if not duplicated_mask.any():
            continue

        message = rule.get("message") if isinstance(rule.get("message"), str) else None
        for idx in subset.index[duplicated_mask]:
            values = "; ".join(
                f"{field}={_format_duplicate_value(dataframe.at[idx, field])}"
                for field in fields
            )
            fallback = (
                f"Registros duplicados en campos {', '.join(fields)} ({values})"
            )
            observations[idx].append(_compose_error(message, fallback))
            row_is_valid[idx] = False


def _format_duplicate_value(value: Any) -> str:
    if value is None:
        return "vacío"
    return str(value)


_NORMALIZATION_STOPWORDS: set[str] = {
    "de",
    "del",
    "la",
    "el",
    "los",
    "las",
    "un",
    "una",
    "uno",
    "y",
    "the",
    "a",
}


def _normalize_type_label(label: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(label))
    ascii_label = "".join(char for char in normalized if not unicodedata.combining(char))
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", ascii_label)
    separated = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", separated)
    collapsed = re.sub(r"[\s\-_/]+", " ", separated)
    return collapsed.lower().strip()


def _tokenize_label(label: str) -> tuple[str, ...]:
    normalized = _normalize_type_label(label)
    if not normalized:
        return ()
    tokens = [
        token
        for token in normalized.split()
        if token and token not in _NORMALIZATION_STOPWORDS
    ]
    return tuple(tokens)


def _labels_match(raw_header: str, expected_normalized: str, expected_label: str | None) -> bool:
    normalized_header = _normalize_type_label(raw_header)
    if normalized_header == expected_normalized:
        return True
    if expected_label is None:
        return False
    return _tokenize_label(raw_header) == _tokenize_label(expected_label)


def _labels_equivalent(
    normalized_candidate: str,
    raw_candidate: str,
    expected_normalized: str,
    expected_label: str | None,
) -> bool:
    if normalized_candidate == expected_normalized:
        return True
    if expected_label is None:
        return False
    return _tokenize_label(raw_candidate) == _tokenize_label(expected_label)


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


def _validate_full_list_rule(
    *,
    value: Any,
    column_name: str,
    rule_config: Mapping[str, Any],
    message: str | None,
    row_context: Mapping[str, Any] | None,
    **_: Any,
) -> tuple[str, list[str]]:
    text_value = str(value)
    combinations = _extract_composite_combinations(rule_config)
    if not combinations:
        return text_value, []

    row_snapshot: Mapping[str, Any] = row_context or {}
    related_fields: set[str] = {column_name}
    for combination in combinations:
        related_fields.update(combination.keys())

    def _stringify(raw: Any) -> str | None:
        normalized = _normalize_cell_value(raw)
        if normalized is None:
            return None
        return str(normalized)

    current_values: dict[str, str | None] = {}
    for field in sorted(related_fields):
        raw_value = value if field == column_name else row_snapshot.get(field)
        text_related = _stringify(raw_value)
        current_values[field] = text_related
    missing_for_viable: set[str] = set()
    for combination in combinations:
        missing_fields = [field for field in combination if current_values.get(field) is None]
        if missing_fields:
            if all(
                current_values.get(field) == expected
                for field, expected in combination.items()
                if field not in missing_fields
            ):
                missing_for_viable.update(missing_fields)
            continue
        if all(current_values.get(field) == expected for field, expected in combination.items()):
            return text_value, []

    if missing_for_viable:
        missing = ", ".join(sorted(missing_for_viable))
        return text_value, [
            _compose_error(
                message,
                f"{column_name}: completa los campos relacionados ({missing})",
            )
        ]

    summary = "; ".join(
        " / ".join(f"{field}={expected}" for field, expected in combination.items())
        for combination in combinations
    )
    return text_value, [
        _compose_error(
            message,
            f"{column_name}: combinación no permitida ({summary})",
        )
    ]


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
    pd = _get_pandas_module()
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
    column_lookup: Mapping[str, str] | None = None,
    column_tokens: Mapping[str, tuple[str, ...]] | None = None,
    **_: Any,
) -> tuple[Any, list[str]]:
    fallback_value, fallback_errors = _apply_base_parser(
        value, column_name, base_parser, message
    )

    specific_rules = _extract_specific_dependency_rules(rule_config)

    if not isinstance(specific_rules, list) or not specific_rules:
        return fallback_value, fallback_errors

    dependent_name: str | None = None
    normalized_dependent_name: str | None = None

    for entry in specific_rules:
        if not isinstance(entry, Mapping) or len(entry) < 2:
            continue

        dependent_candidates = [
            key
            for key, candidate in entry.items()
            if isinstance(key, str)
            and key.strip()
            and not isinstance(candidate, Mapping)
        ]

        if not dependent_candidates:
            continue

        if len(dependent_candidates) > 1:
            dependent_name = None
            normalized_dependent_name = None
            break

        candidate_name = dependent_candidates[0]
        normalized_candidate = _normalize_type_label(candidate_name)

        if dependent_name is None:
            dependent_name = candidate_name
            normalized_dependent_name = normalized_candidate
        elif normalized_dependent_name != normalized_candidate:
            dependent_name = None
            normalized_dependent_name = None
            break

    if not dependent_name or not normalized_dependent_name:
        return fallback_value, fallback_errors

    found_dependent = False
    dependent_current: Any = None
    resolved_header: str | None = None
    for key, candidate in row_context.items():
        if isinstance(key, str) and _labels_match(
            key,
            normalized_dependent_name,
            dependent_name,
        ):
            dependent_current = candidate
            found_dependent = True
            resolved_header = key
            break

    if not found_dependent and column_lookup:
        mapped = column_lookup.get(normalized_dependent_name)
        if mapped and mapped in row_context:
            dependent_current = row_context.get(mapped)
            found_dependent = True
            resolved_header = mapped

    if not found_dependent and column_tokens:
        target_tokens = _tokenize_label(dependent_name)
        token_matches = [
            header
            for header, tokens in column_tokens.items()
            if header in row_context
            and tokens
            and tokens == target_tokens
        ]
        if not token_matches and target_tokens:
            target_set = set(target_tokens)
            token_matches = [
                header
                for header, tokens in column_tokens.items()
                if header in row_context
                and tokens
                and (
                    target_set.issubset(set(tokens))
                    or set(tokens).issubset(target_set)
                )
            ]
        if len(token_matches) == 1:
            resolved_header = token_matches[0]
            dependent_current = row_context.get(resolved_header)
            found_dependent = True

    if resolved_header and not _labels_match(
        resolved_header,
        normalized_dependent_name,
        dependent_name,
    ):
        dependent_name = resolved_header
        normalized_dependent_name = _normalize_type_label(resolved_header)

    if not found_dependent:
        return fallback_value, fallback_errors

    matched = False
    accumulated_errors: list[str] = []
    resulting_value = value

    for entry in specific_rules:
        if not isinstance(entry, Mapping) or len(entry) < 2:
            accumulated_errors.append(
                _compose_error(message, f"{column_name}: configuración dependiente inválida")
            )
            continue

        trigger_value: Any | None = None
        validators: list[tuple[str, Callable[[Any, str, Mapping[str, Any], str | None], tuple[Any, list[str]]], Mapping[str, Any]]] = []

        for raw_key, config in entry.items():
            if not isinstance(raw_key, str) or not raw_key.strip():
                accumulated_errors.append(
                    _compose_error(message, f"{column_name}: clave de dependencia inválida")
                )
                validators = []
                trigger_value = None
                break

            normalized_key = _normalize_type_label(raw_key)

            if _labels_equivalent(
                normalized_key,
                raw_key,
                normalized_dependent_name,
                dependent_name,
            ):
                trigger_value = config
                if isinstance(config, Mapping):
                    accumulated_errors.append(
                        _compose_error(
                            message,
                            f"{column_name}: el valor del campo dependiente '{raw_key}' no puede ser un objeto",
                        )
                    )
                    validators = []
                    trigger_value = None
                    break
                continue

            handler = _DEPENDENCY_RULE_HANDLERS.get(normalized_key)
            if handler is None:
                if (
                    normalized_key in _DEPENDENCY_METADATA_KEYS
                    or not isinstance(config, Mapping)
                ):
                    continue
                accumulated_errors.append(
                    _compose_error(
                        message,
                        f"{column_name}: tipo dependiente '{raw_key}' no soportado",
                    )
                )
                continue

            if not isinstance(config, Mapping):
                accumulated_errors.append(
                    _compose_error(
                        message,
                        f"{column_name}: la configuración asociada a '{raw_key}' debe ser un objeto",
                    )
                )
                continue

            validators.append((raw_key, handler, config))

        if trigger_value is None:
            accumulated_errors.append(
                _compose_error(
                    message,
                    f"{column_name}: falta indicar el valor para '{dependent_name}' en la configuración dependiente",
                )
            )
            continue

        if not _dependency_values_equal(dependent_current, trigger_value):
            continue

        matched = True
        candidate_value = value
        candidate_errors: list[str] = []

        for raw_key, handler, config in validators:
            candidate_value, dependency_errors = handler(
                candidate_value,
                column_name,
                config,
                message,
            )
            if dependency_errors:
                candidate_errors.extend(dependency_errors)

        if candidate_errors:
            accumulated_errors.extend(candidate_errors)
            continue

        resulting_value = candidate_value

    if accumulated_errors:
        return value, accumulated_errors

    if matched:
        return resulting_value, []

    return fallback_value, fallback_errors


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


def _dependency_document_validator(
    value: Any, column_name: str, rule_config: Mapping[str, Any], message: str | None
) -> tuple[str, list[str]]:
    return _validate_document_rule(
        value=value,
        column_name=column_name,
        rule_config=rule_config,
        message=message,
    )


def _dependency_list_validator(
    value: Any, column_name: str, rule_config: Mapping[str, Any], message: str | None
) -> tuple[str, list[str]]:
    return _validate_list_rule(
        value=value,
        column_name=column_name,
        rule_config=rule_config,
        message=message,
    )


def _dependency_full_list_validator(
    value: Any, column_name: str, rule_config: Mapping[str, Any], message: str | None
) -> tuple[str, list[str]]:
    return _validate_full_list_rule(
        value=value,
        column_name=column_name,
        rule_config=rule_config,
        message=message,
    )


def _dependency_phone_validator(
    value: Any, column_name: str, rule_config: Mapping[str, Any], message: str | None
) -> tuple[str, list[str]]:
    return _validate_phone_rule(
        value=value,
        column_name=column_name,
        rule_config=rule_config,
        message=message,
    )


def _dependency_email_validator(
    value: Any, column_name: str, rule_config: Mapping[str, Any], message: str | None
) -> tuple[str, list[str]]:
    return _validate_email_rule(
        value=value,
        column_name=column_name,
        rule_config=rule_config,
        message=message,
    )


def _dependency_date_validator(
    value: Any, column_name: str, rule_config: Mapping[str, Any], message: str | None
) -> tuple[date, list[str]]:
    return _validate_date_rule(
        value=value,
        column_name=column_name,
        rule_config=rule_config,
        message=message,
    )


def _dependency_values_equal(actual: Any, expected: Any) -> bool:
    normalized_actual = _normalize_cell_value(actual)
    normalized_expected = _normalize_cell_value(expected)

    if isinstance(normalized_actual, bool) or isinstance(normalized_expected, bool):
        return bool(normalized_actual) is bool(normalized_expected)

    numeric_types = (int, float, Decimal)
    if isinstance(normalized_actual, numeric_types) and isinstance(normalized_expected, numeric_types):
        try:
            return Decimal(str(normalized_actual)) == Decimal(str(normalized_expected))
        except (InvalidOperation, ValueError):
            return False

    if normalized_actual is None or normalized_expected is None:
        return normalized_actual is None and normalized_expected is None

    return _normalize_type_label(str(normalized_actual)) == _normalize_type_label(
        str(normalized_expected)
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


def _extract_specific_dependency_rules(
    rule_config: Mapping[str, Any]
) -> list[Mapping[str, Any]] | None:
    for key, value in rule_config.items():
        if isinstance(key, str) and _normalize_type_label(key) == "reglas especifica":
            if isinstance(value, list):
                return value
            return None

    fallback = rule_config.get("reglas especifica")
    if isinstance(fallback, list):
        return fallback

    # Algunas reglas generadas desde herramientas externas anidan la definición
    # específica dentro de otro bloque "Regla". Permitimos esa estructura para
    # mantener compatibilidad con reglas existentes.
    nested_candidates = [
        nested
        for key, nested in rule_config.items()
        if isinstance(key, str)
        and _normalize_type_label(key) == "regla"
        and isinstance(nested, Mapping)
    ]
    for nested in nested_candidates:
        extracted = _extract_specific_dependency_rules(nested)
        if extracted:
            return extracted

    return None


def _extract_composite_combinations(rule_config: Mapping[str, Any]) -> list[dict[str, str]]:
    candidate_keys = [
        "Lista compleja",
        "Lista",
        "Listas",
        "Combinaciones",
    ]
    for key in candidate_keys:
        raw_values = rule_config.get(key)
        if not isinstance(raw_values, list):
            continue
        combinations: list[dict[str, str]] = []
        for entry in raw_values:
            if not isinstance(entry, Mapping):
                continue
            normalized_entry: dict[str, str] = {}
            for campo, valor in entry.items():
                if not isinstance(campo, str):
                    continue
                field_name = campo.strip()
                if not field_name:
                    continue
                normalized_value = _normalize_cell_value(valor)
                if normalized_value is None:
                    continue
                if isinstance(normalized_value, (Mapping, Sequence)) and not isinstance(
                    normalized_value, (str, bytes)
                ):
                    continue
                normalized_entry[field_name] = str(normalized_value)
            if normalized_entry:
                combinations.append(normalized_entry)
        if combinations:
            return combinations
    return []


def _coerce_timestamp(value: Any) -> Any:
    pd = _get_pandas_module()
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
    pd = _get_pandas_module()
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
    pd = _get_pandas_module()
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
    "lista compleja": _parse_string,
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
    "lista compleja": _validate_full_list_rule,
    "telefono": _validate_phone_rule,
    "correo": _validate_email_rule,
    "fecha": _validate_date_rule,
    "dependencia": _validate_dependency_rule,
    "validacion conjunta": _validate_joint_rule,
}

_DEPENDENCY_METADATA_KEYS: set[str] = {
    "ejemplo",
    "ejemplos",
    "example",
    "examples",
    "descripcion",
    "descripcion general",
    "descripcion corta",
    "notas",
    "nota",
    "notes",
}

_DEPENDENCY_RULE_HANDLERS: dict[
    str, Callable[[Any, str, Mapping[str, Any], str | None], tuple[Any, list[str]]]
] = {
    "texto": _dependency_text_validator,
    "numero": _dependency_number_validator,
    "documento": _dependency_document_validator,
    "lista": _dependency_list_validator,
    "lista compleja": _dependency_full_list_validator,
    "telefono": _dependency_phone_validator,
    "correo": _dependency_email_validator,
    "fecha": _dependency_date_validator,
}


__all__ = [
    "get_load",
    "get_load_report",
    "get_load_original_file",
    "list_loads",
    "upload_template_load",
    "process_template_load",
]
