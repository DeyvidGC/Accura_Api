"""Schemas for KPI endpoints."""

from pydantic import BaseModel, Field

try:  # pragma: no cover - compatibility with pydantic v1/v2
    from pydantic import ConfigDict
except ImportError:  # pragma: no cover - fallback for pydantic v1
    ConfigDict = None  # type: ignore[misc]


class MonthlyComparisonRead(BaseModel):
    current_month: int = Field(..., description="Valor registrado en el mes en curso")
    previous_month: int = Field(
        ..., description="Valor registrado en el mes inmediatamente anterior"
    )

    if ConfigDict is not None:  # pragma: no branch - runtime configuration
        model_config = ConfigDict(from_attributes=True)
    else:  # pragma: no cover - compatibility path for pydantic v1
        class Config:
            orm_mode = True


class TemplatePublicationSummaryRead(BaseModel):
    total: int = Field(..., description="Cantidad total de plantillas registradas")
    published: int = Field(..., description="Cantidad de plantillas publicadas")
    unpublished: int = Field(..., description="Cantidad de plantillas no publicadas")
    active: int = Field(..., description="Cantidad de plantillas activas")

    if ConfigDict is not None:  # pragma: no branch - runtime configuration
        model_config = ConfigDict(from_attributes=True)
    else:  # pragma: no cover - compatibility path for pydantic v1
        class Config:
            orm_mode = True


class ValidationEffectivenessRead(BaseModel):
    successful: int = Field(..., description="Total de validaciones exitosas en el mes")
    total: int = Field(..., description="Total de validaciones completadas en el mes")
    effectiveness_percentage: float = Field(
        ..., description="Porcentaje de efectividad de las validaciones en el mes"
    )

    if ConfigDict is not None:  # pragma: no branch - runtime configuration
        model_config = ConfigDict(from_attributes=True)
    else:  # pragma: no cover - compatibility path for pydantic v1
        class Config:
            orm_mode = True


class RuleSummaryRead(BaseModel):
    total: int = Field(..., description="Cantidad total de reglas registradas")
    active: int = Field(..., description="Cantidad de reglas activas")
    assigned: int = Field(
        ..., description="Cantidad de reglas asignadas a columnas de plantillas"
    )

    if ConfigDict is not None:  # pragma: no branch - runtime configuration
        model_config = ConfigDict(from_attributes=True)
    else:  # pragma: no cover - compatibility path for pydantic v1
        class Config:
            orm_mode = True


class HistorySnapshotRead(BaseModel):
    total_loads: int = Field(..., description="Cantidad total de cargas realizadas")
    active_users: int = Field(
        ..., description="Cantidad de usuarios activos pertenecientes al administrador"
    )
    processed_rows: int = Field(
        ..., description="Cantidad total de filas procesadas en las cargas"
    )

    if ConfigDict is not None:  # pragma: no branch - runtime configuration
        model_config = ConfigDict(from_attributes=True)
    else:  # pragma: no cover - compatibility path for pydantic v1
        class Config:
            orm_mode = True


class KPIReportRead(BaseModel):
    active_users: MonthlyComparisonRead
    templates: TemplatePublicationSummaryRead
    loads: MonthlyComparisonRead
    validations: ValidationEffectivenessRead
    rules: RuleSummaryRead
    history: HistorySnapshotRead

    if ConfigDict is not None:  # pragma: no branch - runtime configuration
        model_config = ConfigDict(from_attributes=True)
    else:  # pragma: no cover - compatibility path for pydantic v1
        class Config:
            orm_mode = True


__all__ = [
    "KPIReportRead",
    "MonthlyComparisonRead",
    "TemplatePublicationSummaryRead",
    "ValidationEffectivenessRead",
    "RuleSummaryRead",
    "HistorySnapshotRead",
]
