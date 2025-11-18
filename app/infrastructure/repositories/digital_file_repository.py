"""Persistence helpers for digital files."""

from sqlalchemy.orm import Session

from app.domain.entities import DigitalFile
from app.infrastructure.models import DigitalFileModel
from app.utils import ensure_app_naive_datetime, now_in_app_timezone


class DigitalFileRepository:
    """Provide CRUD operations for digital files."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list(
        self,
        *,
        template_id: int | None = None,
        skip: int = 0,
        limit: int | None = None,
    ) -> list[DigitalFile]:
        query = self.session.query(DigitalFileModel)
        if template_id is not None:
            query = query.filter(DigitalFileModel.template_id == template_id)
        query = query.order_by(DigitalFileModel.created_at.desc())
        if skip:
            query = query.offset(skip)
        if limit is not None:
            query = query.limit(limit)
        models = query.all()
        return [self._to_entity(model) for model in models]

    def get(self, digital_file_id: int) -> DigitalFile | None:
        model = self.session.get(DigitalFileModel, digital_file_id)
        return self._to_entity(model) if model else None

    def get_by_template_id(self, template_id: int) -> DigitalFile | None:
        model = (
            self.session.query(DigitalFileModel)
            .filter(DigitalFileModel.template_id == template_id)
            .first()
        )
        return self._to_entity(model) if model else None

    def create(self, digital_file: DigitalFile) -> DigitalFile:
        model = DigitalFileModel()
        self._apply_entity_to_model(model, digital_file, include_creation_fields=True)
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        return self._to_entity(model)

    def update(self, digital_file: DigitalFile) -> DigitalFile:
        model = self.session.get(DigitalFileModel, digital_file.id)
        if model is None:
            msg = f"Digital file with id {digital_file.id} not found"
            raise ValueError(msg)
        self._apply_entity_to_model(model, digital_file, include_creation_fields=False)
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        return self._to_entity(model)

    def delete_by_template_id(self, template_id: int) -> None:
        self.session.query(DigitalFileModel).filter(
            DigitalFileModel.template_id == template_id
        ).delete(synchronize_session=False)
        self.session.commit()

    @staticmethod
    def _to_entity(model: DigitalFileModel) -> DigitalFile:
        return DigitalFile(
            id=model.id,
            template_id=model.template_id,
            name=model.name,
            description=model.description,
            path=model.path,
            created_by=model.created_by,
            created_at=ensure_app_naive_datetime(model.created_at),
            updated_by=model.updated_by,
            updated_at=ensure_app_naive_datetime(model.updated_at),
        )

    @staticmethod
    def _apply_entity_to_model(
        model: DigitalFileModel,
        digital_file: DigitalFile,
        *,
        include_creation_fields: bool,
    ) -> None:
        model.template_id = digital_file.template_id
        if include_creation_fields:
            model.created_by = digital_file.created_by
            model.created_at = (
                ensure_app_naive_datetime(digital_file.created_at)
                or ensure_app_naive_datetime(now_in_app_timezone())
            )
            model.updated_by = digital_file.updated_by
            model.updated_at = ensure_app_naive_datetime(digital_file.updated_at)
        model.name = digital_file.name
        model.description = digital_file.description
        model.path = digital_file.path
        if not include_creation_fields:
            model.updated_by = digital_file.updated_by
            model.updated_at = (
                ensure_app_naive_datetime(digital_file.updated_at)
                or ensure_app_naive_datetime(now_in_app_timezone())
            )


__all__ = ["DigitalFileRepository"]
