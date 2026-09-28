from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from database.models.user import Permission, Role, User
from database.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: Session):
        super().__init__(session, User)

    def get_by_username(self, username: str) -> User | None:
        stmt = select(User).where(User.username == username)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return self.session.execute(stmt).scalar_one_or_none()

    def count(self) -> int:
        return len(self.list())

    def search(self, query: str = "", role_id: int | None = None) -> list[User]:
        stmt = select(User)
        if query:
            like = f"%{query.strip()}%"
            stmt = stmt.where(or_(User.username.ilike(like), User.full_name.ilike(like), User.email.ilike(like)))
        if role_id:
            stmt = stmt.where(User.role_id == role_id)
        stmt = stmt.order_by(User.full_name)
        return list(self.session.execute(stmt).scalars().all())

    def count_active_admins(self, admin_role_id: int, exclude_user_id: int | None = None) -> int:
        stmt = select(func.count()).select_from(User).where(User.role_id == admin_role_id, User.is_active.is_(True))
        if exclude_user_id:
            stmt = stmt.where(User.id != exclude_user_id)
        return self.session.execute(stmt).scalar_one()


class RoleRepository(BaseRepository[Role]):
    def __init__(self, session: Session):
        super().__init__(session, Role)

    def get_by_name(self, name: str) -> Role | None:
        stmt = select(Role).where(Role.name == name)
        return self.session.execute(stmt).scalar_one_or_none()


class PermissionRepository(BaseRepository[Permission]):
    def __init__(self, session: Session):
        super().__init__(session, Permission)

    def get_by_code(self, code: str) -> Permission | None:
        stmt = select(Permission).where(Permission.code == code)
        return self.session.execute(stmt).scalar_one_or_none()
