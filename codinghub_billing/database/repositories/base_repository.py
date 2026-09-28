"""Generic CRUD repository. Concrete repositories subclass this instead of
hand-rolling SQL/ORM queries in services or GUI code (Section 3 layering)."""
from __future__ import annotations

from typing import Generic, Sequence, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    model: Type[ModelT]

    def __init__(self, session: Session, model: Type[ModelT] | None = None):
        self.session = session
        if model is not None:
            self.model = model

    def get(self, id_: int) -> ModelT | None:
        return self.session.get(self.model, id_)

    def list(self) -> Sequence[ModelT]:
        return self.session.execute(select(self.model)).scalars().all()

    def add(self, instance: ModelT) -> ModelT:
        self.session.add(instance)
        self.session.flush()
        return instance

    def update(self, instance: ModelT) -> ModelT:
        self.session.add(instance)
        self.session.flush()
        return instance

    def delete(self, instance: ModelT) -> None:
        self.session.delete(instance)
        self.session.flush()
