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
        schemas.UserCreate(username="apitester", email="api@tester.example", password="Secret123!"),
    )
    api_key_record, raw_key = crud.create_api_key(db, user.id, "CLI key")
    return user, api_key_record, raw_key


def test_api_key_authentication_allows_access(flask_app):
    with flask_app.app_context():
        user, record, raw_key = _create_user_with_api_key()
        prefix = record.key_prefix
    client = flask_app.test_client()
    response = client.get("/api/templates", headers={"X-API-Key": raw_key})
    assert response.status_code == 200
    assert response.get_json() == []

    with flask_app.app_context():
        refreshed = crud.get_api_key_by_prefix(db, prefix)
        assert refreshed is not None
        assert refreshed.last_used is not None


def test_authorization_header_api_key(flask_app):
    with flask_app.app_context():
        _, _, raw_key = _create_user_with_api_key()
    client = flask_app.test_client()
    response = client.get("/api/templates", headers={"Authorization": f"ApiKey {raw_key}"})
    assert response.status_code == 200
