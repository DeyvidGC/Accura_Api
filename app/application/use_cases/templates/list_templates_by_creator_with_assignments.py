"""Use case for listing templates created by an administrator along with assignments."""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.domain.entities import Template, TemplateUserAccess, User
from app.infrastructure.repositories import (
    TemplateRepository,
    TemplateUserAccessRepository,
    UserRepository,
)


def list_templates_by_creator_with_assignments(
    session: Session,
    *,
    creator_id: int,
) -> Sequence[tuple[Template, User | None, Sequence[User]]]:
    """Return templates created by ``creator_id`` with their assigned users."""

    template_repository = TemplateRepository(session)
    access_repository = TemplateUserAccessRepository(session)
    user_repository = UserRepository(session)

    templates = list(template_repository.list_by_creator(creator_id))
    if not templates:
        return []

    assignment_map: dict[int, list[TemplateUserAccess]] = {}
    assigned_user_ids: set[int] = set()
    for template in templates:
        accesses = list(
            access_repository.list_by_template(
                template.id, include_inactive=False
            )
        )
        assignment_map[template.id] = accesses
        for access in accesses:
            assigned_user_ids.add(access.user_id)

    user_ids: set[int] = set(assigned_user_ids)
    for template in templates:
        if template.created_by is not None:
            user_ids.add(template.created_by)
    users = user_repository.get_map_by_ids(user_ids)

    overview: list[tuple[Template, User | None, list[User]]] = []
    for template in templates:
        creator = (
            users.get(template.created_by)
            if template.created_by is not None
            else None
        )
        assigned_users: list[User] = []
        for access in assignment_map.get(template.id, []):
            user = users.get(access.user_id)
            if user is not None:
                assigned_users.append(user)
        overview.append((template, creator, assigned_users))

    return overview


__all__ = ["list_templates_by_creator_with_assignments"]
