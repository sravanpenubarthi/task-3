# Student Management API

A CRUD REST API for managing students, built with **FastAPI**, **SQLAlchemy 2.0** and **Pydantic v2**.
Uses **SQLite** (zero setup); switch to another database with the `DATABASE_URL` environment variable.

## Project structure

```
student_management/
├── app/
│   ├── main.py            # app factory, lifespan, global error handlers
│   ├── config.py          # env-based configuration (DATABASE_URL)
│   ├── database.py        # engine, session, get_db dependency
│   ├── models.py          # SQLAlchemy model (Student)
│   ├── schemas.py         # Pydantic request/response schemas + validation rules
│   ├── crud.py            # database operations (no HTTP concerns)
│   ├── exceptions.py      # domain errors -> HTTP status mapping
│   └── routers/students.py    # route definitions
├── tests/test_students.py     # 34 pytest tests (in-memory SQLite)
├── schema.sql                 # database schema (DDL)
├── postman_collection.json    # importable Postman collection with test scripts
└── requirements.txt
```

Layering: **router -> crud -> model**. Routers handle HTTP, `crud` handles data, `schemas` handle validation.

## Setup & run

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

- Interactive docs (Swagger UI): http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
- The SQLite file `students.db` and the table are created automatically on startup.

### Run tests

```bash
pytest -q
```

## Database schema

Table `students` (see `schema.sql`):

| Column     | Type          | Constraints                          |
|------------|---------------|--------------------------------------|
| student_id | INTEGER       | PRIMARY KEY, auto-increment (unique) |
| name       | VARCHAR(100)  | NOT NULL                             |
| email      | VARCHAR(255)  | NOT NULL, **UNIQUE**                 |
| phone      | VARCHAR(20)   | optional                             |
| age        | INTEGER       | NOT NULL, CHECK 18-60                |
| course     | VARCHAR(100)  | NOT NULL, indexed                    |
| address    | VARCHAR(255)  | optional                             |
| created_at | DATETIME      | NOT NULL, default now                |

## API reference

| Method | Path                 | Description                                   | Success | Errors             |
|--------|----------------------|-----------------------------------------------|---------|--------------------|
| POST   | `/students`          | Add student                                   | 201     | 409, 422           |
| GET    | `/students`          | List students (`course`, `min_age`, `max_age`, `skip`, `limit`) | 200 | 400, 422 |
| GET    | `/students/{id}`     | Get student by ID                             | 200     | 404, 422           |
| PUT    | `/students/{id}`     | Replace student (mandatory fields required)   | 200     | 404, 409, 422      |
| PATCH  | `/students/{id}`     | Partial update                                | 200     | 404, 409, 422      |
| DELETE | `/students/{id}`     | Delete student                                | 204     | 404                |
| GET    | `/health`            | Liveness check                                | 200     |                    |

**Bonus (query parameters on `GET /students`)**

- Search by course: `GET /students?course=Python` (case-insensitive)
- Filter by age: `GET /students?min_age=20&max_age=30` (inclusive)
- Filters can be combined: `GET /students?course=Python&min_age=20`

### Example

```bash
curl -X POST http://127.0.0.1:8000/students \
  -H "Content-Type: application/json" \
  -d '{"name":"Ravi Kumar","email":"ravi.kumar@example.com","phone":"+91 98765 43210",
       "age":22,"course":"Python","address":"Nellore, Andhra Pradesh"}'
```

```json
{
  "student_id": 1,
  "name": "Ravi Kumar",
  "email": "ravi.kumar@example.com",
  "phone": "+91 98765 43210",
  "age": 22,
  "course": "Python",
  "address": "Nellore, Andhra Pradesh",
  "created_at": "2026-09-30T07:40:12.123456Z"
}
```

### Validation rules

- `name`, `email`, `age`, `course` are **mandatory** on POST/PUT. `phone` and `address` are optional.
- `email`: valid format; stored lower-cased; **unique** (case-insensitive) -> `409` on conflict.
- `age`: integer between **18 and 60**.
- `phone`: 10-15 digits, with optional leading `+`, spaces or hyphens.
- Text fields: whitespace trimmed, must not be blank; `name` 2-100 chars.
- `PATCH`: at least one field, no explicit `null` for mandatory fields.
- `limit` must be 1-100, `skip` >= 0, `min_age` must not exceed `max_age`.

### Error format

Every error uses one consistent envelope:

```json
{ "error": { "code": "duplicate_email", "message": "A student with email 'ravi.kumar@example.com' already exists." } }
```

Validation errors (`422`) add per-field details:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed.",
    "details": [ { "field": "age", "message": "Input should be greater than or equal to 18" } ]
  }
}
```

| Code                | HTTP |
|---------------------|------|
| `validation_error`  | 422  |
| `student_not_found` | 404  |
| `duplicate_email`   | 409  |
| `invalid_age_range` | 400  |
| `internal_error`    | 500  |

## Testing

### Swagger UI
Open `/docs`, expand an endpoint, click **Try it out**, then **Execute**.

### Postman
Import `postman_collection.json`. It uses two collection variables (`base_url`, `student_id`); the
"Add student" request stores the new ID automatically. Run the collection top to bottom with the
Collection Runner: each request includes assertions on status codes.

### Test checklist

| # | Case                          | Expected        |
|---|-------------------------------|-----------------|
| 1 | Create a student              | 201             |
| 2 | Get all students              | 200             |
| 3 | Get student by ID             | 200             |
| 4 | Update student (PUT / PATCH)  | 200             |
| 5 | Delete student                | 204             |
| 6 | Search by course              | 200, filtered   |
| 7 | Filter by age                 | 200, filtered   |
| 8 | Invalid email                 | 422             |
| 9 | Invalid age (17 / 61)         | 422             |
| 10 | Duplicate email              | 409             |
| 11 | Non-existing student         | 404             |

## Design notes

- **Uniqueness is enforced twice**: an application-level check (friendly 409) and a DB `UNIQUE` constraint
  (protects against race conditions; `IntegrityError` is translated to the same 409).
- **Emails are normalised to lower-case** so `A@x.com` and `a@x.com` cannot both exist.
- **Age is validated twice**: by Pydantic (friendly 422) and by a DB `CHECK` constraint.
- **PUT vs PATCH**: PUT replaces the whole resource, PATCH updates only supplied fields.
- **Pagination** on the list endpoint prevents unbounded responses.
- **Out of scope (intentionally)**: authentication, Alembic migrations, soft deletes. `create_all` on startup
  is fine for this task; use Alembic for production schema changes.
