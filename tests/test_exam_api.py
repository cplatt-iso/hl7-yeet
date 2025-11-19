import pytest

from app import create_app, schemas, crud
from app.extensions import db


def _configure_env(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("FLASK_SKIP_EVENTLET", "1")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")


@pytest.fixture
def flask_app(tmp_path, monkeypatch):
    _configure_env(tmp_path, monkeypatch)
    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        yield app
        db.session.remove()
        db.drop_all()


def _create_user_with_api_key():
    user = crud.create_user(
        db,
        schemas.UserCreate(
            username="examtester",
            email="exam@tester.example",
            password="Secret123!",
        ),
    )
    api_key_record, raw_key = crud.create_api_key(db, user.id, "Exam API key")
    return user, api_key_record, raw_key


def _auth_headers(raw_key: str) -> dict:
    return {"X-API-Key": raw_key}


def test_get_exam_spec_by_id(flask_app):
    with flask_app.app_context():
        _, _, raw_key = _create_user_with_api_key()
    client = flask_app.test_client()
    response = client.get(
        "/api/simulator/exams/CT-HEAD-WO",
        headers=_auth_headers(raw_key),
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["id"] == "CT-HEAD-WO"
    assert payload["modality"] == "CT"


def test_select_exam_spec_by_modality(flask_app):
    with flask_app.app_context():
        _, _, raw_key = _create_user_with_api_key()
    client = flask_app.test_client()
    response = client.post(
        "/api/simulator/exams/select",
        json={"modality": "MR"},
        headers=_auth_headers(raw_key),
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["modality"] == "MR"
    assert payload["_selection"]["strategy"] == "random"
    assert payload["_selection"]["filters"]["modality"] == "MR"


def test_list_exams_with_setting_filter(flask_app):
    with flask_app.app_context():
        _, _, raw_key = _create_user_with_api_key()
    client = flask_app.test_client()
    response = client.get(
        "/api/simulator/exams",
        query_string={"setting": "outpatient"},
        headers=_auth_headers(raw_key),
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["filters"] == {"setting": "outpatient"}
    assert payload["count"] == 1
    assert payload["exams"][0]["id"] == "MR-KNEE-RIGHT-WO"


def test_list_exam_modalities(flask_app):
    with flask_app.app_context():
        _, _, raw_key = _create_user_with_api_key()
    client = flask_app.test_client()
    response = client.get(
        "/api/simulator/exams/modalities",
        headers=_auth_headers(raw_key),
    )
    assert response.status_code == 200
    payload = response.get_json()
    codes = {item["code"] for item in payload["modalities"]}
    assert {"CT", "MR"}.issubset(codes)