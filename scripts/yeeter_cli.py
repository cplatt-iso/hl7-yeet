#!/usr/bin/env python3
# --- START OF FILE scripts/yeeter_cli.py ---
"""Command-line utilities for interacting with the HL7 Yeeter simulator API."""

from __future__ import annotations

import csv
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Tuple

import click
import requests

DEFAULT_API_URL = os.environ.get("YEETER_API_URL", "https://yeet.trazen.org")

_config_path_override = os.environ.get("YEETER_CONFIG_PATH")
if _config_path_override:
    CONFIG_PATH = Path(_config_path_override).expanduser()
else:
    CONFIG_PATH = Path.home() / ".yeeter" / "config.json"
CONFIG_DIR = CONFIG_PATH.parent
USER_AGENT = "YeeterCLI/1.0"
TERMINAL_STATUSES = {"COMPLETED", "ERROR", "FAILED", "CANCELLED"}


class ApiError(click.ClickException):
    """Raised when the Yeeter API returns a non-success response."""

    exit_code = 1


class AuthenticationRequired(click.ClickException):
    """Raised when no cached credentials are available."""

    exit_code = 2


def _load_config() -> Dict[str, Any]:
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    return {}


def _save_config(data: Dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with CONFIG_PATH.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)


class YeeterClient:
    """Lightweight HTTP client for talking to the HL7 Yeeter API."""

    def __init__(self, api_url: str, token: str | None = None, api_key: str | None = None, verify_tls: bool = True):
        self.api_url = api_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.session.verify = verify_tls
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        if api_key:
            self.session.headers.update({"X-API-Key": api_key})

    def request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        url = f"{self.api_url}{path}"
        timeout = kwargs.pop("timeout", 30)
        try:
            response = self.session.request(method, url, timeout=timeout, **kwargs)
        except requests.RequestException as exc:
            raise ApiError(f"Failed to reach {url}: {exc}") from exc

        if response.status_code == 401:
            raise AuthenticationRequired("Authentication failed. Run 'yeeter-cli login' again.")
        if response.status_code >= 400:
            message = _extract_error_message(response)
            raise ApiError(f"{method} {path} -> {response.status_code}: {message}")
        return response

    def get_json(self, path: str, **kwargs: Any) -> Dict[str, Any]:
        response = self.request("GET", path, **kwargs)
        return response.json()

    def post_json(self, path: str, payload: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        response = self.request("POST", path, json=payload, **kwargs)
        if response.status_code == 202:
            # 202 Accepted still carries JSON body
            return response.json()
        return response.json()


def _extract_error_message(response: requests.Response) -> str:
    try:
        data = response.json()
    except ValueError:
        return response.text or "(no error payload)"

    if isinstance(data, dict):
        for key in ("error", "message", "detail", "msg"):
            if key in data and data[key]:
                return str(data[key])
    return json.dumps(data)


def _get_authenticated_client(ctx: click.Context) -> Tuple[YeeterClient, Dict[str, Any]]:
    config = _load_config()
    api_key = config.get("api_key")
    token = config.get("access_token")
    if not api_key and not token:
        raise AuthenticationRequired("No cached credentials. Run 'yeeter-cli login' or 'yeeter-cli api-key'.")

    api_url = ctx.obj["api_url"]
    verify_tls = ctx.obj["verify_tls"]
    if config.get("api_url") and config["api_url"] != api_url:
        click.echo(
            f"[warning] Cached credentials were issued for {config['api_url']}; current target is {api_url}",
            err=True,
        )

    if api_key:
        if token:
            click.echo("[info] Using stored API key for authentication.", err=True)
        client = YeeterClient(api_url=api_url, api_key=api_key, verify_tls=verify_tls)
    else:
        client = YeeterClient(api_url=api_url, token=token, verify_tls=verify_tls)
    return client, config


def _print_run_snapshot(run: Dict[str, Any]) -> None:
    started_at = run.get("started_at")
    completed_at = run.get("completed_at")
    click.echo(
        f"Run {run['id']} | status={run['status']} | patients={run.get('patient_count', 'n/a')} | "
        f"started={started_at or 'n/a'} | completed={completed_at or 'n/a'}"
    )
    events = run.get("events") or []
    if events:
        last = events[-1]
        click.echo(
            f"  last event [{last['timestamp']}] step={last['step_order']} iter={last['iteration']} "
            f"status={last['status']}" \
            f" :: {last['details']}"
        )


def _print_stats_table(stats: Dict[str, Any]) -> None:
    duration = stats.get("duration_seconds")
    duration_display = f"{duration:.2f}s" if isinstance(duration, (int, float)) else "n/a"
    click.echo(f"Run {stats['run_id']} statistics")
    click.echo("=" * 40)
    click.echo(
        f"Status: {stats['status']}, Patients: {stats['patient_count']}, "
        f"Unique Steps: {stats['unique_steps']}, Max Iteration: {stats['max_iteration']}"
    )
    click.echo(
        f"Started: {stats.get('started_at') or 'n/a'} | Completed: {stats.get('completed_at') or 'n/a'} | "
        f"Duration: {duration_display}"
    )
    click.echo(
        "Events -> total: {total} | success: {success} | failures: {failure} | warnings: {warning} | "
        "info: {info} | debug: {debug}".format(
            total=stats['total_events'],
            success=stats['success_events'],
            failure=stats['failure_events'],
            warning=stats['warning_events'],
            info=stats['info_events'],
            debug=stats['debug_events'],
        )
    )
    if stats.get("last_failure"):
        click.echo(f"Last failure: {stats['last_failure']}")

    steps = stats.get("steps") or []
    if steps:
        click.echo("\nStep breakdown:")
        click.echo("step,total,success,failure,warn,info")
        for step in steps:
            click.echo(
                f"{step['step_order']},{step['total_events']},{step['success_events']},{step['failure_events']},"
                f"{step['warning_events']},{step['info_events']}"
            )


def _emit_stats_csv(stats: Dict[str, Any]) -> None:
    writer = csv.writer(sys.stdout)
    writer.writerow(["metric", "value"])
    for key in (
        "run_id",
        "status",
        "patient_count",
        "started_at",
        "completed_at",
        "duration_seconds",
        "total_events",
        "success_events",
        "failure_events",
        "warning_events",
        "info_events",
        "debug_events",
        "unique_steps",
        "max_iteration",
        "last_failure",
    ):
        writer.writerow([key, stats.get(key, "")])

    writer.writerow([])
    writer.writerow(["step_order", "total_events", "success_events", "failure_events", "warning_events", "info_events"])
    for step in stats.get("steps", []):
        writer.writerow(
            [
                step["step_order"],
                step["total_events"],
                step["success_events"],
                step["failure_events"],
                step["warning_events"],
                step["info_events"],
            ]
        )


@click.group()
@click.option("--api-url", default=DEFAULT_API_URL, show_default=True, help="Base URL for the Yeeter API.")
@click.option("--insecure", is_flag=True, default=False, help="Disable TLS verification (for local testing only).")
@click.pass_context
def cli(ctx: click.Context, api_url: str, insecure: bool) -> None:
    """Interact with HL7 Yeeter from the command line."""
    ctx.ensure_object(dict)
    ctx.obj["api_url"] = api_url.rstrip("/")
    ctx.obj["verify_tls"] = not insecure


@cli.command()
@click.option("--username", prompt=True)
@click.option("--password", prompt=True, hide_input=True)
@click.pass_context
def login(ctx: click.Context, username: str, password: str) -> None:
    """Authenticate with the Yeeter API and cache the JWT token."""
    client = YeeterClient(api_url=ctx.obj["api_url"], verify_tls=ctx.obj["verify_tls"])
    payload = {"username": username, "password": password}
    response = client.post_json("/api/auth/login", payload)

    access_token = response.get("access_token")
    if not access_token:
        raise ApiError("Login succeeded but no access_token returned.")

    config = _load_config()
    config.update(
        {
            "api_url": ctx.obj["api_url"],
            "access_token": access_token,
            "username": response.get("username", username),
            "is_admin": response.get("is_admin", False),
            "auth_method": "jwt",
            "saved_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }
    )
    _save_config(config)
    click.echo(f"Authenticated as {config['username']}. Token cached at {CONFIG_PATH}.")


@cli.command("api-key")
@click.option("--value", "api_key", help="API key generated via the web UI.")
@click.option("--clear", is_flag=True, help="Remove any stored API key from the local cache.")
@click.pass_context
def configure_api_key(ctx: click.Context, api_key: str | None, clear: bool) -> None:
    """Store or remove an API key for non-interactive automation."""
    if clear and api_key:
        raise click.UsageError("Cannot use --value and --clear together.")

    config = _load_config()

    if clear:
        if "api_key" in config:
            del config["api_key"]
        config["auth_method"] = "jwt" if config.get("access_token") else None
        config["saved_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        _save_config(config)
        click.echo("Stored API key removed.")
        return

    normalized_key = (api_key or click.prompt("API key", hide_input=True)).strip()

    if len(normalized_key) < 16 or not normalized_key.startswith("ytr_"):
        raise click.BadParameter("API keys must start with 'ytr_' and should be at least 16 characters long.")

    config.update(
        {
            "api_url": ctx.obj["api_url"],
            "api_key": normalized_key,
            "auth_method": "api_key",
            "saved_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }
    )
    _save_config(config)
    click.echo(f"API key stored for {config['api_url']}.")


@cli.group()
@click.pass_context
def templates(ctx: click.Context) -> None:
    """Commands for viewing simulation templates."""


@templates.command("list")
@click.option("--output", "output_format", type=click.Choice(["table", "json"]), default="table", show_default=True,
              help="Choose pretty table output or raw JSON.")
@click.pass_context
def list_templates(ctx: click.Context, output_format: str) -> None:
    """List available simulation templates."""
    client, _ = _get_authenticated_client(ctx)
    templates = client.get_json("/api/simulator/templates")

    if output_format == "json":
        click.echo(json.dumps(templates, indent=2))
        return

    if not templates:
        click.echo("No templates found.")
        return

    click.echo("ID  | Name")
    click.echo("----|------------------------------")
    for template in templates:
        if isinstance(template, dict):
            template_id = str(template.get('id', 'n/a')).rjust(3)
            name = template.get('name', 'n/a')
            click.echo(f"{template_id} | {name}")
        else:
            click.echo(str(template))


@cli.group()
@click.pass_context
def runs(ctx: click.Context) -> None:
    """Commands for creating and monitoring simulation runs."""


@runs.command("list")
@click.option(
    "--output",
    "output_format",
    type=click.Choice(["table", "json"]),
    default="table",
    show_default=True,
    help="Choose pretty table output or raw JSON.",
)
@click.pass_context
def list_runs(ctx: click.Context, output_format: str) -> None:
    """List recent simulation runs for the current user."""
    client, _ = _get_authenticated_client(ctx)
    runs = client.get_json("/api/simulator/runs")

    if output_format == "json":
        click.echo(json.dumps(runs, indent=2))
        return

    if not runs:
        click.echo("No simulation runs found.")
        return

    click.echo("ID   | Status      | Patients | Started At           | Completed At")
    click.echo("-----|-------------|----------|----------------------|----------------------")
    for entry in runs:
        if not isinstance(entry, dict):
            click.echo(str(entry))
            continue

        run_id = str(entry.get("id", "n/a")).rjust(4)
        status = str(entry.get("status", "n/a")).ljust(11)
        patients = str(entry.get("patient_count", "n/a")).rjust(8)
        started = (entry.get("started_at") or "n/a").ljust(22)
        completed = entry.get("completed_at") or "n/a"
        click.echo(f"{run_id} | {status} | {patients} | {started} | {completed}")


@runs.command("start")
@click.option("--template-id", required=True, type=int, help="Simulation template ID to execute.")
@click.option("--patients", default=1, show_default=True, type=click.IntRange(1, None), help="Number of patient iterations.")
@click.option("--output", "output_format", type=click.Choice(["message", "json"]), default="message", show_default=True,
              help="Control how the run information is printed.")
@click.pass_context
def start_run(ctx: click.Context, template_id: int, patients: int, output_format: str) -> None:
    """Start a simulation run for a given template."""
    client, _ = _get_authenticated_client(ctx)
    payload = {"template_id": template_id, "patient_count": patients}
    response = client.post_json("/api/simulator/run", payload)
    run_id = response.get("run_id")
    if not run_id:
        raise ApiError("Run creation response did not include run_id.")
    if output_format == "json":
        click.echo(json.dumps({
            "run_id": run_id,
            "template_id": template_id,
            "patient_count": patients,
            "message": response.get("message")
        }))
    else:
        click.echo(f"Run {run_id} accepted for template {template_id} (patients={patients}).")


@runs.command("watch")
@click.argument("run_id", type=int)
@click.option("--interval", default=3.0, show_default=True, type=float, help="Polling interval in seconds.")
@click.option("--follow/--no-follow", default=True, show_default=True, help="Continue polling until the run finishes.")
@click.pass_context
def watch_run(ctx: click.Context, run_id: int, interval: float, follow: bool) -> None:
    """Poll a simulation run and display live status updates."""
    client, _ = _get_authenticated_client(ctx)

    while True:
        run = client.get_json(f"/api/simulator/runs/{run_id}")
        _print_run_snapshot(run)

        if not follow or run.get("status") in TERMINAL_STATUSES:
            break

        time.sleep(max(interval, 1.0))


@runs.command("cancel")
@click.argument("run_id", type=int)
@click.pass_context
def cancel_run(ctx: click.Context, run_id: int) -> None:
    """Request cancellation for an in-flight simulation run."""
    client, _ = _get_authenticated_client(ctx)
    response = client.post_json(f"/api/simulator/runs/{run_id}/cancel", {})
    click.echo(response.get("message", "Cancellation requested."))


@runs.command("stats")
@click.argument("run_id", type=int)
@click.option("--format", "output_format", type=click.Choice(["table", "json", "csv"]), default="table", show_default=True)
@click.pass_context
def run_stats(ctx: click.Context, run_id: int, output_format: str) -> None:
    """Fetch aggregated statistics for a simulation run."""
    client, _ = _get_authenticated_client(ctx)
    stats = client.get_json(f"/api/simulator/runs/{run_id}/stats")

    if output_format == "json":
        click.echo(json.dumps(stats, indent=2))
    elif output_format == "csv":
        _emit_stats_csv(stats)
    else:
        _print_stats_table(stats)


if __name__ == "__main__":
    cli()
# --- END OF FILE scripts/yeeter_cli.py ---
