"""Database access layer. No HTTP concerns live here."""
from typing import cast

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import DuplicateEmailError, InvalidAgeRangeError, StudentNotFoundError
from app.models import Student


def _commit(db: Session, email: str | None = None) -> None:
    """Commit; translate a unique-constraint race into a DuplicateEmailError."""
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DuplicateEmailError(email or "unknown") from None


def _email_taken(db: Session, email: str, exclude_id: int | None = None) -> bool:
    stmt = select(Student.student_id).where(Student.email == email)
    if exclude_id is not None:
        stmt = stmt.where(Student.student_id != exclude_id)
    return db.scalar(stmt) is not None


def list_students(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    course: str | None = None,
    min_age: int | None = None,
    max_age: int | None = None,
) -> list[Student]:
    if min_age is not None and max_age is not None and min_age > max_age:
        raise InvalidAgeRangeError()
    stmt = select(Student)
    if course:
        stmt = stmt.where(func.lower(Student.course) == course.strip().lower())
    if min_age is not None:
        stmt = stmt.where(Student.age >= min_age)
    if max_age is not None:
        stmt = stmt.where(Student.age <= max_age)
    stmt = stmt.order_by(Student.student_id).offset(skip).limit(limit)
    return list(db.scalars(stmt))


def get_student(db: Session, student_id: int) -> Student:
    student = db.get(Student, student_id)
    if student is None:
        raise StudentNotFoundError(student_id)
    return student


def create_student(db: Session, data: dict[str, object]) -> Student:
    email = cast(str, data["email"])
    if _email_taken(db, email):
        raise DuplicateEmailError(email)
    student = Student(**data)
    db.add(student)
    _commit(db, email)
    db.refresh(student)
    return student


def update_student(db: Session, student_id: int, changes: dict[str, object]) -> Student:
    student = get_student(db, student_id)
    new_email = changes.get("email")
    if isinstance(new_email, str) and _email_taken(db, new_email, exclude_id=student_id):
        raise DuplicateEmailError(new_email)
    for field, value in changes.items():
        setattr(student, field, value)
    _commit(db, new_email if isinstance(new_email, str) else None)
    db.refresh(student)
    return student


def delete_student(db: Session, student_id: int) -> None:
    student = get_student(db, student_id)
    db.delete(student)
    db.commit()
