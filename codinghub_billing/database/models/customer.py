"""Customer / Student model (Section 11)."""
from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base, TimestampMixin


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    student_id: Mapped[str | None] = mapped_column(String(30), nullable=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    mobile: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    address: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    city: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    state: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    pincode: Mapped[str] = mapped_column(String(10), nullable=False, default="")
    gstin: Mapped[str | None] = mapped_column(String(15), nullable=True)
    pan: Mapped[str | None] = mapped_column(String(10), nullable=True)
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id"), nullable=True)
    enrollment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="Active")
    notes: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
