from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from database.models.course import Course
from database.repositories.base_repository import BaseRepository


class CourseRepository(BaseRepository[Course]):
    def __init__(self, session: Session):
        super().__init__(session, Course)

    def count(self) -> int:
        return self.session.execute(select(func.count(Course.id))).scalar_one()

    def search(self, query: str = "", status: str | None = None, category: str | None = None) -> list[Course]:
        stmt = select(Course)
        if query:
            like = f"%{query.strip()}%"
            stmt = stmt.where(or_(Course.name.ilike(like), Course.category.ilike(like)))
        if status and status != "All":
            stmt = stmt.where(Course.status == status)
        if category and category != "All":
            stmt = stmt.where(Course.category == category)
        stmt = stmt.order_by(Course.name)
        return list(self.session.execute(stmt).scalars().all())

    def list_categories(self) -> list[str]:
        rows = self.session.execute(
            select(Course.category).where(Course.category != "").distinct().order_by(Course.category)
        ).scalars().all()
        return list(rows)
