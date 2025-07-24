# --- START OF FILE app/commands.py ---
import click
import logging
import requests  # <-- Our new weapon
from flask.cli import with_appcontext
from .extensions import db
from .models import Hl7TableDefinition

# The holy grail URL you discovered
HL7_TABLES_URL = "https://terminology.hl7.org/1.0.0/CodeSystem-v2-tables.json"

@click.command(name='load_hl7_tables')
@with_appcontext
def load_hl7_tables():
    """
    Fetches the official HL7 v2 table definitions from the HL7 terminology
    server and loads them into the database.
    """
    click.echo(f"Fetching HL7 table definitions from: {HL7_TABLES_URL}")
    
    try:
        response = requests.get(HL7_TABLES_URL)
        response.raise_for_status()  # This will raise an exception for bad status codes (4xx or 5xx)
        data = response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch data from HL7 terminology server: {e}")
        return
    except ValueError:
        logging.error("Failed to parse JSON response from server.")
        return

    click.echo("Successfully fetched data. Clearing existing table definitions...")
    db.session.query(Hl7TableDefinition).delete()
    db.session.commit()

    loaded_count = 0
    
    # This JSON is a FHIR CodeSystem resource. The structure is a nested list of 'concept' objects.
    # The top-level concepts are the tables themselves.
    for table_concept in data.get('concept', []):
        table_id = table_concept.get('code')
        if not table_id:
            continue
            
        # The values of each table are in a nested 'concept' list.
        for value_concept in table_concept.get('concept', []):
            value = value_concept.get('code')
            description = value_concept.get('display')
            
            if not value or not description:
                continue
            
            definition = Hl7TableDefinition(
                table_id=table_id,
                value=value,
                description=description,
                version="2.5.1"  # We can hardcode this for now
            )
            db.session.add(definition)
            loaded_count += 1
            
    db.session.commit()
    click.echo(f'Fucking brilliant. Successfully loaded {loaded_count} definitions into the database.')

def register_commands(app):
    app.cli.add_command(load_hl7_tables)
# --- END OF FILE app/commands.py ---