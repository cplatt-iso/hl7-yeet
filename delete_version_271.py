#!/usr/bin/env python3
"""Script to delete HL7 version 2.7.1 from the database."""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Build database URL from environment variables
POSTGRES_USER = os.getenv('POSTGRES_USER', 'yeeter_user')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'yeeter_pw')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'hl7_yeeter_db')
POSTGRES_HOST = 'localhost'
POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5434')

DATABASE_URL = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

print(f"Connecting to database...")
print(f"Host: {POSTGRES_HOST}:{POSTGRES_PORT}")
print(f"Database: {POSTGRES_DB}")
print()

try:
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # First check if the version exists
        result = conn.execute(
            text("SELECT id, version, description FROM hl7_versions WHERE version = '2.7.1'")
        )
        version = result.fetchone()
        
        if version:
            print(f"Found version 2.7.1:")
            print(f"  ID: {version[0]}")
            print(f"  Version: {version[1]}")
            print(f"  Description: {version[2]}")
            print()
            
            # Delete it
            print("Deleting version 2.7.1 from database...")
            conn.execute(text("DELETE FROM hl7_versions WHERE version = '2.7.1'"))
            conn.commit()
            print("✓ Version 2.7.1 successfully deleted")
            print()
            
            # Show remaining versions
            result = conn.execute(
                text("SELECT version, is_active, is_default FROM hl7_versions ORDER BY version")
            )
            versions = result.fetchall()
            print(f"Remaining versions ({len(versions)}):")
            for v in versions:
                default_marker = "⭐" if v[2] else "  "
                active_marker = "✓" if v[1] else "✗"
                print(f"  {default_marker}{active_marker} {v[0]}")
        else:
            print("Version 2.7.1 not found in database")
            
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
