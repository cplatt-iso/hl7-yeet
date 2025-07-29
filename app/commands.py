import os
import json
import logging
import click
from flask.cli import with_appcontext
from .extensions import db
from .models import Hl7TableDefinition

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

def register_commands(app):
    app.cli.add_command(load_hl7_tables)
# --- END OF FILE app/commands.py ---