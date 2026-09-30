from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

BASE = "/students"


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def payload(**overrides):
    data = {
        "name": "Ravi Kumar",
        "email": "ravi@example.com",
        "phone": "+91 98765 43210",
        "age": 22,
        "course": "Python",
        "address": "Nellore, Andhra Pradesh",
    }
    return {**data, **overrides}


def test_create_and_get(client: TestClient):
    r = client.post(BASE, json=payload())
    assert r.status_code == 201
    body = r.json()
    assert body["student_id"] == 1 and body["created_at"]
    assert client.get(f"{BASE}/{body['student_id']}").json()["email"] == "ravi@example.com"


def test_optional_fields_can_be_omitted(client):
    r = client.post(BASE, json={"name": "Sita Devi", "email": "s@x.com", "age": 30, "course": "Java"})
    assert r.status_code == 201
    assert r.json()["phone"] is None and r.json()["address"] is None


def test_email_is_normalised_and_unique(client):
    client.post(BASE, json=payload(email="Ravi@Example.com"))
    r = client.post(BASE, json=payload(email="RAVI@example.com"))
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "duplicate_email"


@pytest.mark.parametrize("field", ["name", "email", "age", "course"])
def test_mandatory_fields(client, field):
    data = payload()
    del data[field]
    r = client.post(BASE, json=data)
    assert r.status_code == 422
    assert r.json()["error"]["details"][0]["field"] == field


@pytest.mark.parametrize("email", ["plainaddress", "a@", "@x.com", "a b@x.com"])
def test_invalid_email(client, email):
    assert client.post(BASE, json=payload(email=email)).status_code == 422


@pytest.mark.parametrize("age", [17, 61, 0, -5, "abc"])
def test_invalid_age(client, age):
    assert client.post(BASE, json=payload(age=age)).status_code == 422


@pytest.mark.parametrize("age", [18, 60])
def test_age_boundaries_ok(client, age):
    assert client.post(BASE, json=payload(age=age)).status_code == 201


@pytest.mark.parametrize("phone", ["12345", "abcdefghij", "1234567890123456", ""])
def test_invalid_phone(client, phone):
    assert client.post(BASE, json=payload(phone=phone)).status_code == 422


def test_blank_name_rejected(client):
    assert client.post(BASE, json=payload(name="   ")).status_code == 422


def test_list_and_pagination(client):
    for i in range(3):
        client.post(BASE, json=payload(email=f"s{i}@x.com"))
    assert len(client.get(BASE).json()) == 3
    assert len(client.get(BASE, params={"limit": 2}).json()) == 2
    assert client.get(BASE, params={"limit": 0}).status_code == 422


def test_search_by_course(client):
    client.post(BASE, json=payload(email="a@x.com", course="Python"))
    client.post(BASE, json=payload(email="b@x.com", course="Java"))
    rows = client.get(BASE, params={"course": "python"}).json()
    assert [r["email"] for r in rows] == ["a@x.com"]


def test_filter_by_age(client):
    for email, age in [("a@x.com", 20), ("b@x.com", 30), ("c@x.com", 40)]:
        client.post(BASE, json=payload(email=email, age=age))
    rows = client.get(BASE, params={"min_age": 20, "max_age": 30}).json()
    assert sorted(r["age"] for r in rows) == [20, 30]
    assert len(client.get(BASE, params={"min_age": 35}).json()) == 1


def test_combined_filters(client):
    client.post(BASE, json=payload(email="a@x.com", age=20, course="Python"))
    client.post(BASE, json=payload(email="b@x.com", age=35, course="Python"))
    client.post(BASE, json=payload(email="c@x.com", age=35, course="Java"))
    rows = client.get(BASE, params={"course": "Python", "min_age": 30}).json()
    assert [r["email"] for r in rows] == ["b@x.com"]


def test_invalid_age_range(client):
    r = client.get(BASE, params={"min_age": 40, "max_age": 20})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "invalid_age_range"


def test_not_found(client):
    for method, kwargs in [("get", {}), ("put", {"json": payload()}),
                           ("patch", {"json": {"age": 25}}), ("delete", {})]:
        r = getattr(client, method)(f"{BASE}/999", **kwargs)
        assert r.status_code == 404, method
        assert r.json()["error"]["code"] == "student_not_found"


def test_put_replaces_and_checks_duplicate_email(client):
    a = client.post(BASE, json=payload(email="a@x.com")).json()
    client.post(BASE, json=payload(email="b@x.com"))
    assert client.put(f"{BASE}/{a['student_id']}", json=payload(email="b@x.com")).status_code == 409
    r = client.put(f"{BASE}/{a['student_id']}", json=payload(email="a@x.com", age=28))
    assert r.status_code == 200 and r.json()["age"] == 28


def test_patch_partial_update(client):
    sid = client.post(BASE, json=payload()).json()["student_id"]
    r = client.patch(f"{BASE}/{sid}", json={"course": "FastAPI"})
    assert r.status_code == 200
    assert r.json()["course"] == "FastAPI" and r.json()["name"] == "Ravi Kumar"
    assert client.patch(f"{BASE}/{sid}", json={}).status_code == 422
    assert client.patch(f"{BASE}/{sid}", json={"age": None}).status_code == 422
    assert client.patch(f"{BASE}/{sid}", json={"age": 99}).status_code == 422


def test_delete(client):
    sid = client.post(BASE, json=payload()).json()["student_id"]
    assert client.delete(f"{BASE}/{sid}").status_code == 204
    assert client.get(f"{BASE}/{sid}").status_code == 404
    assert client.delete(f"{BASE}/{sid}").status_code == 404


def test_non_integer_id(client):
    assert client.get(f"{BASE}/abc").status_code == 422


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}
