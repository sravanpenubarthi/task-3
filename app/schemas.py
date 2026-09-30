"""Pydantic schemas: request validation and response serialisation."""
import re
from datetime import datetime
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    model_validator,
)


def _check_phone(value: str) -> str:
    if not re.fullmatch(r"\+?[0-9][0-9 \-]*", value):
        raise ValueError("Phone may contain only digits, spaces, hyphens and a leading '+'.")
    if not 10 <= len(re.sub(r"\D", "", value)) <= 15:
        raise ValueError("Phone must contain 10 to 15 digits.")
    return value


# Reusable field types keep Create / Patch schemas consistent.
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]
Email = Annotated[EmailStr, AfterValidator(str.lower)]  # emails are stored lower-cased
Phone = Annotated[str, StringConstraints(strip_whitespace=True, max_length=20), AfterValidator(_check_phone)]
Age = Annotated[int, Field(ge=18, le=60)]
Course = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Address = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]


class StudentCreate(BaseModel):
    """Payload for POST and PUT. name, email, age and course are mandatory."""

    name: Name
    email: Email
    phone: Phone | None = None
    age: Age
    course: Course
    address: Address | None = None


class StudentPatch(BaseModel):
    """Payload for PATCH: send only the fields to change."""

    name: Name | None = None
    email: Email | None = None
    phone: Phone | None = None
    age: Age | None = None
    course: Course | None = None
    address: Address | None = None

    @model_validator(mode="after")
    def _check_fields(self) -> "StudentPatch":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")
        required = {"name", "email", "age", "course"}
        nulls = [f for f in self.model_fields_set & required if getattr(self, f) is None]
        if nulls:
            raise ValueError(f"Fields cannot be null: {', '.join(sorted(nulls))}.")
        return self


class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    student_id: int
    name: str
    email: str
    phone: str | None
    age: int
    course: str
    address: str | None
    created_at: datetime
