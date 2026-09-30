"""HTTP routes for /students."""
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db
from app.schemas import StudentCreate, StudentOut, StudentPatch

router = APIRouter(prefix="/students", tags=["Students"])

DB = Annotated[Session, Depends(get_db)]

_ERRORS = {
    400: {"description": "min_age is greater than max_age"},
    404: {"description": "Student not found"},
    409: {"description": "Email already in use"},
    422: {"description": "Validation error"},
}


@router.post(
    "",
    response_model=StudentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a student",
    responses={k: _ERRORS[k] for k in (409, 422)},
)
def add_student(payload: StudentCreate, db: DB):
    return crud.create_student(db, payload.model_dump())


@router.get(
    "",
    response_model=list[StudentOut],
    summary="Get all students (search by course, filter by age)",
    responses={k: _ERRORS[k] for k in (400, 422)},
)
def get_students(
    db: DB,
    course: Annotated[str | None, Query(description="Search by course (case-insensitive)")] = None,
    min_age: Annotated[int | None, Query(ge=0, description="Minimum age (inclusive)")] = None,
    max_age: Annotated[int | None, Query(ge=0, description="Maximum age (inclusive)")] = None,
    skip: Annotated[int, Query(ge=0, description="Records to skip")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Max records to return")] = 50,
):
    return crud.list_students(
        db, skip=skip, limit=limit, course=course, min_age=min_age, max_age=max_age
    )


@router.get(
    "/{student_id}",
    response_model=StudentOut,
    summary="Get a student by ID",
    responses={404: _ERRORS[404]},
)
def get_student(student_id: int, db: DB):
    return crud.get_student(db, student_id)


@router.put(
    "/{student_id}",
    response_model=StudentOut,
    summary="Replace a student (mandatory fields required)",
    responses={k: _ERRORS[k] for k in (404, 409, 422)},
)
def replace_student(student_id: int, payload: StudentCreate, db: DB):
    return crud.update_student(db, student_id, payload.model_dump())


@router.patch(
    "/{student_id}",
    response_model=StudentOut,
    summary="Partially update a student",
    responses={k: _ERRORS[k] for k in (404, 409, 422)},
)
def patch_student(student_id: int, payload: StudentPatch, db: DB):
    return crud.update_student(db, student_id, payload.model_dump(exclude_unset=True))


@router.delete(
    "/{student_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a student",
    responses={404: _ERRORS[404]},
)
def delete_student(student_id: int, db: DB):
    crud.delete_student(db, student_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
