"""Domain exceptions. Each maps to an HTTP status in app.main."""


class AppError(Exception):
    status_code = 500
    code = "internal_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class StudentNotFoundError(AppError):
    status_code = 404
    code = "student_not_found"

    def __init__(self, student_id: int) -> None:
        super().__init__(f"Student with id {student_id} not found.")


class DuplicateEmailError(AppError):
    status_code = 409
    code = "duplicate_email"

    def __init__(self, email: str) -> None:
        super().__init__(f"A student with email '{email}' already exists.")


class InvalidAgeRangeError(AppError):
    status_code = 400
    code = "invalid_age_range"

    def __init__(self) -> None:
        super().__init__("min_age cannot be greater than max_age.")
