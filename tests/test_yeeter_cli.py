import json
from pathlib import Path

import click
from click.testing import CliRunner

from scripts import yeeter_cli


def _set_config_path(monkeypatch, config_path: Path):
    monkeypatch.setenv("YEETER_CONFIG_PATH", str(config_path))
    yeeter_cli.CONFIG_PATH = config_path
    yeeter_cli.CONFIG_DIR = config_path.parent


def test_cli_login_caches_token(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    _set_config_path(monkeypatch, config_path)
    monkeypatch.setenv("YEETER_API_URL", "https://example.com")

    def fake_post_json(self, path, payload, **kwargs):
        assert path == "/api/auth/login"
        assert payload == {"username": "user", "password": "pass"}
        return {"access_token": "abc123", "username": "user", "is_admin": True}

    monkeypatch.setattr(yeeter_cli.YeeterClient, "post_json", fake_post_json, raising=False)

    runner = CliRunner()
    result = runner.invoke(yeeter_cli.cli, ["login", "--username", "user", "--password", "pass"])

    assert result.exit_code == 0
    data = json.loads(config_path.read_text())
    assert data["access_token"] == "abc123"
    assert data["username"] == "user"
    assert data["is_admin"] is True
    assert data["auth_method"] == "jwt"
    assert "api_key" not in data


def test_cli_api_key_command_stores_and_clears_key(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    _set_config_path(monkeypatch, config_path)
    monkeypatch.setenv("YEETER_API_URL", "https://example.com")

    runner = CliRunner()
    key_value = "ytr_example_api_key_value_123456"
    store_result = runner.invoke(yeeter_cli.cli, ["api-key", "--value", key_value])
    assert store_result.exit_code == 0

    data = json.loads(config_path.read_text())
    assert data["api_key"] == key_value
    assert data["auth_method"] == "api_key"

    clear_result = runner.invoke(yeeter_cli.cli, ["api-key", "--clear"])
    assert clear_result.exit_code == 0
    cleared = json.loads(config_path.read_text())
    assert "api_key" not in cleared


def test_cli_runs_stats_json_output(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    _set_config_path(monkeypatch, config_path)

    stats_payload = {
        "run_id": 42,
        "user_id": 1,
        "template_id": 7,
        "patient_count": 3,
        "status": "COMPLETED",
        "started_at": "2025-01-01T12:00:00Z",
        "completed_at": "2025-01-01T12:01:00Z",
        "duration_seconds": 60.0,
        "first_event_at": "2025-01-01T12:00:10Z",
        "last_event_at": "2025-01-01T12:00:55Z",
        "total_events": 10,
        "success_events": 9,
        "failure_events": 1,
        "warning_events": 0,
        "info_events": 0,
        "debug_events": 0,
        "unique_steps": 4,
        "max_iteration": 3,
        "last_failure": None,
        "steps": [],
    }

    class DummyClient:
        def get_json(self, path, **kwargs):
            assert path == "/api/simulator/runs/42/stats"
            return stats_payload

    def fake_get_client(ctx):
        return DummyClient(), {"access_token": "token"}

    monkeypatch.setattr(yeeter_cli, "_get_authenticated_client", fake_get_client)

    runner = CliRunner()
    result = runner.invoke(yeeter_cli.cli, ["runs", "stats", "42", "--format", "json"])

    assert result.exit_code == 0
    assert "\"run_id\": 42" in result.output
    assert "duration_seconds" in result.output


def test_cli_runs_cancel_invokes_endpoint(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    _set_config_path(monkeypatch, config_path)

    class DummyClient:
        def post_json(self, path, payload, **kwargs):
            assert path == "/api/simulator/runs/7/cancel"
            assert payload == {}
            return {"message": "Cancellation requested.", "run_id": 7}

    def fake_get_client(ctx):
        return DummyClient(), {}

    monkeypatch.setattr(yeeter_cli, "_get_authenticated_client", fake_get_client)

    runner = CliRunner()
    result = runner.invoke(yeeter_cli.cli, ["runs", "cancel", "7"])

    assert result.exit_code == 0
    assert "Cancellation requested." in result.output


def test_cli_runs_start_json_output(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    _set_config_path(monkeypatch, config_path)

    class DummyClient:
        def post_json(self, path, payload, **kwargs):
            assert path == "/api/simulator/run"
            assert payload == {"template_id": 5, "patient_count": 3}
            return {"run_id": 314, "message": "Simulation run initiated successfully."}

    def fake_get_client(ctx):
        return DummyClient(), {}

    monkeypatch.setattr(yeeter_cli, "_get_authenticated_client", fake_get_client)

    runner = CliRunner()
    result = runner.invoke(yeeter_cli.cli, ["runs", "start", "--template-id", "5", "--patients", "3", "--output", "json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["run_id"] == 314
    assert payload["template_id"] == 5
    assert payload["patient_count"] == 3
    assert "message" in payload


def test_cli_templates_list_table_output(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    _set_config_path(monkeypatch, config_path)

    class DummyClient:
        def get_json(self, path, **kwargs):
            assert path == "/api/simulator/templates"
            return [
                {"id": 1, "name": "Template One"},
                {"id": 2, "name": "Template Two"},
            ]

    def fake_get_client(ctx):
        return DummyClient(), {}

    monkeypatch.setattr(yeeter_cli, "_get_authenticated_client", fake_get_client)

    runner = CliRunner()
    result = runner.invoke(yeeter_cli.cli, ["templates", "list"])

    assert result.exit_code == 0
    assert "ID  | Name" in result.output
    assert "  1 | Template One" in result.output
    assert "  2 | Template Two" in result.output


def test_cli_templates_list_json_output(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    _set_config_path(monkeypatch, config_path)

    payload = [
        {"id": 9, "name": "Template Nine"}
    ]

    class DummyClient:
        def get_json(self, path, **kwargs):
            assert path == "/api/simulator/templates"
            return payload

    def fake_get_client(ctx):
        return DummyClient(), {}

    monkeypatch.setattr(yeeter_cli, "_get_authenticated_client", fake_get_client)

    runner = CliRunner()
    result = runner.invoke(yeeter_cli.cli, ["templates", "list", "--output", "json"])

    assert result.exit_code == 0
    assert json.dumps(payload, indent=2) in result.output


def test_get_authenticated_client_prefers_api_key(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    _set_config_path(monkeypatch, config_path)

    config_path.write_text(
        json.dumps({
            "api_key": "ytr_sample_key_for_headers_999",
            "api_url": "https://example.com"
        })
    )

    ctx = click.Context(yeeter_cli.cli)
    ctx.obj = {"api_url": "https://example.com", "verify_tls": True}

    client, config = yeeter_cli._get_authenticated_client(ctx)

    assert "X-API-Key" in client.session.headers
    assert client.session.headers["X-API-Key"] == "ytr_sample_key_for_headers_999"
    assert "Authorization" not in client.session.headers
    assert config["api_key"].startswith("ytr_sample_key_for_headers")