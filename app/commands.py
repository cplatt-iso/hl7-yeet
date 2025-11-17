import os
import json
import logging
import click
from flask import current_app
from flask.cli import with_appcontext

from .extensions import db
from .models import Hl7TableDefinition
from .util.worker_scaler import init_worker_autoscaler

STATIC_DIR = "/app/app/static"  # inside container path

@click.command(name="load_hl7_tables")
@with_appcontext
def load_hl7_tables():
    """
    Loads HL7 v2 table definitions from individual CodeSystem JSON files into DB.
    """
    # Load master index first
    index_path = os.path.join(STATIC_DIR, "CodeSystem-v2-tables.json")
    if not os.path.exists(index_path):
        click.echo(f"ERROR: Missing {index_path}")
        return

    with open(index_path, "r") as f:
        tables_data = json.load(f)

    top_concepts = tables_data.get("concept", [])
    click.echo(f"Found {len(top_concepts)} tables in index. Clearing DB…")

    db.session.query(Hl7TableDefinition).delete()
    db.session.commit()

    loaded_count = 0

    for table in top_concepts:
        table_id = table.get("code")
        if not table_id:
            continue

        file_path = os.path.join(STATIC_DIR, f"CodeSystem-v2-{table_id}.json")
        if not os.path.exists(file_path):
            logging.warning(f"[MISSING] {file_path}")
            continue

        with open(file_path, "r") as f:
            table_data = json.load(f)

        # Load value concepts
        for value_concept in table_data.get("concept", []):
            value = value_concept.get("code")
            description = value_concept.get("display")
            if not value or not description:
                continue

            db.session.add(
                Hl7TableDefinition(
                    table_id=table_id,
                    value=value,
                    description=description,
                    version="2.5.1"
                )
            )
            loaded_count += 1

    db.session.commit()
    click.echo(f"Fucking brilliant. Successfully loaded {loaded_count} definitions into the database.")


@click.command(name="scale_workers")
@click.argument("replicas", type=int)
@with_appcontext
def scale_workers(replicas: int):
    """Manually scale the worker deployment to REPLICAS using the autoscaler."""

    if replicas < 1:
        raise click.BadParameter("replicas must be >= 1")

    autoscaler = init_worker_autoscaler(current_app)
    success, error = autoscaler.apply_manual_scale(replicas)
    if not success:
        raise click.ClickException(f"Failed to scale workers: {error}")

    payload = autoscaler.get_status_payload()
    status = payload.get("status", {})
    click.echo(
        f"Workers scaled to {status.get('current_replicas')} replicas (target={status.get('target_replicas')})."
    )

def register_commands(app):
    app.cli.add_command(load_hl7_tables)
    app.cli.add_command(scale_workers)
# --- END OF FILE app/commands.py ---