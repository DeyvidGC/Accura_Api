"""Persistence layer for generated load report files."""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.domain.entities import LoadedFile
from app.infrastructure.models import LoadedFileModel
from app.utils import ensure_app_timezone, now_in_app_timezone


class LoadedFileRepository:
    """Provide CRUD-style operations for :class:`LoadedFile` records."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_for_user(self, user_id: int) -> Sequence[LoadedFile]:
        query = (
            self.session.query(LoadedFileModel)
            .filter(LoadedFileModel.created_user_id == user_id)
            .order_by(desc(LoadedFileModel.created_at), desc(LoadedFileModel.id))
        )
        return [self._to_entity(model) for model in query.all()]

    def get_latest_by_load(self, load_id: int) -> LoadedFile | None:
        query = (
            self.session.query(LoadedFileModel)
            .filter(LoadedFileModel.load_id == load_id)
            .order_by(desc(LoadedFileModel.created_at), desc(LoadedFileModel.id))
        )
        model = query.first()
        return self._to_entity(model) if model else None

    def create(self, loaded_file: LoadedFile) -> LoadedFile:
        model = LoadedFileModel()
        self._apply_entity_to_model(model, loaded_file)
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        return self._to_entity(model)

    @staticmethod
    def _to_entity(model: LoadedFileModel) -> LoadedFile:
        return LoadedFile(
            id=model.id,
            load_id=model.load_id,
            name=model.name,
            path=model.path,
            size_bytes=model.size_bytes,
            num_load=model.num_load,
            created_user_id=model.created_user_id,
            created_at=ensure_app_timezone(model.created_at),
        )

    @staticmethod
    def _apply_entity_to_model(model: LoadedFileModel, loaded_file: LoadedFile) -> None:
        model.load_id = loaded_file.load_id
        model.name = loaded_file.name
        model.path = loaded_file.path
        model.size_bytes = loaded_file.size_bytes
        model.num_load = loaded_file.num_load
        model.created_user_id = loaded_file.created_user_id
        if loaded_file.created_at is not None:
            model.created_at = ensure_app_timezone(loaded_file.created_at)
        else:
            model.created_at = now_in_app_timezone()


__all__ = ["LoadedFileRepository"]
