#!/usr/bin/env python3
"""Script to check available HL7 versions in the database."""

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
        # Check HL7 versions in database
        result = conn.execute(
            text("SELECT id, version, description, is_active, is_default, processed_at FROM hl7_versions ORDER BY processed_at DESC")
        )
        versions = result.fetchall()
        
        if versions:
            print(f"✓ Found {len(versions)} HL7 version(s) in database:")
            print()
            for v in versions:
                active_marker = "✓" if v[3] else "✗"
                default_marker = "⭐" if v[4] else "  "
                print(f"  {default_marker}{active_marker} Version: {v[1]}")
                print(f"     Description: {v[2]}")
                print(f"     Active: {v[3]}, Default: {v[4]}")
                print(f"     Processed: {v[5]}")
                
                # Check if definition files exist
                base_dir = os.path.abspath('/home/icculus/projects/yeeter')
                version_path = os.path.join(base_dir, 'segment-dictionary', v[1])
                if os.path.isdir(version_path):
                    file_count = len([f for f in os.listdir(version_path) if f.endswith('.json')])
                    print(f"     📁 Definitions: {file_count} files found at {version_path}")
                else:
                    print(f"     ❌ Definitions: NOT FOUND at {version_path}")
                print()
        else:
            print("❌ No HL7 versions found in database")
            print()
            print("To add an HL7 version:")
            print("  1. Log in as an admin")
            print("  2. Go to Admin → HL7 Version Management")
            print("  3. Upload an HL7 definition ZIP file (containing fields.xsd and segments.xsd)")
            
except Exception as e:
    print(f"❌ Error connecting to database: {e}")
    print()
    print("Make sure:")
    print("  1. PostgreSQL is running (check docker-compose)")
    print("  2. Port 5434 is accessible")
    print("  3. Database credentials in .env are correct")
